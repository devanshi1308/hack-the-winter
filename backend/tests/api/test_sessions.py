"""
API tests for sessions and messages endpoints using FastAPI TestClient.
We monkeypatch db.mongo.get_mongo to an in-memory fake to avoid real DB.
"""

from fastapi.testclient import TestClient
import types
import uuid

from app import app


class FakeMongo:
    def __init__(self):
        self.users = {}
        self.sessions = {}
        self.messages = []

    # sessions
    def create_session(self, data):
        sid = data["session_id"]
        if sid in self.sessions:
            raise ValueError("Session already exists")
        self.sessions[sid] = {
            **data,
            "created_at": "2025-01-01T00:00:00Z",
            "message_count": 0,
            "is_pinned": False,
        }
        return sid

    def list_sessions(self, user_id: str, limit: int = 50):
        items = [s for s in self.sessions.values() if s["user_id"] == user_id]
        return items[:limit]

    def get_session(self, session_id: str):
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, updates: dict) -> bool:
        if session_id not in self.sessions:
            return False
        self.sessions[session_id].update(updates)
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions.pop(session_id)
            # also remove messages
            self.messages = [m for m in self.messages if m["session_id"] != session_id]
            return True
        return False

    # messages
    def add_message(self, msg):
        self.messages.append(msg)
        if msg["session_id"] in self.sessions:
            self.sessions[msg["session_id"]["message_count"]] = self.sessions[msg["session_id"]].get("message_count", 0) + 1
        return uuid.uuid4().hex

    def get_session_messages(self, session_id: str, limit: int = 100):
        items = [m for m in self.messages if m["session_id"] == session_id]
        return items[:limit]

    def get_mood_series(self, user_id: str, days: int = 30):
        # return minimal shape
        return []


client = TestClient(app)


def test_sessions_crud(monkeypatch):
    fake = FakeMongo()

    # monkeypatch get_mongo
    import db.mongo as mongo_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)

    # create session
    resp = client.post("/api/sessions", json={"user_id": "u1", "name": "First"})
    assert resp.status_code == 200
    sid = resp.json()["session_id"]
    assert sid

    # list sessions
    resp = client.get("/api/sessions", params={"user_id": "u1"})
    assert resp.status_code == 200
    sessions = resp.json()["sessions"]
    assert len(sessions) == 1

    # update session
    resp = client.patch(f"/api/sessions/{sid}", json={"is_pinned": True})
    assert resp.status_code == 200

    # delete session
    resp = client.delete(f"/api/sessions/{sid}")
    assert resp.status_code == 200


def test_messages_flow(monkeypatch):
    fake = FakeMongo()

    # monkeypatch get_mongo
    import db.mongo as mongo_mod
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)

    # create session first
    sid = uuid.uuid4().hex
    fake.create_session({"session_id": sid, "user_id": "u1", "name": "S"})

    # add message
    payload = {"session_id": sid, "user_id": "u1", "role": "user", "content": "hello"}
    resp = client.post("/api/messages", json=payload)
    assert resp.status_code == 200
    mid = resp.json()["message_id"]
    assert mid

    # fetch messages
    resp = client.get("/api/messages", params={"session_id": sid, "limit": 10})
    assert resp.status_code == 200
    msgs = resp.json()["messages"]
    assert len(msgs) == 1
