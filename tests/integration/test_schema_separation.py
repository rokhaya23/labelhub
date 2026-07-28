"""Tests qui prouvent que les schemas de sortie ne fuient jamais de champs
internes (hashed_password en particulier) - exigence explicite du sujet."""


class TestSchemaSeparation:
    def test_register_response_never_contains_hashed_password(self, client):
        r = client.post(
            "/auth/register",
            json={"full_name": "Test", "email": "sep1@test.com", "password": "azertyui123"},
        )
        body = r.json()
        assert "hashed_password" not in body
        assert "password" not in body

    def test_users_me_response_never_contains_hashed_password(self, client, annotator_headers):
        r = client.get("/users/me", headers=annotator_headers)
        body = r.json()
        assert "hashed_password" not in body
        assert "password" not in body
        # Champs attendus, et rien de plus que ça côté sensible
        assert set(body.keys()) == {"id", "email", "full_name", "role", "is_active", "created_at"}

    def test_users_list_response_never_contains_hashed_password(self, client, admin_headers):
        r = client.get("/users", headers=admin_headers)
        for user in r.json():
            assert "hashed_password" not in user

    def test_annotation_response_matches_expected_fields_only(
        self, client, data_manager_headers, annotator_headers, annotator2_headers
    ):
        from tests.conftest import get_user_id

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
        ann1_id = get_user_id(client, annotator_headers)
        ann2_id = get_user_id(client, annotator2_headers)
        client.post(
            f"/campaigns/{campaign_id}/assignments",
            json={"annotator_ids": [ann1_id, ann2_id]},
            headers=data_manager_headers,
        )
        client.patch(f"/campaigns/{campaign_id}/open", headers=data_manager_headers)

        tasks = client.get("/tasks/me", headers=annotator_headers).json()
        r = client.post(f"/tasks/{tasks[0]['id']}/annotations", json={"label": "a"}, headers=annotator_headers)

        expected_fields = {
            "id", "task_id", "annotator_id", "label", "status",
            "reviewer_id", "reviewed_at", "created_at", "updated_at",
        }
        assert set(r.json().keys()) == expected_fields