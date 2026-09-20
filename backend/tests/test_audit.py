from fastapi.testclient import TestClient

from app.database import session_scope
from app.main import app
from app.repositories import AuditRepository, UserRepository

client = TestClient(app)


def token(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    cookie = response.cookies["docuscope_session"]
    client.cookies.clear()
    return cookie


def auth(email="admin@docuscope.local", password="Admin123!"):
    return {"Cookie": f"docuscope_session={token(email, password)}"}


def test_record_appends_a_typed_event():
    with session_scope() as session:
        repository = AuditRepository(session)
        actor = UserRepository(session).get_by_email("admin@docuscope.local")
        before = len(repository.query(limit=1000))
        event = repository.record(actor, "USER_UPDATED", "u-lea", "Équipes : Ressources humaines, Commercial")
        assert len(repository.query(limit=1000)) == before + 1
        assert event.actor_name == "Amélie Martin"
        assert event.action == "USER_UPDATED"
        assert event.target == "u-lea"


def test_login_is_audited():
    with session_scope() as session:
        before = len(AuditRepository(session).query(action="LOGIN", limit=1000))
    token()
    with session_scope() as session:
        assert len(AuditRepository(session).query(action="LOGIN", limit=1000)) == before + 1


def test_question_is_audited_with_its_sources(monkeypatch):
    async def fake_generate(question, context):
        return "safe"

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    response = client.post(
        "/api/chat",
        headers=auth("lea@docuscope.local", "Demo123!"),
        json={"question": "onboarding checklist"},
    )
    assert response.status_code == 200
    event = client.get("/api/audit?action=QUESTION_ASKED", headers=auth()).json()[0]
    assert event["actor_email"] == "lea@docuscope.local"
    assert "Politique RH 2026" in event["detail"]


def test_audit_endpoint_is_admin_only():
    assert client.get("/api/audit", headers=auth("lea@docuscope.local", "Demo123!")).status_code == 403
    assert client.get("/api/audit").status_code == 401


def test_audit_endpoint_returns_newest_first_and_filters():
    client.post("/api/teams", headers=auth(), json={"slug": "design", "label": "Design"})
    payload = client.get("/api/audit", headers=auth()).json()
    assert payload[0]["action"] in ("TEAM_CREATED", "LOGIN")
    filtered = client.get("/api/audit?action=TEAM_CREATED", headers=auth()).json()
    assert filtered
    assert {item["action"] for item in filtered} == {"TEAM_CREATED"}
    by_actor = client.get("/api/audit?actor=lea@docuscope.local", headers=auth()).json()
    assert all(item["actor_email"] == "lea@docuscope.local" for item in by_actor)


def test_dashboard_activity_is_scoped_for_non_admins():
    """The feed names members and permission changes; an EMPLOYEE sees only their own."""
    payload = client.get("/api/dashboard", headers=auth("lea@docuscope.local", "Demo123!")).json()
    assert payload["activity"]
    assert {event["actor_email"] for event in payload["activity"]} == {"lea@docuscope.local"}

    admin_payload = client.get("/api/dashboard", headers=auth()).json()
    assert len({event["actor_email"] for event in admin_payload["activity"]}) >= 1
