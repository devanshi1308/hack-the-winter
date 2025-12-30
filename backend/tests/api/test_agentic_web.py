"""
API test for /agent/exercise validating web-augmented agentic RAG.
Monkeypatch WebSearch to return deterministic results without network.
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


def test_agent_exercise_with_fake_web(monkeypatch):
    fake = FakeMongo()

    # Patch Mongo
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    # Patch WebSearch.search to return snippets
    import utils.web_search as ws_mod
    import app as app_mod

    class DummyWS:
        def search(self, query: str, max_results: int = 5):
            return [
                {"title": "Tip 1", "url": "http://e1", "content": "Breathe slowly."},
                {"title": "Tip 2", "url": "http://e2", "content": "Count to five."},
            ]

    # Patch both module where class is defined and where it's imported
    monkeypatch.setattr(ws_mod, "WebSearch", lambda: DummyWS())
    monkeypatch.setattr(app_mod, "WebSearch", lambda: DummyWS())

    payload = {
        "user_id": "uweb",
        "session_id": "sweb",
        "target_facets": ["self_regulation"],
        "context_tags": ["stress"],
        "duration_hint": "2 minutes",
        "query": "how to calm down quickly"
    }

    resp = client.post("/agent/exercise", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("web_used") is True
    assert isinstance(data.get("exercise"), dict)
    assert len(fake.messages) >= 1
