from asyncio import Task
import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models.user import User

class AnnotationStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class Annotation(Base):
    __tablename__ = "annotations"
    __table_args__ = (
        # Invariant : un reviewer ne peut pas valider une annotation qu'il a lui-même produite.
        CheckConstraint(
            "reviewer_id IS NULL OR reviewer_id != annotator_id", name="ck_reviewer_not_annotator"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), unique=True, nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AnnotationStatus] = mapped_column(
        Enum(AnnotationStatus, name="annotation_status"),
        default=AnnotationStatus.SUBMITTED,
        nullable=False,
    )
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="annotation")
    annotator: Mapped["User"] = relationship(back_populates="annotations", foreign_keys=[annotator_id])
    reviewer: Mapped["User | None"] = relationship(foreign_keys=[reviewer_id])

    # Autres invariants (contrôlés côté service/repository, pas en DB) :
    # - une annotation APPROVED ne peut plus être modifiée par l'annotateur
    # - une campagne CLOSED interdit toute nouvelle annotation