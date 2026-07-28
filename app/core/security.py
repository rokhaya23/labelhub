from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.utils.hashing import hash_password, verify_password  # noqa: F401 (ré-exportés pour compat)

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(
    subject: str | int,
    extra_data: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Génère un JWT d'accès (courte durée)."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """Génère un JWT de rafraîchissement (longue durée)."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    """Décode un JWT et vérifie son type (access/refresh).

    C'est cette vérification de `expected_type` qui empêche un refresh token
    (à durée de vie longue) d'être utilisé pour s'authentifier sur une route
    protégée normale - sans elle, un refresh token volé aurait les mêmes
    pouvoirs qu'un access token pendant 7 jours au lieu de 15 minutes.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception
    if payload.get("sub") is None or payload.get("type") != expected_type:
        raise credentials_exception
    return payload


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Dépendance à utiliser sur chaque route protégée : Depends(get_current_user).
    """
    payload = decode_token(token, expected_type="access")
    user_id = int(payload["sub"])

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable ou inactif",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user