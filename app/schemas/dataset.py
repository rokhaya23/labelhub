from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DatasetCreate(BaseModel):
    """POST /datasets. `owner_id` n'est jamais fourni par le client :
    il est déduit de l'utilisateur authentifié (current_user.id) dans la
    route, pas dans le schema - sinon un data_manager pourrait créer un
    dataset au nom d'un autre.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)


class DatasetItemCreate(BaseModel):
    """POST /datasets/{id}/items. Import en lot : une campagne exige au
    moins 10 items, donc un import unitaire serait peu pratique.
    """

    items: list[str] = Field(min_length=1, description="Liste des contenus textuels à importer")


class DatasetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    created_at: datetime


class DatasetResponse(BaseModel):
    """Vue résumée - utilisée pour GET /datasets (liste)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime


class DatasetDetailResponse(DatasetResponse):
    """Vue détaillée - utilisée pour GET /datasets/{id}, avec ses items."""

    items: list[DatasetItemResponse] = []