"""
API test for local folder ingestion via /rag/ingest (server-side docs).
We create a temporary directory with a dummy .pdf file to trigger the offline
fallback path and ensure metadata is recorded with default user_id 'system'.
"""

from fastapi.testclient import TestClient
from app import app
import tempfile
import os


class FakeMongo:
    def __init__(self):
        self.docs = []

    def add_document(self, doc_data: dict) -> str:
        self.docs.append(doc_data)
        return doc_data["doc_id"]


client = TestClient(app)


def test_local_ingest_folder(monkeypatch):
    fake = FakeMongo()

    import db.mongo as mongo_mod
    import app as app_mod

    monkeypatch.setattr(mongo_mod, "get_mongo", lambda: fake)
    monkeypatch.setattr(app_mod, "get_mongo", lambda: fake)

    with tempfile.TemporaryDirectory() as tmpdir:
        # create a small dummy 'pdf'
        dummy_path = os.path.join(tmpdir, "doc1.pdf")
        with open(dummy_path, "wb") as fh:
            fh.write(b"%PDF-1.4\n%Dummy")

        # call endpoint using local ingestion
        resp = client.post(f"/rag/ingest?use_local=true&local_dir={tmpdir}")
        assert resp.status_code == 200
        data = resp.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        # ensure metadata persisted with default 'system' user
        assert len(fake.docs) == 1
        assert fake.docs[0]["user_id"] == "system"
        assert fake.docs[0]["metadata"].get("path").endswith("doc1.pdf")
