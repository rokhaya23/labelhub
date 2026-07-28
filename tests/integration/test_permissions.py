"""Tests d'intégration permissions : vérifie que le rôle ET la propriété de
la ressource sont bien appliqués sur les routes protégées."""

from tests.conftest import get_user_id


class TestRolePermissions:
    def test_annotator_cannot_create_dataset(self, client, annotator_headers):
        r = client.post("/datasets", json={"name": "x"}, headers=annotator_headers)
        assert r.status_code == 403

    def test_reviewer_cannot_create_dataset(self, client, reviewer_headers):
        r = client.post("/datasets", json={"name": "x"}, headers=reviewer_headers)
        assert r.status_code == 403

    def test_data_manager_can_create_dataset(self, client, data_manager_headers):
        r = client.post("/datasets", json={"name": "x"}, headers=data_manager_headers)
        assert r.status_code == 201

    def test_annotator_cannot_list_users(self, client, annotator_headers):
        r = client.get("/users", headers=annotator_headers)
        assert r.status_code == 403

    def test_admin_can_list_users(self, client, admin_headers):
        r = client.get("/users", headers=admin_headers)
        assert r.status_code == 200

    def test_annotator_cannot_review_annotations(self, client, annotator_headers):
        # /campaigns/{id}/annotations est réservé aux reviewers
        r = client.get("/campaigns/1/annotations", headers=annotator_headers)
        assert r.status_code == 403


class TestResourceOwnership:
    def test_data_manager_cannot_access_another_data_manager_dataset(self, client, db_session):
        from app.models.role import RoleEnum
        from tests.conftest import _create_user_and_login

        dm1_headers = _create_user_and_login(client, db_session, "dm1@own.com", RoleEnum.DATA_MANAGER)
        dm2_headers = _create_user_and_login(client, db_session, "dm2@own.com", RoleEnum.DATA_MANAGER)

        r = client.post("/datasets", json={"name": "prive de dm1"}, headers=dm1_headers)
        dataset_id = r.json()["id"]

        r = client.get(f"/datasets/{dataset_id}", headers=dm2_headers)
        assert r.status_code == 403

    def test_admin_can_access_any_dataset(self, client, db_session, admin_headers):
        from app.models.role import RoleEnum
        from tests.conftest import _create_user_and_login

        dm_headers = _create_user_and_login(client, db_session, "dm3@own.com", RoleEnum.DATA_MANAGER)
        r = client.post("/datasets", json={"name": "prive"}, headers=dm_headers)
        dataset_id = r.json()["id"]

        r = client.get(f"/datasets/{dataset_id}", headers=admin_headers)
        assert r.status_code == 200

    def test_admin_can_open_any_campaign(self, client, db_session, admin_headers):
        from app.models.role import RoleEnum
        from tests.conftest import _create_user_and_login, get_user_id

        dm_headers = _create_user_and_login(client, db_session, "dm4@own.com", RoleEnum.DATA_MANAGER)
        ann1_headers = _create_user_and_login(client, db_session, "a1@own.com", RoleEnum.ANNOTATOR)
        ann2_headers = _create_user_and_login(client, db_session, "a2@own.com", RoleEnum.ANNOTATOR)

        r = client.post("/datasets", json={"name": "d"}, headers=dm_headers)
        dataset_id = r.json()["id"]
        client.post(
            f"/datasets/{dataset_id}/items",
            json={"items": [f"item {i}" for i in range(10)]},
            headers=dm_headers,
        )
        r = client.post(
            "/campaigns",
            json={"name": "c", "dataset_id": dataset_id, "allowed_labels": ["a"]},
            headers=dm_headers,
        )
        campaign_id = r.json()["id"]

        ann1_id = get_user_id(client, ann1_headers)
        ann2_id = get_user_id(client, ann2_headers)

        # L'admin, pas le data_manager propriétaire, assigne et ouvre
        r = client.post(
            f"/campaigns/{campaign_id}/assignments",
            json={"annotator_ids": [ann1_id, ann2_id]},
            headers=admin_headers,
        )
        assert r.status_code == 200

        r = client.patch(f"/campaigns/{campaign_id}/open", headers=admin_headers)
        assert r.status_code == 200

    def test_annotator_cannot_submit_on_unassigned_task(
        self, client, db_session, data_manager_headers, annotator_headers, annotator2_headers
    ):
        r = client.post("/datasets", json={"name": "d"}, headers=data_manager_headers)
        dataset_id = r.json()["id"]
        client.post(
            f"/datasets/{dataset_id}/items",
            json={"items": [f"item {i}" for i in range(10)]},
            headers=data_manager_headers,
        )
        r = client.post(
            "/campaigns",
            json={"name": "c", "dataset_id": dataset_id, "allowed_labels": ["a", "b"]},
            headers=data_manager_headers,
        )
        campaign_id = r.json()["id"]

        ann1_id = get_user_id(client, annotator_headers)
        ann2_id = get_user_id(client, annotator2_headers)
        client.post(
            f"/campaigns/{campaign_id}/assignments",
            json={"annotator_ids": [ann1_id, ann2_id]},
            headers=data_manager_headers,
        )
        client.patch(f"/campaigns/{campaign_id}/open", headers=data_manager_headers)

        tasks_ann1 = client.get("/tasks/me", headers=annotator_headers).json()
        task_id = tasks_ann1[0]["id"]

        # ann2 essaie d'annoter une tâche assignée à ann1
        r = client.post(f"/tasks/{task_id}/annotations", json={"label": "a"}, headers=annotator2_headers)
        assert r.status_code == 403

    def test_reviewer_not_assigned_to_campaign_is_blocked(
        self, client, data_manager_headers, reviewer_headers
    ):
        """Un reviewer existe globalement, mais ne peut voir/valider que les
        campagnes où il a été explicitement affecté via
        POST /campaigns/{id}/reviewers."""
        r = client.post("/datasets", json={"name": "d"}, headers=data_manager_headers)
        dataset_id = r.json()["id"]
        client.post(
            f"/datasets/{dataset_id}/items",
            json={"items": [f"item {i}" for i in range(10)]},
            headers=data_manager_headers,
        )
        r = client.post(
            "/campaigns",
            json={"name": "c", "dataset_id": dataset_id, "allowed_labels": ["a"]},
            headers=data_manager_headers,
        )
        campaign_id = r.json()["id"]

        # Le reviewer n'a jamais été affecté à cette campagne
        r = client.get(f"/campaigns/{campaign_id}/annotations", headers=reviewer_headers)
        assert r.status_code == 403