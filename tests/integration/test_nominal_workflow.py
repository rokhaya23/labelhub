"""Parcours nominal complet du sujet LabelHub, de bout en bout via l'API
HTTP réelle : inscription -> promotion -> dataset -> campagne -> ouverture ->
soumission -> review -> progression."""

from tests.conftest import get_user_id


class TestNominalWorkflow:
    def test_full_labelhub_workflow(self, client, db_session):
        from app.models.role import RoleEnum
        from tests.conftest import _create_user_and_login

        admin_headers = _create_user_and_login(client, db_session, "admin@flow.com", RoleEnum.ADMIN)
        dm_headers = _create_user_and_login(client, db_session, "dm@flow.com", RoleEnum.DATA_MANAGER)
        ann1_headers = _create_user_and_login(client, db_session, "ann1@flow.com", RoleEnum.ANNOTATOR)
        ann2_headers = _create_user_and_login(client, db_session, "ann2@flow.com", RoleEnum.ANNOTATOR)
        reviewer_headers = _create_user_and_login(client, db_session, "rev@flow.com", RoleEnum.REVIEWER)

        # 1. Dataset + items
        r = client.post("/datasets", json={"name": "Avis clients"}, headers=dm_headers)
        assert r.status_code == 201
        dataset_id = r.json()["id"]

        r = client.post(
            f"/datasets/{dataset_id}/items",
            json={"items": [f"avis numero {i}" for i in range(10)]},
            headers=dm_headers,
        )
        assert r.status_code == 201
        assert len(r.json()["items"]) == 10

        # 2. Campagne avec labels fixés
        r = client.post(
            "/campaigns",
            json={"name": "Sentiment", "dataset_id": dataset_id, "allowed_labels": ["positif", "negatif", "neutre"]},
            headers=dm_headers,
        )
        assert r.status_code == 201
        campaign_id = r.json()["id"]
        assert r.json()["status"] == "draft"

        # 3. Ouverture refusée sans annotateurs assignés
        r = client.patch(f"/campaigns/{campaign_id}/open", headers=dm_headers)
        assert r.status_code == 400

        # 4. Assignation puis ouverture réussie
        ann1_id = get_user_id(client, ann1_headers)
        ann2_id = get_user_id(client, ann2_headers)
        r = client.post(
            f"/campaigns/{campaign_id}/assignments",
            json={"annotator_ids": [ann1_id, ann2_id]},
            headers=dm_headers,
        )
        assert r.status_code == 200

        r = client.patch(f"/campaigns/{campaign_id}/open", headers=dm_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "open"

        # 5bis. Affectation du reviewer à cette campagne (requis pour valider)
        reviewer_id = get_user_id(client, reviewer_headers)
        r = client.post(
            f"/campaigns/{campaign_id}/reviewers", json={"reviewer_ids": [reviewer_id]}, headers=dm_headers
        )
        assert r.status_code == 200

        # 5. Répartition des tâches (5 par annotateur)
        tasks_ann1 = client.get("/tasks/me", headers=ann1_headers).json()
        tasks_ann2 = client.get("/tasks/me", headers=ann2_headers).json()
        assert len(tasks_ann1) == 5
        assert len(tasks_ann2) == 5

        # 6. Soumission d'une annotation avec un label valide
        r = client.post(
            f"/tasks/{tasks_ann1[0]['id']}/annotations", json={"label": "positif"}, headers=ann1_headers
        )
        assert r.status_code == 201
        annotation_id = r.json()["id"]
        assert r.json()["status"] == "submitted"

        # 7. Label hors de la liste autorisée refusé
        r = client.post(
            f"/tasks/{tasks_ann1[1]['id']}/annotations", json={"label": "hors_liste"}, headers=ann1_headers
        )
        assert r.status_code == 400

        # 8. Le reviewer voit l'annotation soumise
        r = client.get(f"/campaigns/{campaign_id}/annotations?status_filter=submitted", headers=reviewer_headers)
        assert r.status_code == 200
        assert any(a["id"] == annotation_id for a in r.json())

        # 9. Auto-review bloquée
        r = client.patch(
            f"/annotations/{annotation_id}/review", json={"decision": "approve"}, headers=ann1_headers
        )
        assert r.status_code == 403

        # 10. Review par le reviewer
        r = client.patch(
            f"/annotations/{annotation_id}/review", json={"decision": "approve"}, headers=reviewer_headers
        )
        assert r.status_code == 200
        assert r.json()["status"] == "approved"

        # 11. Progression cohérente
        r = client.get(f"/campaigns/{campaign_id}/progress", headers=dm_headers)
        assert r.status_code == 200
        progress = r.json()
        assert progress["tasks_total"] == 10
        assert progress["tasks_submitted"] == 1
        assert progress["annotations_approved"] == 1

        # 12. Fermeture de la campagne
        r = client.patch(f"/campaigns/{campaign_id}/close", headers=dm_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "closed"