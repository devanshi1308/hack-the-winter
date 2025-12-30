"""
API tests for new orchestrator-based features:
- Adaptive chat with modes
- Weekly review
- Ingest endpoint
- Mood timeline
- Alert test
"""

from fastapi.testclient import TestClient
from app import app


class FakeMongo:
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.messages = []
        self.documents = []
    
    def get_user(self, user_id: str):
        return self.users.get(user_id)
    
    def create_user(self, data):
        self.users[data["user_id"]] = data
        return data["user_id"]
    
    def update_user(self, user_id: str, updates: dict):
        if user_id in self.users:
            self.users[user_id].update(updates)
            return True
        return False
    
    def add_message(self, msg):
        self.messages.append(msg)
        return "m1"
    
    def get_session_messages(self, session_id: str, limit: int = 100):
        return [m for m in self.messages if m.get("session_id") == session_id][:limit]
    
    def get_recent_messages(self, user_id: str, days: int = 30, limit: int = 100):
        return [m for m in self.messages if m.get("user_id") == user_id][:limit]
    
    def get_mood_series(self, user_id: str, days: int = 30):
        return [{"_id": "2025-01-01", "avg_mood": 55.0, "count": 5}]
    
    class client:
        class admin:
            @staticmethod
            def command(name):
                return {"ok": 1}


client = TestClient(app)


def test_adaptive_chat_qa_mode(monkeypatch):
    fake = FakeMongo()
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)
    
    payload = {
        "user_id": "u1",
        "message": "I feel anxious today",
        "mode": "qa"
    }
    
    resp = client.post("/api/chat/s1", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert "citations" in data
    assert "sentiment" in data


def test_weekly_review(monkeypatch):
    fake = FakeMongo()
    fake.messages = [
        {"session_id": "s1", "user_id": "u1", "role": "user", "content": "test", "metadata": {"mood_index": 60}, "timestamp": "2025-01-01T00:00:00Z"},
    ]
    
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)
    
    payload = {"session_id": "s1", "user_id": "u1"}
    resp = client.post("/api/weekly-review", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "goals" in data
    assert "insights" in data


def test_ingest_endpoint(monkeypatch):
    fake = FakeMongo()
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)
    
    payload = {
        "urls": ["https://example.com/article"],
        "youtube_ids": ["abc123"],
        "user_id": "u1"
    }
    
    resp = client.post("/api/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "docs_indexed" in data
    assert "sources" in data


def test_mood_timeline(monkeypatch):
    fake = FakeMongo()
    import db.mongo as mongo_mod
    import app as app_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)
    
    resp = client.get("/api/analytics/mood_timeline?user_id=u1&days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
