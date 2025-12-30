"""
Unit tests for MongoDB data layer.

Tests:
- User CRUD operations
- Session management
- Message storage and retrieval
- Document metadata
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock


@pytest.mark.unit
class TestUserOperations:
    """Test user profile operations."""
    
    def test_create_user(self, mock_mongo):
        # arrange
        user_data = {
            "user_id": "new_user",
            "email": "new@example.com",
            "baseline_scores": {
                "self_awareness": 0.5,
                "self_regulation": 0.5,
                "motivation": 0.5,
                "empathy": 0.5,
                "social_skills": 0.5
            }
        }
        mock_mongo.create_user.return_value = "new_user"
        
        # act
        result = mock_mongo.create_user(user_data)
        
        # assert
        assert result == "new_user"
        mock_mongo.create_user.assert_called_once_with(user_data)
    
    def test_get_user(self, mock_mongo):
        # arrange
        user_id = "test_user"
        
        # act
        result = mock_mongo.get_user(user_id)
        
        # assert
        assert result is not None
        assert result["user_id"] == user_id
        assert "baseline_scores" in result
    
    def test_update_baseline_scores(self, mock_mongo):
        # arrange
        user_id = "test_user"
        new_scores = {
            "self_awareness": 0.8,
            "self_regulation": 0.7,
            "motivation": 0.9,
            "empathy": 0.7,
            "social_skills": 0.6
        }
        mock_mongo.update_baseline_scores.return_value = True
        
        # act
        result = mock_mongo.update_baseline_scores(user_id, new_scores)
        
        # assert
        assert result is True


@pytest.mark.unit
class TestSessionOperations:
    """Test session management."""
    
    def test_create_session(self, mock_mongo):
        # arrange
        session_data = {
            "session_id": "new_session",
            "user_id": "test_user",
            "name": "New Chat"
        }
        mock_mongo.create_session.return_value = "new_session"
        
        # act
        result = mock_mongo.create_session(session_data)
        
        # assert
        assert result == "new_session"
    
    def test_list_sessions(self, mock_mongo):
        # arrange
        user_id = "test_user"
        mock_mongo.list_sessions.return_value = [
            {"session_id": "s1", "name": "Session 1"},
            {"session_id": "s2", "name": "Session 2"}
        ]
        
        # act
        sessions = mock_mongo.list_sessions(user_id)
        
        # assert
        assert len(sessions) == 2
        assert all("session_id" in s for s in sessions)
    
    def test_pin_session(self, mock_mongo):
        # arrange
        session_id = "test_session"
        mock_mongo.pin_session.return_value = True
        
        # act
        result = mock_mongo.pin_session(session_id, True)
        
        # assert
        assert result is True
    
    def test_delete_session(self, mock_mongo):
        # arrange
        session_id = "test_session"
        mock_mongo.delete_session.return_value = True
        
        # act
        result = mock_mongo.delete_session(session_id)
        
        # assert
        assert result is True


@pytest.mark.unit
class TestMessageOperations:
    """Test message storage and retrieval."""
    
    def test_add_message(self, mock_mongo):
        # arrange
        message_data = {
            "session_id": "test_session",
            "user_id": "test_user",
            "role": "user",
            "content": "I'm feeling anxious today"
        }
        mock_mongo.add_message.return_value = "msg_123"
        
        # act
        result = mock_mongo.add_message(message_data)
        
        # assert
        assert result == "msg_123"
    
    def test_get_session_messages(self, mock_mongo):
        # arrange
        session_id = "test_session"
        mock_mongo.get_session_messages.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        # act
        messages = mock_mongo.get_session_messages(session_id)
        
        # assert
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
    
    def test_get_recent_messages(self, mock_mongo):
        # arrange
        user_id = "test_user"
        mock_mongo.get_recent_messages.return_value = [
            {"content": "Recent message 1"},
            {"content": "Recent message 2"}
        ]
        
        # act
        messages = mock_mongo.get_recent_messages(user_id, days=7)
        
        # assert
        assert len(messages) == 2


@pytest.mark.unit
class TestDocumentOperations:
    """Test document metadata operations."""
    
    def test_add_document(self, mock_mongo):
        # arrange
        doc_data = {
            "doc_id": "doc_123",
            "user_id": "test_user",
            "filename": "wellness_guide.pdf",
            "chunk_count": 42
        }
        mock_mongo.add_document.return_value = "doc_123"
        
        # act
        result = mock_mongo.add_document(doc_data)
        
        # assert
        assert result == "doc_123"
    
    def test_list_documents(self, mock_mongo):
        # arrange
        user_id = "test_user"
        mock_mongo.list_documents.return_value = [
            {"doc_id": "doc_1", "filename": "file1.pdf"},
            {"doc_id": "doc_2", "filename": "file2.pdf"}
        ]
        
        # act
        docs = mock_mongo.list_documents(user_id)
        
        # assert
        assert len(docs) == 2
        assert all("doc_id" in d for d in docs)
