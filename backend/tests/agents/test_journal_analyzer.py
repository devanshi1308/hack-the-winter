"""
Unit tests for journal analysis module.

Tests:
- Emotion extraction
- Sentiment analysis
- Cognitive distortion detection (both LLM and regex)
- Facet signal generation
- Fallback behavior when LLM unavailable
"""

import pytest
from core.journal_analyzer import (
    analyze_entry,
    extract_signals,
    apply_distortion_rules,
    _normalize_emotions,
    _ensure_all_facets,
    _clamp
)


class TestDistortionRules:
    """Test regex-based cognitive distortion detection."""
    
    def test_all_or_nothing_detection(self):
        # arrange
        text = "Everyone always ignores me and nobody ever listens"
        
        # act
        distortions = apply_distortion_rules(text)
        
        # assert
        assert "all_or_nothing" in distortions
    
    def test_must_statements(self):
        # arrange
        text = "I must finish this today and I should have known better"
        
        # act
        distortions = apply_distortion_rules(text)
        
        # assert
        assert "must_statements" in distortions
    
    def test_catastrophizing(self):
        # arrange
        text = "This is a complete disaster and everything is ruined"
        
        # act
        distortions = apply_distortion_rules(text)
        
        # assert
        assert "catastrophizing" in distortions
    
    def test_personalization(self):
        # arrange
        text = "It's all my fault that the project failed"
        
        # act
        distortions = apply_distortion_rules(text)
        
        # assert
        assert "personalization" in distortions
    
    def test_multiple_distortions(self):
        # arrange
        text = "Everyone always thinks I'm stupid and everything I do is a disaster. It's all my fault."
        
        # act
        distortions = apply_distortion_rules(text)
        
        # assert
        assert len(distortions) >= 2
        assert "all_or_nothing" in distortions
        assert "catastrophizing" in distortions


class TestEmotionNormalization:
    """Test emotion scoring and normalization."""
    
    def test_clamp_within_bounds(self):
        # arrange & act
        result = _clamp(0.5, 0.0, 1.0)
        
        # assert
        assert result == 0.5
    
    def test_clamp_above_max(self):
        # arrange & act
        result = _clamp(1.5, 0.0, 1.0)
        
        # assert
        assert result == 1.0
    
    def test_clamp_below_min(self):
        # arrange & act
        result = _clamp(-0.5, 0.0, 1.0)
        
        # assert
        assert result == 0.0
    
    def test_normalize_emotions_top_k(self):
        # arrange
        emotions = [
            {"label": "joy", "score": 0.8},
            {"label": "anger", "score": 0.6},
            {"label": "sadness", "score": 0.4},
            {"label": "fear", "score": 0.2}
        ]
        
        # act
        result = _normalize_emotions(emotions, top_k=2)
        
        # assert
        assert len(result) == 2
        assert result[0]["label"] == "joy"
        assert result[1]["label"] == "anger"
    
    def test_normalize_emotions_scores_clamped(self):
        # arrange
        emotions = [
            {"label": "joy", "score": 1.5},  # over max
            {"label": "anger", "score": -0.5}  # under min
        ]
        
        # act
        result = _normalize_emotions(emotions)
        
        # assert
        assert result[0]["score"] == 1.0
        assert result[1]["score"] == 0.0


class TestFacetSignals:
    """Test facet signal normalization."""
    
    def test_ensure_all_facets_complete(self):
        # arrange
        signals = {
            "self_awareness": "+",
            "self_regulation": "-"
        }
        
        # act
        result = _ensure_all_facets(signals)
        
        # assert
        assert len(result) == 5
        assert result["self_awareness"] == "+"
        assert result["self_regulation"] == "-"
        assert result["motivation"] == "0"
        assert result["empathy"] == "0"
        assert result["social_skills"] == "0"
    
    def test_ensure_all_facets_invalid_values(self):
        # arrange
        signals = {
            "self_awareness": "invalid",
            "self_regulation": "+"
        }
        
        # act
        result = _ensure_all_facets(signals)
        
        # assert
        assert result["self_awareness"] == "0"  # invalid replaced with default
        assert result["self_regulation"] == "+"


@pytest.mark.unit
class TestJournalAnalysis:
    """Test complete journal analysis pipeline."""
    
    def test_analyze_entry_with_llm(self, mock_llm_journal_analysis, sample_journal_entry):
        # arrange
        payload = sample_journal_entry
        
        # act
        result = analyze_entry(payload, mock_llm_journal_analysis)
        
        # assert
        assert "emotions" in result
        assert "sentiment" in result
        assert "cognitive_distortions" in result
        assert "facet_signals" in result
        assert "one_line_insight" in result
        assert len(result["emotions"]) <= 3
        assert -1.0 <= result["sentiment"] <= 1.0
    
    def test_analyze_entry_merges_distortions(self, mock_llm_journal_analysis):
        # arrange
        payload = {
            "user_id": "test",
            "mood": 2,
            "journal": "Everything always goes wrong and it's a complete disaster",
            "context": {}
        }
        
        # act
        result = analyze_entry(payload, mock_llm_journal_analysis)
        
        # assert
        # Should have distortions from both LLM and regex rules
        assert len(result["cognitive_distortions"]) >= 2
    
    def test_analyze_entry_empty_journal(self, mock_llm):
        # arrange
        payload = {
            "user_id": "test",
            "mood": 3,
            "journal": "",
            "context": {}
        }
        
        # act
        result = analyze_entry(payload, mock_llm)
        
        # assert
        assert result["emotions"][0]["label"] == "neutral"
        assert result["sentiment"] == 0.0
        assert len(result["topics"]) == 0
    
    def test_analyze_entry_without_llm(self):
        # arrange
        payload = {
            "user_id": "test",
            "mood": 3,
            "journal": "Test entry",
            "context": {}
        }
        
        # act
        result = analyze_entry(payload, llm=None)
        
        # assert
        # Should return conservative defaults when no LLM
        assert "emotions" in result
        assert result["emotions"][0]["label"] == "unsure"
