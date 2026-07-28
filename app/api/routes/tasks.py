from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_annotator
from app.db.session import get_db
from app.models.user import User
from app.repositories.annotation_repository import annotation_repository
from app.repositories.task_repository import task_repository
from app.schemas.annotation import AnnotationCreate, AnnotationResponse
from app.schemas.task import TaskResponse

router = APIRouter()


@router.get("/me", response_model=list[TaskResponse])
def list_my_tasks(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator),
):
    return task_repository.list_for_annotator(db, current_user.id, skip=skip, limit=limit)


@router.post("/{task_id}/annotations", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
def submit_annotation(
    task_id: int,
    payload: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator),
):
    task = task_repository.get_by_id(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable")
    return annotation_repository.create(db, task, current_user.id, payload)