from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


def auth(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


def test_delete_team_cascades_to_members_and_documents():
    assert client.delete("/api/teams/finance", headers=auth()).status_code == 204
    assert "finance" not in {team["slug"] for team in client.get("/api/teams", headers=auth()).json()}
    marc = next(user for user in client.get("/api/users", headers=auth()).json() if user["email"] == "marc@docuscope.local")
    assert marc["teams"] == []
    assert store.DOCUMENTS["doc-finance"].allowed_teams == set()


def test_deleting_a_team_revokes_the_access_it_granted():
    """The cascade has to reach retrieval, not just the team registry."""
    marc = auth("marc@docuscope.local", "Demo123!")
    before = {item["title"] for item in client.get("/api/documents", headers=marc).json()}
    assert "Rapport financier T2" in before

    client.delete("/api/teams/finance", headers=auth())

    after = {item["title"] for item in client.get("/api/documents", headers=marc).json()}
    assert "Rapport financier T2" not in after


def test_delete_team_is_audited_with_its_impact():
    client.delete("/api/teams/finance", headers=auth())
    event = client.get("/api/audit?action=TEAM_DELETED", headers=auth()).json()[0]
    assert event["target"] == "Finance"
    assert "1 membre(s)" in event["detail"]
    assert "1 document(s)" in event["detail"]


def test_delete_unknown_team_is_not_found():
    assert client.delete("/api/teams/nope", headers=auth()).status_code == 404


def test_delete_document():
    assert client.delete("/api/documents/doc-pipeline", headers=auth()).status_code == 204
    assert "doc-pipeline" not in store.DOCUMENTS
    event = client.get("/api/audit?action=DOCUMENT_DELETED", headers=auth()).json()[0]
    assert event["target"] == "Revue du pipeline commercial"


def test_deleted_document_leaves_the_access_preview():
    before = client.get("/api/users/u-tom/access", headers=auth()).json()
    assert before["total_count"] == len(store.DOCUMENTS)
    client.delete("/api/documents/doc-pipeline", headers=auth())
    after = client.get("/api/users/u-tom/access", headers=auth()).json()
    assert after["total_count"] == before["total_count"] - 1
    assert "Revue du pipeline commercial" not in {entry["title"] for entry in after["entries"]}


def test_delete_unknown_document_is_not_found():
    assert client.delete("/api/documents/doc-ghost", headers=auth()).status_code == 404


def test_deletion_endpoints_are_admin_only():
    employee = auth("lea@docuscope.local", "Demo123!")
    assert client.delete("/api/teams/finance", headers=employee).status_code == 403
    assert client.delete("/api/documents/doc-pipeline", headers=employee).status_code == 403
