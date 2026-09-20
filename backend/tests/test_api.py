from fastapi.testclient import TestClient

from app.main import app
from app.config import settings

client = TestClient(app)


def token(email="lea@docuscope.local", password="Demo123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    cookie = response.cookies["docuscope_session"]
    client.cookies.clear()
    return cookie


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_login_and_role():
    response = client.post("/api/auth/login", json={"email": "admin@docuscope.local", "password": "Admin123!"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "ADMIN"


def test_document_isolation():
    response = client.get("/api/documents", headers={"Cookie": f"docuscope_session={token()}"})
    titles = {item["title"] for item in response.json()}
    assert "Politique RH 2026" in titles
    assert "Rapport financier T2" not in titles


def test_chat_never_uses_forbidden_document(monkeypatch):
    captured = {}

    async def fake_generate(question, context):
        captured["context"] = context
        return "safe"

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    response = client.post("/api/chat", headers={"Cookie": f"docuscope_session={token()}"}, json={"question": "finance report revenue"})
    assert response.status_code == 200
    assert "Rapport financier T2" not in captured["context"]


def test_unrelated_question_returns_no_context(monkeypatch):
    captured = {}

    async def fake_generate(question, context):
        captured["context"] = context
        return "Je ne trouve pas cette information."

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    response = client.post("/api/chat", headers={"Cookie": f"docuscope_session={token()}"}, json={"question": "qui est le chef de la boîte"})
    assert response.status_code == 200
    assert captured["context"] == ""
    assert response.json()["sources"] == []


def test_document_content_respects_permissions():
    response = client.get(f"/api/documents/doc-rh/content", headers={"Cookie": f"docuscope_session={token()}"})
    assert response.status_code == 200
    forbidden = client.get("/api/documents/doc-finance/content", headers={"Cookie": f"docuscope_session={token()}"})
    assert forbidden.status_code == 403


def test_chat_accepts_lm_studio_block_output(monkeypatch):
    from app import llm

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output": [
                {"type": "reasoning", "content": "internal"},
                {"type": "message", "content": "Alice Martin dirige l'entreprise."},
            ]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(llm.settings, "mock_llm", False)

    import asyncio
    answer = asyncio.run(llm.generate("qui dirige l'entreprise", "[1] Organigramme: Alice Martin dirige l'entreprise."))
    assert answer == "Alice Martin dirige l'entreprise."


def test_lm_studio_prompt_requires_french_and_general_answers(monkeypatch):
    from app import llm
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output": [{"type": "message", "content": "2"}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient())
    monkeypatch.setattr(llm.settings, "mock_llm", False)

    import asyncio
    assert asyncio.run(llm.generate("quelle est la politique générale", "")) == "2"
    assert "français" in captured["payload"]["system_prompt"]
    assert "questions générales" in captured["payload"]["system_prompt"]


def test_retrieval_follows_permission_changes(monkeypatch):
    """Grant, then revoke: the chat context must track the permission, not the seed."""
    contexts = []

    async def fake_generate(question, context):
        contexts.append(context)
        return "safe"

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    admin = {"Cookie": f"docuscope_session={token('admin@docuscope.local', 'Admin123!')}"}
    lea = {"Cookie": f"docuscope_session={token()}"}

    client.patch("/api/documents/doc-finance/access", headers=admin, json={"allowed_roles": ["ADMIN"], "allowed_teams": ["finance", "rh"]})
    client.post("/api/chat", headers=lea, json={"question": "finance report revenue"})
    assert "Rapport financier T2" in contexts[-1]

    client.patch("/api/documents/doc-finance/access", headers=admin, json={"allowed_roles": ["ADMIN"], "allowed_teams": ["finance"]})
    client.post("/api/chat", headers=lea, json={"question": "finance report revenue"})
    assert "Rapport financier T2" not in contexts[-1]

    client.patch("/api/users/u-lea", headers=admin, json={"teams": ["finance"]})
    client.post("/api/chat", headers=lea, json={"question": "finance report revenue"})
    assert "Rapport financier T2" in contexts[-1]
