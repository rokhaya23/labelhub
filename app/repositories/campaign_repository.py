from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError
from app.models.annotation import Annotation, AnnotationStatus
from app.models.campaign import Campaign, CampaignAssignment, CampaignReviewer, CampaignStatus
from app.models.task import Task
from app.repositories.dataset_repository import dataset_repository
from app.repositories.task_repository import task_repository
from app.schemas.campaign import CampaignCreate

MIN_ITEMS_TO_OPEN = 10
MIN_ANNOTATORS_TO_OPEN = 2


class CampaignRepository:
    def get_by_id(self, db: Session, campaign_id: int) -> Campaign | None:
        return db.get(Campaign, campaign_id)

    def create(self, db: Session, created_by: int, payload: CampaignCreate) -> Campaign:
        campaign = Campaign(
            name=payload.name,
            dataset_id=payload.dataset_id,
            allowed_labels=payload.allowed_labels,
            created_by=created_by,
        )
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign

    def assign_annotators(
        self, db: Session, campaign: Campaign, annotator_ids: list[int]
    ) -> list[CampaignAssignment]:
        assignments = [
            CampaignAssignment(campaign_id=campaign.id, annotator_id=aid) for aid in annotator_ids
        ]
        db.add_all(assignments)
        db.commit()
        for a in assignments:
            db.refresh(a)
        return assignments

    def count_distinct_annotators(self, db: Session, campaign_id: int) -> int:
        return (
            db.query(CampaignAssignment.annotator_id)
            .filter(CampaignAssignment.campaign_id == campaign_id)
            .distinct()
            .count()
        )

    def assign_reviewers(
        self, db: Session, campaign: Campaign, reviewer_ids: list[int]
    ) -> list[CampaignReviewer]:
        assignments = [
            CampaignReviewer(campaign_id=campaign.id, reviewer_id=rid) for rid in reviewer_ids
        ]
        db.add_all(assignments)
        db.commit()
        for a in assignments:
            db.refresh(a)
        return assignments

    def is_reviewer_assigned(self, db: Session, campaign_id: int, reviewer_id: int) -> bool:
        return (
            db.query(CampaignReviewer)
            .filter(CampaignReviewer.campaign_id == campaign_id, CampaignReviewer.reviewer_id == reviewer_id)
            .first()
            is not None
        )

    def open(self, db: Session, campaign: Campaign) -> Campaign:
        """Applique les 2 invariants du sujet avant de passer OPEN, et génère
        les Tasks (répartition des items entre annotateurs) puisqu'aucun
        endpoint ne les crée manuellement."""
        item_count = dataset_repository.count_items(db, campaign.dataset_id)
        annotator_count = self.count_distinct_annotators(db, campaign.id)

        if item_count < MIN_ITEMS_TO_OPEN:
            raise BusinessRuleError(
                f"Impossible d'ouvrir : {item_count} item(s), {MIN_ITEMS_TO_OPEN} minimum requis"
            )
        if annotator_count < MIN_ANNOTATORS_TO_OPEN:
            raise BusinessRuleError(
                f"Impossible d'ouvrir : {annotator_count} annotateur(s), {MIN_ANNOTATORS_TO_OPEN} minimum requis"
            )

        dataset = dataset_repository.get_by_id(db, campaign.dataset_id)
        annotator_ids = [
            aid
            for (aid,) in db.query(CampaignAssignment.annotator_id)
            .filter(CampaignAssignment.campaign_id == campaign.id)
            .distinct()
            .all()
        ]
        task_repository.create_tasks_for_campaign(db, campaign.id, dataset.items, annotator_ids)

        campaign.status = CampaignStatus.OPEN
        campaign.opened_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    def close(self, db: Session, campaign: Campaign) -> Campaign:
        campaign.status = CampaignStatus.CLOSED
        campaign.closed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        return campaign

    def progress(self, db: Session, campaign: Campaign) -> dict:
        tasks_total = task_repository.count_for_campaign(db, campaign.id)
        tasks_submitted = task_repository.count_submitted_for_campaign(db, campaign.id)
        approved = (
            db.query(Annotation)
            .join(Task, Task.id == Annotation.task_id)
            .filter(Task.campaign_id == campaign.id, Annotation.status == AnnotationStatus.APPROVED)
            .count()
        )
        rejected = (
            db.query(Annotation)
            .join(Task, Task.id == Annotation.task_id)
            .filter(Task.campaign_id == campaign.id, Annotation.status == AnnotationStatus.REJECTED)
            .count()
        )
        return {
            "campaign_id": campaign.id,
            "status": campaign.status,
            "tasks_total": tasks_total,
            "tasks_submitted": tasks_submitted,
            "tasks_pending": tasks_total - tasks_submitted,
            "annotations_approved": approved,
            "annotations_rejected": rejected,
        }


campaign_repository = CampaignRepository()