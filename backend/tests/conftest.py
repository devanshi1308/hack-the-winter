"""
Pytest configuration and shared fixtures for RaAI tests.

Provides mocks for:
- LLM calls (Google Gemini, Groq)
- External APIs (ElevenLabs, Twilio, FCM)
- MongoDB
- FAISS vector store
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, Mock
from typing import Dict, Any

# Ensure the backend root is on sys.path for absolute imports like `core.*` and `rag.*`
_TESTS_DIR = os.path.dirname(__file__)
_BACKEND_ROOT = os.path.abspath(os.path.join(_TESTS_DIR, ".."))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


# ==================== LLM MOCKS ====================

@pytest.fixture
def mock_llm():
    """Mock LLM that returns predictable JSON responses."""
    llm = MagicMock()
    
    # Default response object
    response = MagicMock()
    response.content = '{"emotions": [{"label": "joy", "score": 0.8}], "sentiment": 0.5, "cognitive_distortions": [], "topics": ["work"], "facet_signals": {"self_awareness": "0", "self_regulation": "0", "motivation": "+", "empathy": "0", "social_skills": "0"}, "one_line_insight": "You seem energized about work today."}'
    
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_llm_journal_analysis():
    """Mock LLM specifically for journal analysis."""
    llm = MagicMock()
    response = MagicMock()
    response.content = '''{
        "emotions": [
            {"label": "anxiety", "score": 0.7},
            {"label": "frustration", "score": 0.5}
        ],
        "sentiment": -0.3,
        "cognitive_distortions": ["catastrophizing", "all_or_nothing"],
        "topics": ["work", "deadline"],
        "facet_signals": {
            "self_awareness": "+",
            "self_regulation": "-",
            "motivation": "0",
            "empathy": "0",
            "social_skills": "0"
        },
        "one_line_insight": "Notice the physical signs of stress before it escalates."
    }'''
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_llm_coach_question():
    """Mock LLM for generating coach questions."""
    llm = MagicMock()
    response = MagicMock()
    response.content = "What physical sensation did you notice first when the stress began?"
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_embeddings():
    """Mock embeddings model that returns fixed vectors."""
    embeddings = MagicMock()
    embeddings.embed_documents.return_value = [[0.1] * 768 for _ in range(5)]
    embeddings.embed_query.return_value = [0.1] * 768
    return embeddings


# ==================== DATABASE MOCKS ====================

@pytest.fixture
def mock_mongo():
    """Mock MongoDB instance with collections."""
    mongo = MagicMock()
    
    # Mock collections
    mongo.users = MagicMock()
    mongo.sessions = MagicMock()
    mongo.messages = MagicMock()
    mongo.documents = MagicMock()
    
    # Default return values
    mongo.get_user.return_value = {
        "user_id": "test_user",
        "email": "test@example.com",
        "baseline_scores": {
            "self_awareness": 0.6,
            "self_regulation": 0.5,
            "motivation": 0.7,
            "empathy": 0.6,
            "social_skills": 0.5
        }
    }
    
    mongo.get_session.return_value = {
        "session_id": "test_session",
        "user_id": "test_user",
        "name": "Test Session",
        "created_at": "2025-01-01T00:00:00Z",
        "message_count": 0
    }
    
    return mongo


# ==================== RAG MOCKS ====================

@pytest.fixture
def mock_faiss_retriever():
    """Mock FAISS retriever that returns sample documents."""
    retriever = MagicMock()
    
    # Sample document
    doc = MagicMock()
    doc.page_content = "Practice box breathing: inhale for 4 counts, hold for 4, exhale for 4, hold for 4. Repeat 5 times."
    doc.metadata = {"source": "breathing_exercises.pdf", "page": 1}
    
    retriever.get_relevant_documents.return_value = [doc] * 3
    return retriever


# ==================== EXTERNAL API MOCKS ====================

@pytest.fixture
def mock_elevenlabs():
    """Mock ElevenLabs API for TTS/STT."""
    api = MagicMock()
    api.text_to_speech.return_value = b"fake_audio_bytes"
    api.speech_to_text.return_value = {
        "transcript": "I'm feeling anxious about tomorrow",
        "confidence": 0.95
    }
    return api


@pytest.fixture
def mock_twilio():
    """Mock Twilio API for SMS."""
    client = MagicMock()
    client.messages.create.return_value = MagicMock(sid="SM123456")
    return client


@pytest.fixture
def mock_fcm():
    """Mock Firebase Cloud Messaging for push notifications."""
    fcm = MagicMock()
    fcm.send.return_value = {"success": 1, "failure": 0}
    return fcm


# ==================== TEST DATA FIXTURES ====================

@pytest.fixture
def sample_journal_entry():
    """Sample journal entry for testing."""
    return {
        "user_id": "test_user",
        "mood": 3,
        "journal": "I had a tough day at work. The deadline is looming and I feel overwhelmed. Everything seems to be going wrong.",
        "context": {
            "location": "home",
            "time_of_day": "evening"
        }
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile."""
    return {
        "user_id": "test_user",
        "email": "test@example.com",
        "baseline_scores": {
            "self_awareness": 0.6,
            "self_regulation": 0.5,
            "motivation": 0.7,
            "empathy": 0.6,
            "social_skills": 0.5
        },
        "preferences": {
            "exercise_duration": "short",
            "reminder_time": "morning"
        },
        "consent": {
            "mentorship_matching": True,
            "data_analytics": True
        }
    }


@pytest.fixture
def sample_exercise():
    """Sample exercise recommendation."""
    return {
        "exercise_id": "breathing_001",
        "title": "Box Breathing",
        "steps": [
            "Find a comfortable seated position",
            "Inhale slowly for 4 counts",
            "Hold your breath for 4 counts",
            "Exhale slowly for 4 counts",
            "Hold empty for 4 counts",
            "Repeat 5 times"
        ],
        "expected_outcome": "Reduced anxiety and increased calm",
        "source_doc_id": "breathing_exercises.pdf",
        "followup_question": "How do you feel after completing this exercise?"
    }


@pytest.fixture
def sample_facet_signals():
    """Sample facet signals."""
    return {
        "self_awareness": "+",
        "self_regulation": "-",
        "motivation": "0",
        "empathy": "0",
        "social_skills": "0"
    }


# ==================== CONFIGURATION ====================

@pytest.fixture
def test_config():
    """Test configuration."""
    return {
        "llm": {
            "provider": "google",
            "model_name": "gemini-test",
            "temperature": 0.2
        },
        "embedding_model": {
            "model_name": "test-embedding"
        },
        "mongo": {
            "uri": "mongodb://localhost:27017/",
            "db": "raai_test"
        }
    }


# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
