from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.campaign import CampaignStatus


class CampaignCreate(BaseModel):
    """POST /campaigns. `created_by` déduit de current_user, pas du client
    (même logique que DatasetCreate.owner_id).

    allowed_labels : fixé une fois pour toutes par le data_manager à la
    création - chaque annotation soumise sur cette campagne devra utiliser
    un de ces labels exacts (vérifié dans annotation_repository, pas ici,
    puisque Pydantic ne peut pas valider un annotation.label contre une
    liste qui appartient à une AUTRE ressource déjà en base).
    """

    name: str = Field(min_length=1, max_length=255)
    dataset_id: int
    allowed_labels: list[str] = Field(min_length=1, description="Labels autorisés pour les annotations de cette campagne")


class CampaignAssignmentCreate(BaseModel):
    """POST /campaigns/{id}/assignments. Affecte un ou plusieurs annotateurs
    d'un coup - pratique pour atteindre rapidement l'invariant
    "au moins 2 annotateurs" avant ouverture.
    """

    annotator_ids: list[int] = Field(min_length=1)


class CampaignReviewerCreate(BaseModel):
    """POST /campaigns/{id}/reviewers. Affecte un ou plusieurs reviewers à la
    campagne - un reviewer ne peut voir/valider les annotations que des
    campagnes où il est explicitement affecté (sauf admin)."""

    reviewer_ids: list[int] = Field(min_length=1)


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    dataset_id: int
    status: CampaignStatus
    allowed_labels: list[str]
    created_by: int
    created_at: datetime
    opened_at: datetime | None
    closed_at: datetime | None


class CampaignProgressResponse(BaseModel):
    """GET /campaigns/{id}/progress. Ce schema n'a pas de correspondance
    directe avec un modèle SQLAlchemy : il est calculé par le repository
    à partir des Task et Annotation liées à la campagne (pas de
    `from_attributes`, on le construit explicitement dans le service).
    """

    campaign_id: int
    status: CampaignStatus
    tasks_total: int
    tasks_submitted: int
    tasks_pending: int
    annotations_approved: int
    annotations_rejected: int