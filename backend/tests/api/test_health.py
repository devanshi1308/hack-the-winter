"""
API test for /health DB connectivity flag. We monkeypatch get_mongo to a fake
with an admin ping that succeeds.
"""

from fastapi.testclient import TestClient
from app import app


class FakeAdmin:
    def command(self, name):
        assert name == "ping"
        return {"ok": 1}


class FakeClient:
    def __init__(self):
        self.admin = FakeAdmin()


class FakeMongo:
    def __init__(self):
        self.client = FakeClient()


client = TestClient(app)


def test_health_db_connected(monkeypatch):
    import db.mongo as mongo_mod
    import app as app_mod
    fake = FakeMongo()
    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("db_connected") is True
