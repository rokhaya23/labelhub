from sqlalchemy.orm import Session

from app.models.dataset import Dataset, DatasetItem
from app.schemas.dataset import DatasetCreate


class DatasetRepository:
    def get_by_id(self, db: Session, dataset_id: int) -> Dataset | None:
        return db.get(Dataset, dataset_id)

    def create(self, db: Session, owner_id: int, payload: DatasetCreate) -> Dataset:
        dataset = Dataset(name=payload.name, description=payload.description, owner_id=owner_id)
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        return dataset

    def add_items(self, db: Session, dataset: Dataset, contents: list[str]) -> list[DatasetItem]:
        items = [DatasetItem(dataset_id=dataset.id, content=c) for c in contents]
        db.add_all(items)
        db.commit()
        for item in items:
            db.refresh(item)
        return items

    def count_items(self, db: Session, dataset_id: int) -> int:
        return db.query(DatasetItem).filter(DatasetItem.dataset_id == dataset_id).count()

    def list_all(self, db: Session, skip: int = 0, limit: int = 50) -> list[Dataset]:
        return db.query(Dataset).offset(skip).limit(limit).all()


dataset_repository = DatasetRepository()