from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.errors import BusinessRuleError, ForbiddenActionError
from app.models.annotation import Annotation, AnnotationStatus
from app.models.campaign import Campaign, CampaignReviewer, CampaignStatus
from app.models.task import Task, TaskStatus
from app.schemas.annotation import AnnotationCreate, AnnotationReview, AnnotationUpdate, ReviewDecision
from app.utils.pagination import paginate


class AnnotationRepository:
    def get_by_id(self, db: Session, annotation_id: int) -> Annotation | None:
        return db.get(Annotation, annotation_id)

    def list_for_campaign(
        self,
        db: Session,
        campaign_id: int,
        status: AnnotationStatus | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Annotation]:
        """GET /campaigns/{id}/annotations - permet au reviewer de voir les
        annotations de CETTE campagne avant de les valider (au lieu de devoir
        deviner un annotation_id pour PATCH /annotations/{id}/review).
        Par défaut ne montre que les annotations SUBMITTED (en attente de
        review) ; status=None les montre toutes (utile pour l'historique).
        """
        query = db.query(Annotation).join(Task, Task.id == Annotation.task_id).filter(
            Task.campaign_id == campaign_id
        )
        if status is not None:
            query = query.filter(Annotation.status == status)
        return paginate(query, Annotation, skip=skip, limit=limit)

    def create(self, db: Session, task: Task, annotator_id: int, payload: AnnotationCreate) -> Annotation:
        if task.annotator_id != annotator_id:
            raise ForbiddenActionError("Cette tâche ne vous est pas assignée")

        campaign = db.get(Campaign, task.campaign_id)
        if campaign.status != CampaignStatus.OPEN:
            raise BusinessRuleError("Impossible d'annoter : la campagne n'est pas ouverte")
        if payload.label not in campaign.allowed_labels:
            raise BusinessRuleError(
                f"Label '{payload.label}' non autorisé pour cette campagne. "
                f"Labels valides : {', '.join(campaign.allowed_labels)}"
            )

        annotation = Annotation(task_id=task.id, annotator_id=annotator_id, label=payload.label)
        task.status = TaskStatus.SUBMITTED
        db.add(annotation)
        db.commit()
        db.refresh(annotation)
        return annotation

    def update(
        self, db: Session, annotation: Annotation, annotator_id: int, payload: AnnotationUpdate
    ) -> Annotation:
        if annotation.annotator_id != annotator_id:
            raise ForbiddenActionError("Cette annotation ne vous appartient pas")
        if annotation.status == AnnotationStatus.APPROVED:
            raise BusinessRuleError("Une annotation approuvée ne peut plus être modifiée")

        task = db.get(Task, annotation.task_id)
        campaign = db.get(Campaign, task.campaign_id)
        if campaign.status != CampaignStatus.OPEN:
            raise BusinessRuleError("Impossible de modifier : la campagne est fermée")
        if payload.label not in campaign.allowed_labels:
            raise BusinessRuleError(
                f"Label '{payload.label}' non autorisé pour cette campagne. "
                f"Labels valides : {', '.join(campaign.allowed_labels)}"
            )

        annotation.label = payload.label
        db.commit()
        db.refresh(annotation)
        return annotation

    def review(
        self, db: Session, annotation: Annotation, reviewer_id: int, payload: AnnotationReview
    ) -> Annotation:
        if reviewer_id == annotation.annotator_id:
            raise ForbiddenActionError("Vous ne pouvez pas valider votre propre annotation")

        task = db.get(Task, annotation.task_id)
        is_assigned = (
            db.query(CampaignReviewer)
            .filter(
                CampaignReviewer.campaign_id == task.campaign_id,
                CampaignReviewer.reviewer_id == reviewer_id,
            )
            .first()
            is not None
        )
        if not is_assigned:
            raise ForbiddenActionError("Vous n'êtes pas affecté comme reviewer sur cette campagne")

        annotation.status = (
            AnnotationStatus.APPROVED
            if payload.decision == ReviewDecision.APPROVE
            else AnnotationStatus.REJECTED
        )
        annotation.reviewer_id = reviewer_id
        annotation.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(annotation)
        return annotation


annotation_repository = AnnotationRepository()