from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_data_manager, require_roles
from app.db.session import get_db
from app.models.role import RoleEnum
from app.models.user import User
from app.repositories.dataset_repository import dataset_repository
from app.schemas.dataset import DatasetCreate, DatasetDetailResponse, DatasetItemCreate, DatasetResponse

router = APIRouter()


def _get_owned_dataset_or_404(db: Session, dataset_id: int, current_user: User):
    dataset = dataset_repository.get_by_id(db, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset introuvable")
    if current_user.role != RoleEnum.ADMIN and dataset.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce dataset ne vous appartient pas")
    return dataset


@router.post("", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
def create_dataset(
    payload: DatasetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_data_manager),
):
    return dataset_repository.create(db, current_user.id, payload)


@router.get("/{dataset_id}", response_model=DatasetDetailResponse)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    return _get_owned_dataset_or_404(db, dataset_id, current_user)


@router.post("/{dataset_id}/items", response_model=DatasetDetailResponse, status_code=status.HTTP_201_CREATED)
def add_dataset_items(
    dataset_id: int,
    payload: DatasetItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_data_manager),
):
    dataset = _get_owned_dataset_or_404(db, dataset_id, current_user)
    dataset_repository.add_items(db, dataset, payload.items)
    db.refresh(dataset)
    return dataset