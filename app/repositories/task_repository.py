from itertools import cycle

from sqlalchemy.orm import Session

from app.models.dataset import DatasetItem
from app.models.task import Task, TaskStatus
from app.utils.pagination import paginate


class TaskRepository:
    def create_tasks_for_campaign(
        self, db: Session, campaign_id: int, items: list[DatasetItem], annotator_ids: list[int]
    ) -> list[Task]:
        """Répartit les items entre les annotateurs en tourniquet (round-robin).
        Appelée uniquement par CampaignRepository.open() - aucune route ne crée
        de Task directement, ce n'est pas une entrée client."""
        annotator_cycle = cycle(annotator_ids)
        tasks = [
            Task(campaign_id=campaign_id, item_id=item.id, annotator_id=next(annotator_cycle))
            for item in items
        ]
        db.add_all(tasks)
        db.commit()
        for task in tasks:
            db.refresh(task)
        return tasks

    def get_by_id(self, db: Session, task_id: int) -> Task | None:
        return db.get(Task, task_id)

    def list_for_annotator(self, db: Session, annotator_id: int, skip: int = 0, limit: int = 50) -> list[Task]:
        query = db.query(Task).filter(Task.annotator_id == annotator_id)
        return paginate(query, Task, skip=skip, limit=limit)

    def count_for_campaign(self, db: Session, campaign_id: int) -> int:
        return db.query(Task).filter(Task.campaign_id == campaign_id).count()

    def count_submitted_for_campaign(self, db: Session, campaign_id: int) -> int:
        return (
            db.query(Task)
            .filter(Task.campaign_id == campaign_id, Task.status == TaskStatus.SUBMITTED)
            .count()
        )


task_repository = TaskRepository()