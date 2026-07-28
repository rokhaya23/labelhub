from sqlalchemy.orm import Session

from app.models.role import RoleEnum
from app.models.user import User
from app.schemas.auth import UserRegister
from app.schemas.user import UserCreate
from app.utils.hashing import hash_password


class UserRepository:
    """Seul endroit du projet qui écrit des requêtes SQLAlchemy sur User."""

    def get_by_id(self, db: Session, user_id: int) -> User | None:
        return db.get(User, user_id)

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def create(self, db: Session, payload: UserCreate) -> User:
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=payload.role,
            is_active=payload.is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def register(self, db: Session, payload: UserRegister) -> User:
        """POST /auth/register. Rôle toujours ANNOTATOR par défaut - un admin
        doit explicitement promouvoir via update_role si besoin d'un autre rôle."""
        user = User(
            full_name=payload.full_name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role=RoleEnum.ANNOTATOR,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_role(self, db: Session, user: User, role: RoleEnum) -> User:
        user.role = role
        db.commit()
        db.refresh(user)
        return user

    def set_active(self, db: Session, user: User, is_active: bool) -> User:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user

    def list_all(self, db: Session, skip: int = 0, limit: int = 50) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()


user_repository = UserRepository()