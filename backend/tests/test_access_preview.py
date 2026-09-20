from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def auth(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


def test_preview_covers_every_document_with_a_reason():
    payload = client.get("/api/users/u-lea/access", headers=auth()).json()
    assert payload["user"]["email"] == "lea@docuscope.local"
    entries = {entry["title"]: entry for entry in payload["entries"]}
    assert entries["Politique RH 2026"]["allowed"] is True
    assert entries["Politique RH 2026"]["reason"] == "équipe Ressources humaines"
    assert entries["Manuel de l'employé"]["reason"] == "rôle Employé"
    assert entries["Rapport financier T2"]["allowed"] is False
    assert entries["Rapport financier T2"]["reason"] is None
    assert payload["allowed_count"] == sum(1 for entry in payload["entries"] if entry["allowed"])


def test_preview_agrees_with_what_that_member_actually_sees():
    """The preview and the member's own document list are two views of one rule."""
    preview = client.get("/api/users/u-marc/access", headers=auth()).json()
    allowed = {entry["title"] for entry in preview["entries"] if entry["allowed"]}
    own = {item["title"] for item in client.get("/api/documents", headers=auth("marc@docuscope.local", "Demo123!")).json()}
    assert allowed == own


def test_preview_follows_a_permission_change():
    client.patch("/api/users/u-marc", headers=auth(), json={"teams": []})
    preview = client.get("/api/users/u-marc/access", headers=auth()).json()
    entries = {entry["title"]: entry for entry in preview["entries"]}
    assert entries["Rapport financier T2"]["allowed"] is False


def test_preview_is_admin_only_and_404s_on_unknown_member():
    assert client.get("/api/users/u-lea/access", headers=auth("lea@docuscope.local", "Demo123!")).status_code == 403
    assert client.get("/api/users/u-ghost/access", headers=auth()).status_code == 404
