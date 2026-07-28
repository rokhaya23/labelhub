from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base
from app.models.role import RoleEnum


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="role_enum"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations (chaîne de responsabilités selon le rôle)
    datasets: Mapped[list["Dataset"]] = relationship(back_populates="owner")
    campaigns_created: Mapped[list["Campaign"]] = relationship(back_populates="created_by_user")
    assignments: Mapped[list["CampaignAssignment"]] = relationship(back_populates="annotator")
    tasks: Mapped[list["Task"]] = relationship(back_populates="annotator")
    annotations: Mapped[list["Annotation"]] = relationship(
        back_populates="annotator", foreign_keys="Annotation.annotator_id"
    )