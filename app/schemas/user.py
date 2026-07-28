from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.role import RoleEnum


class UserCreate(BaseModel):
    """Création d'un compte PAR un admin (endpoint protégé, distinct de
    /auth/register). C'est ici, et seulement ici, que le rôle peut être
    choisi à la création - jamais dans un schema exposé au grand public.
    """

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    role: RoleEnum
    is_active: bool = True


class UserUpdate(BaseModel):
    """Mise à jour partielle du profil (PATCH). Tous les champs optionnels
    pour ne modifier que ce qui est fourni.
    """

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserRoleUpdate(BaseModel):
    """Changement de rôle - action admin uniquement
    """

    role: RoleEnum


class UserResponse(BaseModel):
    """Ce qui sort de l'API. Ne contient JAMAIS hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime