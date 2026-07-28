import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import *  # noqa: F401,F403 - enregistre tous les modèles sur Base.metadata
from app.models.role import RoleEnum
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate
from fastapi.testclient import TestClient

# StaticPool + sqlite:///:memory: : une seule connexion SQLite partagée par
# tout le test (client API + accès direct au repository), sinon chaque
# nouvelle connexion ouvrirait une base en mémoire différente et vide.
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    """Base propre pour CHAQUE test (function-scoped) : create_all avant,
    drop_all après - aucun test ne voit les données d'un autre."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """TestClient dont get_db() est remplacé par la session de test, pour que
    les routes utilisent la même base en mémoire que le test."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user_and_login(client, db_session, email, role, password="azertyui123"):
    user_repository.create(
        db_session,
        UserCreate(full_name=f"Test {role.value}", email=email, password=password, role=role, is_active=True),
    )
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"login failed for {email}: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_headers(client, db_session):
    return _create_user_and_login(client, db_session, "admin@test.com", RoleEnum.ADMIN)


@pytest.fixture()
def data_manager_headers(client, db_session):
    return _create_user_and_login(client, db_session, "dm@test.com", RoleEnum.DATA_MANAGER)


@pytest.fixture()
def annotator_headers(client, db_session):
    return _create_user_and_login(client, db_session, "ann1@test.com", RoleEnum.ANNOTATOR)


@pytest.fixture()
def annotator2_headers(client, db_session):
    return _create_user_and_login(client, db_session, "ann2@test.com", RoleEnum.ANNOTATOR)


@pytest.fixture()
def reviewer_headers(client, db_session):
    return _create_user_and_login(client, db_session, "rev@test.com", RoleEnum.REVIEWER)


def get_user_id(client, headers):
    return client.get("/users/me", headers=headers).json()["id"]