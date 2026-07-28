"""Import de tous les modèles ici pour que SQLAlchemy résolve correctement
les relations basées sur des chaînes de caractères (forward references)
et pour qu'Alembic détecte tous les modèles lors de l'autogenerate.
"""

from app.models.role import RoleEnum
from app.models.user import User
from app.models.dataset import Dataset, DatasetItem
from app.models.campaign import Campaign, CampaignAssignment, CampaignStatus, CampaignReviewer
from app.models.task import Task, TaskStatus
from app.models.annotation import Annotation, AnnotationStatus

__all__ = [
    "RoleEnum",
    "User",
    "Dataset",
    "DatasetItem",
    "Campaign",
    "CampaignAssignment",
    "CampaignReviewer",
    "CampaignStatus",
    "Task",
    "TaskStatus",
    "Annotation",
    "AnnotationStatus",
]