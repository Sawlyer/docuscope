from fastapi.testclient import TestClient

from app.main import app
from app.security import create_token


def login(client: TestClient, email="admin@docuscope.local", password="Admin123!"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_sets_http_only_cookie_and_logout_clears_it():
    client = TestClient(app)
    response = login(client)
    cookie = response.headers["set-cookie"].lower()
    assert response.status_code == 200
    assert "docuscope_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "access_token" not in response.json()
    assert client.get("/api/auth/me").status_code == 200

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").status_code == 401


def test_bearer_token_without_cookie_is_rejected():
    client = TestClient(app)
    token = create_token("admin@docuscope.local", "ADMIN")
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_role_changes_and_deletion_invalidate_stale_cookie_authorization():
    sofia = TestClient(app)
    admin = TestClient(app)
    assert login(sofia, "sofia@docuscope.local", "Demo123!").status_code == 200
    assert login(admin).status_code == 200
    assert sofia.get("/api/users").status_code == 200

    assert admin.patch("/api/users/u-sofia", json={"role": "EMPLOYEE"}).status_code == 200
    assert sofia.get("/api/users").status_code == 403
    assert admin.delete("/api/users/u-sofia").status_code == 204
    assert sofia.get("/api/auth/me").status_code == 401


def test_cross_origin_mutation_is_rejected_but_same_origin_and_cli_are_allowed():
    client = TestClient(app)
    assert login(client).status_code == 200
    payload = {"slug": "security", "label": "Sécurité"}
    assert client.post("/api/teams", json=payload, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/teams", json=payload, headers={"Origin": "http://localhost:18000"}).status_code == 201
    assert client.delete("/api/teams/security").status_code == 204
