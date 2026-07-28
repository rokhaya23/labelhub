import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.campaign import Campaign
    from app.models.dataset import DatasetItem
    from app.models.annotation import Annotation


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"


class Task(Base):
    """Affectation d'un item de dataset à un annotateur, dans le cadre d'une campagne.

    C'est cette table qui garantit l'invariant :
    "un annotateur ne peut annoter que les items qui lui sont affectés."
    """

    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("campaign_id", "item_id", "annotator_id", name="uq_task_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("dataset_items.id"), nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), default=TaskStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="tasks")
    item: Mapped["DatasetItem"] = relationship(back_populates="tasks")
    annotator: Mapped["User"] = relationship(back_populates="tasks")
    annotation: Mapped["Annotation | None"] = relationship(back_populates="task", uselist=False)