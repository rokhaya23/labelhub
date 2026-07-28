import enum
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.annotation import AnnotationStatus


class AnnotationCreate(BaseModel):
    """POST /tasks/{id}/annotations. `task_id` vient de l'URL, pas du body ;
    `annotator_id` déduit de current_user (jamais fourni par le client, sinon
    n'importe qui pourrait soumettre une annotation au nom d'un autre)."""

    label: str = Field(min_length=1, max_length=5000)


class AnnotationUpdate(BaseModel):
    """PATCH /annotations/{id}. Un seul champ modifiable, et uniquement par
    l'annotateur tant que le statut n'est pas APPROVED et que la campagne
    n'est pas CLOSED (vérifié dans le service, pas ici)."""

    label: str = Field(min_length=1, max_length=5000)


class ReviewDecision(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"


class AnnotationReview(BaseModel):
    """PATCH /annotations/{id}/review. `reviewer_id` déduit de current_user.
    Le service vérifie l'invariant reviewer != annotator avant d'écrire
    (en plus de la CheckConstraint en base, qui est le filet de sécurité)."""

    decision: ReviewDecision
    comment: str | None = Field(default=None, max_length=1000)


class AnnotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    annotator_id: int
    label: str
    status: AnnotationStatus
    reviewer_id: int | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime