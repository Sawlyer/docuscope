import asyncio

from app import llm


def test_general_question_is_always_sent_to_lm_studio(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"output": [{"type": "message", "content": "Deux."}]}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, json):
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(llm.settings, "mock_llm", False)
    monkeypatch.setattr(llm.httpx, "AsyncClient", lambda **kwargs: FakeClient())

    assert asyncio.run(llm.generate("combien font 1+1", "")) == "Deux."
    assert "combien font 1+1" in captured["json"]["input"]
