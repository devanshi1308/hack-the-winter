"""
API test for /rag/exercise using FastAPI TestClient.
Ensures endpoint returns an exercise and tolerates offline environments.
Also validates optional message persistence when session/user provided.
"""

from fastapi.testclient import TestClient
from app import app


class FakeMongo:
    def __init__(self):
        self.messages = []

    def add_message(self, msg):
        self.messages.append(msg)
        return "m1"


client = TestClient(app)


def test_rag_exercise_offline_and_persist(monkeypatch):
    fake = FakeMongo()

    # Patch both source and app symbol
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    payload = {
        "user_id": "u1",
        "session_id": "s1",
        "target_facets": ["self_awareness"],
        "context_tags": ["work"],
        "duration_hint": "2 minutes",
        "query": "tips to calm down"
    }

    resp = client.post("/rag/exercise", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "exercise" in data
    assert isinstance(data["exercise"], dict)
    assert "offline" in data

    # Messages persisted best-effort
    assert len(fake.messages) >= 1  # allow 1 or 2 depending on errors
