from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


def auth(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


def test_teams_list_members_and_documents():
    teams = {team["slug"]: team for team in client.get("/api/teams", headers=auth()).json()}
    assert teams["rh"]["label"] == "Ressources humaines"
    assert "lea@docuscope.local" in {member["email"] for member in teams["rh"]["members"]}
    assert "Politique RH 2026" in {document["title"] for document in teams["rh"]["documents"]}
    assert teams["finance"]["member_count"] == len(teams["finance"]["members"])


def test_create_team():
    response = client.post("/api/teams", headers=auth(), json={"slug": "Design", "label": "Conception"})
    assert response.status_code == 201
    assert response.json()["slug"] == "design"
    assert "design" in {team["slug"] for team in client.get("/api/teams", headers=auth()).json()}
    events = client.get("/api/audit?action=TEAM_CREATED", headers=auth()).json()
    assert events[0]["target"] == "Conception"


def test_duplicate_team_is_rejected():
    assert client.post("/api/teams", headers=auth(), json={"slug": "rh", "label": "Ressources humaines"}).status_code == 409


def test_change_document_access_and_audit_it():
    response = client.patch(
        "/api/documents/doc-finance/access",
        headers=auth(),
        json={"allowed_roles": ["ADMIN"], "allowed_teams": ["finance", "leadership"]},
    )
    assert response.status_code == 200
    assert store.DOCUMENTS["doc-finance"].allowed_teams == {"finance", "leadership"}
    events = client.get("/api/audit?action=DOCUMENT_ACCESS_CHANGED", headers=auth()).json()
    assert events[0]["target"] == "Rapport financier T2"


def test_changing_access_changes_what_a_member_retrieves():
    employee = auth("lea@docuscope.local", "Demo123!")
    before = {item["title"] for item in client.get("/api/documents", headers=employee).json()}
    assert "Rapport financier T2" not in before
    client.patch(
        "/api/documents/doc-finance/access",
        headers=auth(),
        json={"allowed_roles": ["ADMIN"], "allowed_teams": ["finance", "rh"]},
    )
    after = {item["title"] for item in client.get("/api/documents", headers=employee).json()}
    assert "Rapport financier T2" in after


def test_document_access_rejects_unknown_team_role_and_document():
    assert client.patch("/api/documents/doc-rh/access", headers=auth(), json={"allowed_roles": ["ADMIN"], "allowed_teams": ["nope"]}).status_code == 422
    assert client.patch("/api/documents/doc-rh/access", headers=auth(), json={"allowed_roles": ["ROOT"], "allowed_teams": []}).status_code == 422
    assert client.patch("/api/documents/doc-ghost/access", headers=auth(), json={"allowed_roles": [], "allowed_teams": []}).status_code == 404


def test_matrix_has_one_row_per_role_and_team():
    matrix = client.get("/api/access-matrix", headers=auth()).json()
    assert {document["id"] for document in matrix["documents"]} == set(store.DOCUMENTS)
    roles = [row for row in matrix["rows"] if row["kind"] == "role"]
    teams = [row for row in matrix["rows"] if row["kind"] == "team"]
    assert {row["key"] for row in roles} == {"ADMIN", "EMPLOYEE"}
    assert {row["key"] for row in teams} == set(client.get("/api/team-labels", headers=auth()).json())
    rh = next(row for row in teams if row["key"] == "rh")
    assert rh["access"]["doc-rh"] is True
    assert rh["access"]["doc-finance"] is False


def test_access_endpoints_are_admin_only():
    employee = auth("lea@docuscope.local", "Demo123!")
    assert client.get("/api/teams", headers=employee).status_code == 403
    assert client.get("/api/access-matrix", headers=employee).status_code == 403
    assert client.patch("/api/documents/doc-rh/access", headers=employee, json={"allowed_roles": [], "allowed_teams": []}).status_code == 403


def test_team_labels_are_readable_by_any_signed_in_account():
    """Employees need the display names; only membership detail is admin-only."""
    labels = client.get("/api/team-labels", headers=auth("lea@docuscope.local", "Demo123!")).json()
    assert labels["leadership"] == "Direction"
    assert set(labels) == {"leadership", "rh", "finance", "engineering", "sales"}
    assert client.get("/api/team-labels").status_code == 401
