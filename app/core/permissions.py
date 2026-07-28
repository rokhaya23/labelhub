from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.role import RoleEnum
from app.models.user import User


def require_roles(*allowed_roles: RoleEnum):
    """Fabrique de dépendance FastAPI : vérifie que l'utilisateur authentifié
    a l'un des rôles autorisés. C'est ÇA, "l'autorisation centralisée via
    dépendances" demandée par le sujet - aucune route n'écrit
    `if current_user.role == ...` elle-même.

    Usage dans une route :
        @router.post("/datasets")
        def create_dataset(
            payload: DatasetCreate,
            current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER)),
        ):
            ...
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rôle '{current_user.role.value}' non habilité pour cette action",
            )
        return current_user

    return dependency


# Raccourcis pour les cas à un seul rôle - lisibilité dans les routes.
require_data_manager = require_roles(RoleEnum.DATA_MANAGER)
require_annotator = require_roles(RoleEnum.ANNOTATOR)
require_reviewer = require_roles(RoleEnum.REVIEWER)
require_admin = require_roles(RoleEnum.ADMIN)


def ensure_is_resource_owner(owner_id: int, current_user: User) -> None:
    """Vérification d'habilitation AU NIVEAU RESSOURCE (pas au niveau rôle).

    Exemple : `require_roles(RoleEnum.ANNOTATOR)` garantit que l'utilisateur
    EST annotateur, mais pas que cette annotation précise lui appartient.
    Cette 2ème vérification a besoin de l'id de la ressource chargée
    (donc récupérée dans la route/le service après lookup en base), elle ne
    peut pas être une simple dépendance générique comme require_roles.

    Un admin passe toujours (habilitation transverse).
    """
    if current_user.role != RoleEnum.ADMIN and current_user.id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette ressource ne vous appartient pas",
        )