from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def login(email="lea@docuscope.local", password="Demo123!"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    headers = {"Cookie": f"docuscope_session={response.cookies['docuscope_session']}"}
    client.cookies.clear()
    return headers


def test_conversation_crud_is_persistent_and_owned():
    lea = login()
    marc = login("marc@docuscope.local", "Demo123!")

    created = client.post("/api/conversations", headers=lea, json={"title": "Budget RH"})
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    assert [item["id"] for item in client.get("/api/conversations", headers=lea).json()] == [conversation_id]
    assert client.get(f"/api/conversations/{conversation_id}", headers=marc).status_code == 404
    assert client.delete(f"/api/conversations/{conversation_id}", headers=marc).status_code == 404

    detail = client.get(f"/api/conversations/{conversation_id}", headers=lea)
    assert detail.status_code == 200
    assert detail.json()["messages"] == []
    assert client.delete(f"/api/conversations/{conversation_id}", headers=lea).status_code == 204
    assert client.get(f"/api/conversations/{conversation_id}", headers=lea).status_code == 404


def test_messages_are_persisted_in_order(monkeypatch):
    async def fake_generate(question, context):
        return f"Réponse à : {question}"

    monkeypatch.setattr("app.chat_service.generate", fake_generate)
    headers = login()
    conversation_id = client.post("/api/conversations", headers=headers, json={}).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"question": "Quelle est la politique RH ?"},
    )
    assert response.status_code == 201
    messages = response.json()["messages"]
    assert [item["role"] for item in messages] == ["user", "assistant"]
    assert messages[1]["content"] == "Réponse à : Quelle est la politique RH ?"

    persisted = client.get(f"/api/conversations/{conversation_id}", headers=headers).json()
    assert persisted["messages"] == messages


def test_failed_generation_does_not_persist_partial_exchange(monkeypatch):
    async def fail_generate(question, context):
        raise RuntimeError("LM Studio indisponible")

    monkeypatch.setattr("app.chat_service.generate", fail_generate)
    headers = login()
    conversation_id = client.post("/api/conversations", headers=headers, json={}).json()["id"]

    response = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"question": "Question générale"},
    )
    assert response.status_code == 503
    assert client.get(f"/api/conversations/{conversation_id}", headers=headers).json()["messages"] == []
