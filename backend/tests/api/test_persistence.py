"""
API tests to verify journal and chat persistence to Mongo with mood_index metadata.
"""

from fastapi.testclient import TestClient
from app import app


class FakeMongo:
    def __init__(self):
        self.messages = []

    def add_message(self, msg):
        self.messages.append(msg)
        return "m"


client = TestClient(app)


def test_analyze_entry_persists(monkeypatch):
    fake = FakeMongo()
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    payload = {
        "user_id": "u1",
        "session_id": "s1",
        "journal": "I feel okay today",
    }
    resp = client.post("/ai/analyze-entry", json=payload)
    assert resp.status_code == 200
    # best-effort: at least user message persisted
    assert len(fake.messages) >= 1
    # mood index present
    assert any("mood_index" in m.get("metadata", {}) for m in fake.messages)


def test_chat_mood_persists(monkeypatch):
    fake = FakeMongo()
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    payload = {
        "user_id": "u1",
        "session_id": "s1",
        "message": "I am stressed but hopeful",
    }
    resp = client.post("/chat/mood", json=payload)
    assert resp.status_code == 200
    assert len(fake.messages) >= 1
    assert any("mood_index" in m.get("metadata", {}) for m in fake.messages)
