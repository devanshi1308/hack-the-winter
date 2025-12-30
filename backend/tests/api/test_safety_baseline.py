"""
API tests for safety-check and baseline endpoints using Pydantic models.
"""

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_safety_check_escalate():
    payload = {"text": "I plan to kill myself tonight"}
    resp = client.post("/ai/safety-check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] in ("ESCALATE", "SAFE")
    # keyword fallback should escalate here
    assert data["label"] == "ESCALATE"
    assert data.get("message")


def test_baseline_pydantic_shape():
    payload = {
        "user_id": "u1",
        "answers": [
            {"qid": "SA1", "value": 4},
            {"qid": "SR1", "value": 3},
        ],
    }
    resp = client.post("/ai/score-baseline", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "scores" in data
    for k in ["self_awareness", "self_regulation", "motivation", "empathy", "social_skills"]:
        assert isinstance(data["scores"][k], float)
