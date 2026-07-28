import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id"), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"), default=CampaignStatus.DRAFT, nullable=False
    )
    # Liste des labels autorisés pour cette campagne, fixée par le data_manager
    # à la création. JSON plutôt qu'une table séparée : plus simple à écrire/lire
    # d'un coup, et fonctionne aussi bien en SQLite (tests) qu'en PostgreSQL.
    allowed_labels: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dataset: Mapped["Dataset"] = relationship(back_populates="campaigns")
    created_by_user: Mapped["User"] = relationship(back_populates="campaigns_created")
    assignments: Mapped[list["CampaignAssignment"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    reviewer_assignments: Mapped[list["CampaignReviewer"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="campaign")

    # Invariant (règle métier, contrôlé côté repository/service, pas en DB) :
    # une campagne ne peut passer à OPEN que si dataset.items >= 10
    # et campaign.assignments (annotateurs distincts) >= 2.


class CampaignAssignment(Base):
    """Table d'association : annotateurs affectés à une campagne."""

    __tablename__ = "campaign_assignments"
    __table_args__ = (
        UniqueConstraint("campaign_id", "annotator_id", name="uq_campaign_annotator"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    annotator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="assignments")
    annotator: Mapped["User"] = relationship(back_populates="assignments")


class CampaignReviewer(Base):
    """Table d'association : reviewers affectés à une campagne.

    Symétrique de CampaignAssignment (annotateurs), mais séparée plutôt que
    fusionnée : les deux rôles n'ont pas la même cardinalité minimale (2
    annotateurs minimum pour ouvrir, 0 contrainte sur les reviewers), et les
    mélanger dans une seule table demanderait un champ "role" en plus pour
    les distinguer - une table par rôle est plus simple à lire et à requêter.
    """

    __tablename__ = "campaign_reviewers"
    __table_args__ = (
        UniqueConstraint("campaign_id", "reviewer_id", name="uq_campaign_reviewer"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="reviewer_assignments")
    reviewer: Mapped["User"] = relationship()