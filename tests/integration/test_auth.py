"""Tests d'intégration authentification : via l'API HTTP réelle (TestClient),
pas les repositories directement."""


class TestAuth:
    def test_register_creates_annotator_by_default(self, client):
        r = client.post(
            "/auth/register",
            json={"full_name": "Nouveau", "email": "new@test.com", "password": "azertyui123"},
        )
        assert r.status_code == 201
        assert r.json()["role"] == "annotator"

    def test_register_duplicate_email_rejected(self, client):
        payload = {"full_name": "X", "email": "dup@test.com", "password": "azertyui123"}
        r1 = client.post("/auth/register", json=payload)
        r2 = client.post("/auth/register", json=payload)
        assert r1.status_code == 201
        assert r2.status_code == 400

    def test_login_wrong_password_rejected(self, client):
        client.post(
            "/auth/register",
            json={"full_name": "X", "email": "wp@test.com", "password": "azertyui123"},
        )
        r = client.post("/auth/login", data={"username": "wp@test.com", "password": "mauvais"})
        assert r.status_code == 401

    def test_login_unknown_email_rejected(self, client):
        r = client.post("/auth/login", data={"username": "inconnu@test.com", "password": "x"})
        assert r.status_code == 401

    def test_protected_route_requires_token(self, client):
        r = client.get("/users/me")
        assert r.status_code == 401

    def test_protected_route_rejects_garbage_token(self, client):
        r = client.get("/users/me", headers={"Authorization": "Bearer ceci-nest-pas-un-token"})
        assert r.status_code == 401