"""Tests unitaires : appellent les repositories directement (pas l'API HTTP)
pour vérifier les invariants métier au plus près du code, indépendamment des
routes ou de la sérialisation JSON."""

import pytest

from app.core.errors import BusinessRuleError, ForbiddenActionError
from app.models.role import RoleEnum
from app.repositories.annotation_repository import annotation_repository
from app.repositories.campaign_repository import campaign_repository
from app.repositories.dataset_repository import dataset_repository
from app.repositories.task_repository import task_repository
from app.repositories.user_repository import user_repository
from app.schemas.annotation import AnnotationCreate, AnnotationReview, ReviewDecision
from app.schemas.campaign import CampaignCreate
from app.schemas.dataset import DatasetCreate
from app.schemas.user import UserCreate


def _make_users(db_session):
    dm = user_repository.create(
        db_session,
        UserCreate(full_name="DM", email="dm@u.com", password="azertyui", role=RoleEnum.DATA_MANAGER),
    )
    ann1 = user_repository.create(
        db_session,
        UserCreate(full_name="Ann1", email="a1@u.com", password="azertyui", role=RoleEnum.ANNOTATOR),
    )
    ann2 = user_repository.create(
        db_session,
        UserCreate(full_name="Ann2", email="a2@u.com", password="azertyui", role=RoleEnum.ANNOTATOR),
    )
    reviewer = user_repository.create(
        db_session,
        UserCreate(full_name="Rev", email="r@u.com", password="azertyui", role=RoleEnum.REVIEWER),
    )
    return dm, ann1, ann2, reviewer


class TestUserRepository:
    def test_create_hashes_password(self, db_session):
        user = user_repository.create(
            db_session,
            UserCreate(full_name="Test", email="hash@u.com", password="motdepasseclair", role=RoleEnum.ANNOTATOR),
        )
        assert user.hashed_password != "motdepasseclair"
        assert user.hashed_password.startswith("$2b$")  # préfixe bcrypt

    def test_register_defaults_to_annotator_role(self, db_session):
        from app.schemas.auth import UserRegister

        user = user_repository.register(
            db_session, UserRegister(full_name="Public", email="pub@u.com", password="azertyui")
        )
        assert user.role == RoleEnum.ANNOTATOR


class TestCampaignInvariants:
    def test_open_fails_with_too_few_items(self, db_session):
        dm, ann1, ann2, _ = _make_users(db_session)
        dataset = dataset_repository.create(db_session, dm.id, DatasetCreate(name="d", description=None))
        dataset_repository.add_items(db_session, dataset, [f"item {i}" for i in range(5)])  # < 10
        campaign = campaign_repository.create(
            db_session, dm.id, CampaignCreate(name="c", dataset_id=dataset.id, allowed_labels=["a", "b"])
        )
        campaign_repository.assign_annotators(db_session, campaign, [ann1.id, ann2.id])

        with pytest.raises(BusinessRuleError):
            campaign_repository.open(db_session, campaign)

    def test_open_fails_with_too_few_annotators(self, db_session):
        dm, ann1, _, _ = _make_users(db_session)
        dataset = dataset_repository.create(db_session, dm.id, DatasetCreate(name="d", description=None))
        dataset_repository.add_items(db_session, dataset, [f"item {i}" for i in range(10)])
        campaign = campaign_repository.create(
            db_session, dm.id, CampaignCreate(name="c", dataset_id=dataset.id, allowed_labels=["a"])
        )
        campaign_repository.assign_annotators(db_session, campaign, [ann1.id])  # un seul

        with pytest.raises(BusinessRuleError):
            campaign_repository.open(db_session, campaign)

    def test_open_succeeds_and_creates_tasks(self, db_session):
        dm, ann1, ann2, _ = _make_users(db_session)
        dataset = dataset_repository.create(db_session, dm.id, DatasetCreate(name="d", description=None))
        dataset_repository.add_items(db_session, dataset, [f"item {i}" for i in range(10)])
        campaign = campaign_repository.create(
            db_session, dm.id, CampaignCreate(name="c", dataset_id=dataset.id, allowed_labels=["a", "b"])
        )
        campaign_repository.assign_annotators(db_session, campaign, [ann1.id, ann2.id])

        campaign = campaign_repository.open(db_session, campaign)

        assert campaign.status.value == "open"
        total_tasks = task_repository.count_for_campaign(db_session, campaign.id)
        assert total_tasks == 10


class TestAnnotationInvariants:
    def _open_campaign(self, db_session, labels=("positif", "negatif")):
        dm, ann1, ann2, reviewer = _make_users(db_session)
        dataset = dataset_repository.create(db_session, dm.id, DatasetCreate(name="d", description=None))
        dataset_repository.add_items(db_session, dataset, [f"item {i}" for i in range(10)])
        campaign = campaign_repository.create(
            db_session, dm.id, CampaignCreate(name="c", dataset_id=dataset.id, allowed_labels=list(labels))
        )
        campaign_repository.assign_annotators(db_session, campaign, [ann1.id, ann2.id])
        campaign_repository.assign_reviewers(db_session, campaign, [reviewer.id])
        campaign = campaign_repository.open(db_session, campaign)
        return campaign, ann1, ann2, reviewer

    def test_annotator_cannot_annotate_unassigned_task(self, db_session):
        campaign, ann1, ann2, _ = self._open_campaign(db_session)
        tasks_ann1 = task_repository.list_for_annotator(db_session, ann1.id)

        with pytest.raises(ForbiddenActionError):
            annotation_repository.create(db_session, tasks_ann1[0], ann2.id, AnnotationCreate(label="positif"))

    def test_label_outside_allowed_list_rejected(self, db_session):
        campaign, ann1, _, _ = self._open_campaign(db_session, labels=("positif", "negatif"))
        tasks_ann1 = task_repository.list_for_annotator(db_session, ann1.id)

        with pytest.raises(BusinessRuleError):
            annotation_repository.create(db_session, tasks_ann1[0], ann1.id, AnnotationCreate(label="autre_chose"))

    def test_reviewer_cannot_approve_own_annotation(self, db_session):
        campaign, ann1, _, reviewer = self._open_campaign(db_session)
        tasks_ann1 = task_repository.list_for_annotator(db_session, ann1.id)
        annotation = annotation_repository.create(db_session, tasks_ann1[0], ann1.id, AnnotationCreate(label="positif"))

        with pytest.raises(ForbiddenActionError):
            annotation_repository.review(
                db_session, annotation, ann1.id, AnnotationReview(decision=ReviewDecision.APPROVE)
            )

    def test_approved_annotation_cannot_be_updated(self, db_session):
        from app.schemas.annotation import AnnotationUpdate

        campaign, ann1, _, reviewer = self._open_campaign(db_session)
        tasks_ann1 = task_repository.list_for_annotator(db_session, ann1.id)
        annotation = annotation_repository.create(db_session, tasks_ann1[0], ann1.id, AnnotationCreate(label="positif"))
        annotation = annotation_repository.review(
            db_session, annotation, reviewer.id, AnnotationReview(decision=ReviewDecision.APPROVE)
        )

        with pytest.raises(BusinessRuleError):
            annotation_repository.update(db_session, annotation, ann1.id, AnnotationUpdate(label="negatif"))