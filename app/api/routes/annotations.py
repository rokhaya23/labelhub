from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_annotator, require_reviewer
from app.db.session import get_db
from app.models.user import User
from app.repositories.annotation_repository import annotation_repository
from app.schemas.annotation import AnnotationResponse, AnnotationReview, AnnotationUpdate

router = APIRouter()


def _get_annotation_or_404(db: Session, annotation_id: int):
    annotation = annotation_repository.get_by_id(db, annotation_id)
    if annotation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation introuvable")
    return annotation


@router.patch("/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: int,
    payload: AnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_annotator),
):
    annotation = _get_annotation_or_404(db, annotation_id)
    return annotation_repository.update(db, annotation, current_user.id, payload)


@router.patch("/{annotation_id}/review", response_model=AnnotationResponse)
def review_annotation(
    annotation_id: int,
    payload: AnnotationReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    annotation = _get_annotation_or_404(db, annotation_id)
    return annotation_repository.review(db, annotation, current_user.id, payload)