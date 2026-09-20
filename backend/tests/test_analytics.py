from fastapi.testclient import TestClient

from app import store
from app.main import app

client = TestClient(app)


def auth(email="admin@docuscope.local", password="Admin123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


def payload(query=""):
    return client.get(f"/api/analytics{query}", headers=auth()).json()


def test_series_covers_every_day_of_the_window():
    data = payload()
    assert data["days"] == 14
    assert len(data["questions_per_day"]) == 14
    assert data["questions_per_day"] == sorted(data["questions_per_day"], key=lambda item: item["date"])
    assert sum(item["count"] for item in data["questions_per_day"]) == data["questions_in_period"]


def test_window_is_configurable_and_clamped():
    assert payload("?days=7")["days"] == 7
    assert len(payload("?days=7")["questions_per_day"]) == 7
    assert payload("?days=500")["days"] == 90
    assert payload("?days=0")["days"] == 1


def test_document_counts_come_from_structured_metadata(monkeypatch):
    """A title containing a comma must not inflate the count; meta carries ids."""

    async def fake_generate(question, context):
        return "ok"

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    before = {item["key"]: item["count"] for item in payload()["top_documents"]}
    client.post("/api/chat", headers=auth("lea@docuscope.local", "Demo123!"), json={"question": "liste d'intégration"})
    after = {item["key"]: item["count"] for item in payload()["top_documents"]}
    assert sum(after.values()) > sum(before.values())
    assert set(after) <= set(store.DOCUMENTS)


def test_team_activity_counts_every_team_of_the_actor():
    client.post("/api/chat", headers=auth("claire@docuscope.local", "Demo123!"), json={"question": "entretiens annuels"})
    teams = {item["key"]: item["count"] for item in payload()["activity_by_team"]}
    assert set(teams) == {"leadership", "rh", "finance", "engineering", "sales"}
    # Claire belongs to rh and sales, so each of her questions counts for both.
    assert teams["rh"] > 0


def test_alerts_flag_a_document_nobody_can_reach():
    assert payload()["alerts"]["unreachable_documents"] == []
    client.patch(
        "/api/documents/doc-pipeline/access",
        headers=auth(),
        json={"allowed_roles": [], "allowed_teams": []},
    )
    flagged = payload()["alerts"]["unreachable_documents"]
    assert [item["id"] for item in flagged] == ["doc-pipeline"]


def test_alerts_flag_members_without_a_team_and_empty_teams():
    assert payload()["alerts"]["members_without_team"] == []
    client.patch("/api/users/u-tom", headers=auth(), json={"teams": []})
    data = payload()
    assert [item["email"] for item in data["alerts"]["members_without_team"]] == ["tom@docuscope.local"]

    client.post("/api/teams", headers=auth(), json={"slug": "design", "label": "Conception"})
    assert "design" in {item["key"] for item in payload()["alerts"]["empty_teams"]}


def test_analytics_is_admin_only():
    assert client.get("/api/analytics", headers=auth("lea@docuscope.local", "Demo123!")).status_code == 403
    assert client.get("/api/analytics").status_code == 401
