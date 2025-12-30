"""
Unit tests for RAG pipeline.

Tests:
- Document ingestion and chunking
- FAISS retriever creation
- Exercise synthesis from chunks
- Citation extraction (future)
"""

import pytest
from unittest.mock import MagicMock, patch
from rag.rag_pipeline import ConversationalRAG


@pytest.mark.unit
class TestRAGSearch:
    """Test RAG search and retrieval."""
    
    def test_search_returns_chunks(self, mock_faiss_retriever):
        # arrange
        rag = ConversationalRAG(faiss_dir="test_vectorstore", llm=None)
        query = "breathing exercise for anxiety"
        
        # act
        chunks = rag.search(mock_faiss_retriever, query, k=3)
        
        # assert
        assert len(chunks) == 3
        assert all(isinstance(chunk, str) for chunk in chunks)
    
    def test_search_with_empty_query(self, mock_faiss_retriever):
        # arrange
        rag = ConversationalRAG(faiss_dir="test_vectorstore", llm=None)
        query = ""
        
        # act
        chunks = rag.search(mock_faiss_retriever, query, k=5)
        
        # assert
        # Should still return chunks (retriever handles empty queries)
        assert isinstance(chunks, list)


@pytest.mark.unit
class TestExerciseSynthesis:
    """Test exercise recommendation synthesis."""
    
    def test_synthesize_exercise_with_llm(self, mock_llm):
        # arrange
        rag = ConversationalRAG(faiss_dir="test_vectorstore", llm=mock_llm)
        
        # Mock LLM response with valid JSON
        response = MagicMock()
        response.content = '''{
            "exercise_id": "breathing_001",
            "title": "Box Breathing",
            "steps": ["Inhale 4", "Hold 4", "Exhale 4", "Hold 4", "Repeat"],
            "expected_outcome": "Reduced anxiety",
            "source_doc_id": "test_doc",
            "followup_question": "How do you feel?"
        }'''
        mock_llm.invoke.return_value = response
        
        chunks = ["Practice box breathing: inhale for 4, hold for 4, exhale for 4"]
        target_facets = ["self_regulation"]
        context_tags = ["anxiety", "high_arousal"]
        
        # act
        exercise = rag.synthesize_exercise(chunks, target_facets, context_tags, "2min")
        
        # assert
        assert "exercise_id" in exercise
        assert "title" in exercise
        assert "steps" in exercise
        assert isinstance(exercise["steps"], list)
    
    def test_synthesize_exercise_fallback(self):
        # arrange
        rag = ConversationalRAG(faiss_dir="test_vectorstore", llm=None)
        
        chunks = ["Some exercise content"]
        target_facets = ["self_regulation"]
        context_tags = []
        
        # act
        exercise = rag.synthesize_exercise(chunks, target_facets, context_tags, "2min")
        
        # assert
        # Should return fallback exercise
        assert exercise["exercise_id"] == "fallback_exercise"
        assert "steps" in exercise
        assert len(exercise["steps"]) > 0


@pytest.mark.unit
class TestRAGPipeline:
    """Test complete RAG pipeline."""
    
    def test_get_exercise_complete_flow(self, mock_faiss_retriever, mock_llm):
        # arrange
        rag = ConversationalRAG(faiss_dir="test_vectorstore", llm=mock_llm)
        
        # Mock LLM response
        response = MagicMock()
        response.content = '''{
            "exercise_id": "grounding_001",
            "title": "5-4-3-2-1 Grounding",
            "steps": ["Name 5 things you see", "Name 4 things you hear"],
            "expected_outcome": "Present moment awareness",
            "source_doc_id": "grounding.pdf",
            "followup_question": "What did you notice?"
        }'''
        mock_llm.invoke.return_value = response
        
        target_facets = ["self_awareness"]
        context_tags = ["anxiety"]
        
        # act
        with patch.object(rag, 'search', return_value=["sample chunk 1", "sample chunk 2"]):
            exercise = rag.get_exercise(mock_faiss_retriever, target_facets, context_tags, "2min")
        
        # assert
        assert "exercise_id" in exercise
        assert "title" in exercise
        assert "steps" in exercise
