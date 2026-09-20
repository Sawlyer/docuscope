from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


def auth(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


NEW = {"email": "Zoe@Docuscope.Local", "name": "Zoe Laurent", "password": "Demo123!", "role": "EMPLOYEE", "teams": ["rh"]}


def test_create_member_normalises_email_and_allows_login():
    response = client.post("/api/users", headers=auth(), json=NEW)
    assert response.status_code == 201
    assert response.json()["email"] == "zoe@docuscope.local"
    assert client.post("/api/auth/login", json={"email": "zoe@docuscope.local", "password": "Demo123!"}).status_code == 200


def test_create_records_an_audit_event():
    client.post("/api/users", headers=auth(), json=NEW)
    event = client.get("/api/audit?action=USER_CREATED", headers=auth()).json()[0]
    assert event["target"] == "zoe@docuscope.local"


def test_update_role_and_teams():
    response = client.patch("/api/users/u-lea", headers=auth(), json={"role": "ADMIN", "teams": ["rh", "sales"]})
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert response.json()["teams"] == ["rh", "sales"]
    persisted = next(user for user in client.get("/api/users", headers=auth()).json() if user["id"] == "u-lea")
    assert persisted["teams"] == ["rh", "sales"]


def test_delete_member():
    assert client.delete("/api/users/u-tom", headers=auth()).status_code == 204
    assert "tom@docuscope.local" not in {user["email"] for user in client.get("/api/users", headers=auth()).json()}
    assert client.get("/api/audit?action=USER_DELETED", headers=auth()).json()[0]["target"] == "tom@docuscope.local"


def test_cannot_delete_yourself():
    response = client.delete("/api/users/u-admin", headers=auth())
    assert response.status_code == 409
    assert "propre compte" in response.json()["detail"]


def test_the_workspace_always_keeps_an_administrator():
    """An admin can remove every other admin, but never the seat they sit on."""
    assert client.delete("/api/users/u-sofia", headers=auth()).status_code == 204
    assert {user["id"] for user in client.get("/api/users", headers=auth()).json() if user["role"] == "ADMIN"} == {"u-admin"}
    assert client.delete("/api/users/u-admin", headers=auth()).status_code == 409
    assert "admin@docuscope.local" in {user["email"] for user in client.get("/api/users", headers=auth()).json()}


def test_cannot_demote_the_last_admin():
    client.patch("/api/users/u-sofia", headers=auth(), json={"role": "EMPLOYEE"})
    response = client.patch("/api/users/u-admin", headers=auth(), json={"role": "EMPLOYEE"})
    assert response.status_code == 409
    assert "Dernier administrateur" in response.json()["detail"]
    admin = next(user for user in client.get("/api/users", headers=auth()).json() if user["id"] == "u-admin")
    assert admin["role"] == "ADMIN"


def test_duplicate_email_is_rejected():
    payload = dict(NEW, email="lea@docuscope.local")
    response = client.post("/api/users", headers=auth(), json=payload)
    assert response.status_code == 409
    assert "déjà" in response.json()["detail"]


def test_unknown_team_is_rejected():
    payload = dict(NEW, teams=["nope"])
    response = client.post("/api/users", headers=auth(), json=payload)
    assert response.status_code == 422
    assert "nope" in response.json()["detail"]


def test_unknown_role_is_rejected():
    payload = dict(NEW, role="ROOT")
    assert client.post("/api/users", headers=auth(), json=payload).status_code == 422


def test_unknown_user_is_not_found():
    assert client.patch("/api/users/u-ghost", headers=auth(), json={"role": "ADMIN"}).status_code == 404
    assert client.delete("/api/users/u-ghost", headers=auth()).status_code == 404


def test_employee_cannot_manage_members():
    employee = auth("lea@docuscope.local", "Demo123!")
    assert client.post("/api/users", headers=employee, json=NEW).status_code == 403
    assert client.patch("/api/users/u-marc", headers=employee, json={"role": "ADMIN"}).status_code == 403
    assert client.delete("/api/users/u-marc", headers=employee).status_code == 403
