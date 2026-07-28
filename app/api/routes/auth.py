from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.repositories.user_repository import user_repository
from app.schemas.auth import Token, UserRegister
from app.utils.hashing import verify_password

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte utilisateur",
    description="Crée un compte avec le rôle annotator par défaut. L'email doit être unique.",
    responses={400: {"description": "Email déjà utilisé"}},
)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if user_repository.get_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cet email est déjà utilisé")
    user = user_repository.register(db, payload)
    return {"id": user.id, "email": user.email, "role": user.role}


def _issue_tokens(user_id: int, role: str) -> Token:
    return Token(
        access_token=create_access_token(subject=user_id, extra_data={"role": role}),
        expires_in=15 * 60,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="Authentification (OAuth2 password flow)",
    description="Échange email + mot de passe contre un access token JWT.",
    responses={401: {"description": "Identifiants invalides ou compte désactivé"}},
)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """form_data.username porte en réalité l'email (contrainte du nom de
    champ imposée par la spec OAuth2, cf. schemas/auth.py -> UserLogin)."""
    user = user_repository.get_by_email(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte désactivé")
    return _issue_tokens(user.id, user.role.value)