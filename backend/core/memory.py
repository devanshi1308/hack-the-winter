"""
Memory augmentation system for RaAI.
Implements long-term profile, episodic memory, and vector memory per session.
Episodic memory includes TTL (time-to-live) for automatic expiration.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import os
import json

from logger.custom_logger import CustomLogger
from db.mongo import get_mongo

_LOG = CustomLogger().get_logger(__name__)

# TTL configuration (in seconds)
EPISODIC_MEMORY_TTL_DAYS = int(os.getenv("EPISODIC_MEMORY_TTL_DAYS", "30"))  # Default: 30 days
EPISODIC_MEMORY_TTL_SECONDS = EPISODIC_MEMORY_TTL_DAYS * 86400


class LongTermProfile:
    """
    User's stable traits, goals, preferences with decay/refresh.
    Persisted in MongoDB users collection.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mongo = get_mongo()
        self.log = CustomLogger().get_logger(__name__)
    
    def get_profile(self) -> Dict[str, Any]:
        """Retrieve user profile with stable traits."""
        try:
            user = self.mongo.get_user(self.user_id)
            if not user:
                # Initialize default profile
                user = {
                    "user_id": self.user_id,
                    "traits": {},
                    "goals": [],
                    "preferences": {},
                    "baseline_scores": {}
                }
                self.mongo.create_user(user)
            return user
        except Exception as e:
            self.log.error("Failed to get profile", error=str(e))
            return {"user_id": self.user_id, "traits": {}, "goals": [], "preferences": {}}
    
    def update_profile(self, updates: Dict[str, Any]):
        """Update profile with decay logic for stale data."""
        try:
            self.mongo.update_user(self.user_id, updates)
            self.log.info("Profile updated", user_id=self.user_id)
        except Exception as e:
            self.log.error("Profile update failed", error=str(e))
    
    def refresh_goals(self, new_goals: List[str]):
        """Replace goals with fresh ones."""
        self.update_profile({"goals": new_goals, "goals_updated_at": datetime.now(timezone.utc)})
    
    def add_trait(self, trait_name: str, value: Any):
        """Add or update a trait (e.g., 'coping_style': 'reflective')."""
        profile = self.get_profile()
        traits = profile.get("traits", {})
        traits[trait_name] = value
        self.update_profile({"traits": traits})


class EpisodicMemory:
    """
    Conversation turns with timestamps and tags.
    Stored in MongoDB messages collection with episodic flag.
    Includes TTL for automatic expiration of old episodes.
    """
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.mongo = get_mongo()
        self.log = CustomLogger().get_logger(__name__)
        self._setup_ttl_index()
    
    def _setup_ttl_index(self):
        """Create MongoDB TTL index for automatic episode expiration."""
        try:
            # Ensure TTL index exists on messages collection
            # TTL index on 'expires_at' field removes docs after TTL seconds
            self.mongo.db.messages.create_index(
                "expires_at",
                expireAfterSeconds=0  # Remove when field time is reached
            )
            self.log.info("TTL index setup for episodic memory")
        except Exception as e:
            self.log.warning("TTL index creation skipped (may already exist)", error=str(e))
    
    def add_episode(self, content: str, role: str, tags: List[str] = None, ttl_days: Optional[int] = None):
        """
        Store an episode (conversation turn) with TTL.
        Args:
            content: Episode content
            role: "user" or "assistant"
            tags: Optional list of tags
            ttl_days: Days until auto-expiration (default: EPISODIC_MEMORY_TTL_DAYS)
        """
        try:
            ttl_days = ttl_days or EPISODIC_MEMORY_TTL_DAYS
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
            
            self.mongo.add_message({
                "session_id": self.session_id,
                "user_id": self.user_id,
                "role": role,
                "content": content,
                "metadata": {
                    "episodic": True,
                    "tags": tags or [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "expires_at": expires_at  # MongoDB TTL field
            })
            self.log.info("Episode added with TTL", session_id=self.session_id, ttl_days=ttl_days)
        except Exception as e:
            self.log.error("Failed to add episode", error=str(e))
    
    def get_episodes(self, limit: int = 50, tag_filter: str = None) -> List[Dict[str, Any]]:
        """Retrieve non-expired episodes, optionally filtered by tag."""
        try:
            messages = self.mongo.get_session_messages(self.session_id, limit=limit)
            episodes = [m for m in messages if m.get("metadata", {}).get("episodic")]
            
            if tag_filter:
                episodes = [
                    e for e in episodes
                    if tag_filter in e.get("metadata", {}).get("tags", [])
                ]
            
            return episodes
        except Exception as e:
            self.log.error("Failed to get episodes", error=str(e))
            return []
    
    def summarize_recent(self, days: int = 7) -> str:
        """Generate a summary of recent non-expired episodes."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            messages = self.mongo.get_session_messages(self.session_id, limit=100)
            recent = [
                m for m in messages
                if datetime.fromisoformat(m.get("timestamp", "2020-01-01T00:00:00+00:00").replace("Z", "+00:00")) > cutoff
            ]
            
            count = len(recent)
            user_msgs = [m for m in recent if m.get("role") == "user"]
            
            if count == 0:
                return "No recent activity"
            
            summary = f"In the past {days} days: {count} messages, including {len(user_msgs)} from you. "
            summary += "Themes: reflection, emotional check-ins."
            
            return summary
        except Exception as e:
            self.log.error("Failed to summarize episodes", error=str(e))
            return "Unable to generate summary"
    
    def refresh_episode_ttl(self, episode_id: str, ttl_days: Optional[int] = None):
        """
        Refresh TTL for a specific episode (extend expiration).
        Useful for keeping important episodes fresh.
        """
        try:
            ttl_days = ttl_days or EPISODIC_MEMORY_TTL_DAYS
            expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)
            
            self.mongo.db.messages.update_one(
                {"_id": episode_id},
                {"$set": {"expires_at": expires_at}}
            )
            self.log.info("Episode TTL refreshed", episode_id=str(episode_id), ttl_days=ttl_days)
        except Exception as e:
            self.log.error("Failed to refresh episode TTL", error=str(e))


class VectorMemory:
    """
    Session-specific vector memory for semantic search over past conversations.
    Links to existing FAISS retriever or builds ephemeral index.
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.log = CustomLogger().get_logger(__name__)
        self.embeddings = None
        self.index = None
        
        try:
            from utils.model_loader import ModelLoader
            self.embeddings = ModelLoader().load_embeddings()
        except Exception as e:
            self.log.warning("Embeddings unavailable for vector memory", error=str(e))
    
    def index_session(self, messages: List[Dict[str, Any]]):
        """Build a mini FAISS index from session messages."""
        if not self.embeddings:
            self.log.warning("Cannot index without embeddings")
            return
        
        try:
            from langchain_community.vectorstores import FAISS
            from langchain_core.documents import Document
            
            docs = [
                Document(
                    page_content=m.get("content", ""),
                    metadata={"role": m.get("role"), "timestamp": m.get("timestamp")}
                )
                for m in messages if m.get("content")
            ]
            
            if docs:
                self.index = FAISS.from_documents(docs, self.embeddings)
                self.log.info("Vector memory indexed", session_id=self.session_id, count=len(docs))
        except Exception as e:
            self.log.error("Vector memory indexing failed", error=str(e))
    
    def search(self, query: str, k: int = 5) -> List[str]:
        """Search session vector memory."""
        if not self.index:
            return []
        
        try:
            results = self.index.similarity_search(query, k=k)
            return [doc.page_content for doc in results]
        except Exception as e:
            self.log.error("Vector memory search failed", error=str(e))
            return []


class MemoryManager:
    """Unified memory manager coordinating all memory types."""
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.profile = LongTermProfile(user_id)
        self.episodic = EpisodicMemory(session_id, user_id)
        self.vector = VectorMemory(session_id)
        self.log = CustomLogger().get_logger(__name__)
    
    def initialize(self):
        """Initialize all memory systems for session."""
        try:
            # Load and index recent episodes
            messages = self.episodic.get_episodes(limit=100)
            self.vector.index_session(messages)
            self.log.info("Memory initialized", session_id=self.session_id)
        except Exception as e:
            self.log.error("Memory initialization failed", error=str(e))
    
    def get_context(self, query: str) -> Dict[str, Any]:
        """Retrieve relevant context from all memory types."""
        return {
            "profile": self.profile.get_profile(),
            "recent_summary": self.episodic.summarize_recent(days=7),
            "relevant_episodes": self.vector.search(query, k=3)
        }
    
    def save_interaction(self, user_message: str, assistant_reply: str, tags: List[str] = None):
        """Save an interaction to episodic memory."""
        self.episodic.add_episode(user_message, "user", tags=tags)
        self.episodic.add_episode(assistant_reply, "assistant", tags=tags)


class PreferenceLearner:
    """
    Preference learning from exercise feedback.
    Computes preference vectors and updates user profile.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mongo = get_mongo()
        self.log = CustomLogger().get_logger(__name__)
    
    def add_feedback(
        self,
        exercise_id: str,
        thumbs_up: Optional[bool] = None,
        intensity_match: Optional[str] = None,
        duration_match: Optional[str] = None,
        relevance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record exercise feedback and update preference counters.
        
        Args:
            exercise_id: ID of exercise that was recommended
            thumbs_up: True=liked, False=disliked, None=neutral
            intensity_match: "too_easy", "just_right", "too_intense"
            duration_match: "too_short", "just_right", "too_long"
            relevance: "generic", "personalized", "life_changing"
        
        Returns:
            Updated counters and preference summary
        """
        try:
            # Get current profile
            profile = self.mongo.get_user(self.user_id) or {}
            feedback_history = profile.get("exercise_feedback_history", [])
            
            # Add new feedback
            feedback_entry = {
                "exercise_id": exercise_id,
                "thumbs_up": thumbs_up,
                "intensity_match": intensity_match,
                "duration_match": duration_match,
                "relevance": relevance,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            feedback_history.append(feedback_entry)
            
            # Compute preference counters
            counters = self._compute_counters(feedback_history)
            
            # Compute preference vector from feedback
            preference_vector = self._compute_preference_vector(feedback_history)
            
            # Update profile
            self.mongo.update_user(self.user_id, {
                "exercise_feedback_history": feedback_history[-100:],  # Keep last 100
                "preference_counters": counters,
                "preference_vector": preference_vector,
                "preference_updated_at": datetime.now(timezone.utc).isoformat()
            })
            
            self.log.info("Feedback recorded", user_id=self.user_id, exercise_id=exercise_id)
            
            return {
                "counters": counters,
                "preference_vector": preference_vector,
                "total_feedback": len(feedback_history)
            }
            
        except Exception as e:
            self.log.error("Failed to add feedback", error=str(e))
            return {"error": str(e)}
    
    def _compute_counters(self, feedback_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute preference counters from feedback history."""
        counters = {
            "thumbs_up": 0,
            "thumbs_down": 0,
            "intensity_too_easy": 0,
            "intensity_just_right": 0,
            "intensity_too_intense": 0,
            "duration_too_short": 0,
            "duration_just_right": 0,
            "duration_too_long": 0,
            "relevance_generic": 0,
            "relevance_personalized": 0,
            "relevance_life_changing": 0,
            "total": len(feedback_history)
        }
        
        for feedback in feedback_history:
            # Thumbs
            if feedback.get("thumbs_up") is True:
                counters["thumbs_up"] += 1
            elif feedback.get("thumbs_up") is False:
                counters["thumbs_down"] += 1
            
            # Intensity
            intensity = feedback.get("intensity_match")
            if intensity == "too_easy":
                counters["intensity_too_easy"] += 1
            elif intensity == "just_right":
                counters["intensity_just_right"] += 1
            elif intensity == "too_intense":
                counters["intensity_too_intense"] += 1
            
            # Duration
            duration = feedback.get("duration_match")
            if duration == "too_short":
                counters["duration_too_short"] += 1
            elif duration == "just_right":
                counters["duration_just_right"] += 1
            elif duration == "too_long":
                counters["duration_too_long"] += 1
            
            # Relevance
            relevance = feedback.get("relevance")
            if relevance == "generic":
                counters["relevance_generic"] += 1
            elif relevance == "personalized":
                counters["relevance_personalized"] += 1
            elif relevance == "life_changing":
                counters["relevance_life_changing"] += 1
        
        return counters
    
    def _compute_preference_vector(self, feedback_history: List[Dict[str, Any]]) -> List[float]:
        """
        Compute preference vector from feedback history.
        Simple approach: encode preferences as feature vector.
        In production, use embeddings or collaborative filtering.
        """
        if not feedback_history:
            return [0.0] * 10  # Default neutral vector
        
        # Feature engineering: encode preferences as normalized vector
        counters = self._compute_counters(feedback_history)
        total = max(counters["total"], 1)
        
        # 10-dimensional preference vector
        vector = [
            counters["thumbs_up"] / total,  # Like rate
            counters["thumbs_down"] / total,  # Dislike rate
            counters["intensity_too_easy"] / total,
            counters["intensity_just_right"] / total,
            counters["intensity_too_intense"] / total,
            counters["duration_too_short"] / total,
            counters["duration_just_right"] / total,
            counters["duration_too_long"] / total,
            counters["relevance_personalized"] / total,
            counters["relevance_life_changing"] / total,
        ]
        
        return vector
    
    def get_preference_summary(self) -> Dict[str, Any]:
        """Get user's preference summary and recommendations."""
        try:
            profile = self.mongo.get_user(self.user_id) or {}
            counters = profile.get("preference_counters", {})
            preference_vector = profile.get("preference_vector", [])
            
            # Derive recommendations from counters
            recommendations = []
            
            # Intensity preference
            if counters.get("intensity_too_intense", 0) > counters.get("intensity_too_easy", 0):
                recommendations.append("Prefer gentler, less intense exercises")
            elif counters.get("intensity_too_easy", 0) > counters.get("intensity_too_intense", 0):
                recommendations.append("Prefer more challenging exercises")
            else:
                recommendations.append("Current intensity level seems appropriate")
            
            # Duration preference
            if counters.get("duration_too_long", 0) > counters.get("duration_too_short", 0):
                recommendations.append("Prefer shorter exercises (under 5 min)")
            elif counters.get("duration_too_short", 0) > counters.get("duration_too_long", 0):
                recommendations.append("Prefer longer, more immersive exercises")
            
            # Relevance
            thumbs_up_rate = counters.get("thumbs_up", 0) / max(counters.get("total", 1), 1)
            
            return {
                "counters": counters,
                "preference_vector": preference_vector,
                "thumbs_up_rate": round(thumbs_up_rate, 2),
                "recommendations": recommendations,
                "last_updated": profile.get("preference_updated_at")
            }
            
        except Exception as e:
            self.log.error("Failed to get preference summary", error=str(e))
            return {"error": str(e)}
    
    def personalize_exercise_ranking(
        self,
        exercises: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank exercises based on learned preferences.
        Uses preference_vector to score exercises.
        
        Args:
            exercises: List of exercise dicts with metadata
        
        Returns:
            Reranked exercises with preference scores
        """
        try:
            profile = self.mongo.get_user(self.user_id) or {}
            preference_vector = profile.get("preference_vector")
            
            if not preference_vector:
                # No preferences learned yet, return as-is
                return exercises
            
            # Score each exercise based on preference alignment
            scored_exercises = []
            for exercise in exercises:
                # Simple scoring: match exercise attributes to preference vector
                # In production: use embeddings or learned model
                score = self._score_exercise(exercise, preference_vector)
                exercise["preference_score"] = score
                scored_exercises.append(exercise)
            
            # Sort by preference score descending
            scored_exercises.sort(key=lambda x: x.get("preference_score", 0), reverse=True)
            
            return scored_exercises
            
        except Exception as e:
            self.log.error("Failed to personalize ranking", error=str(e))
            return exercises
    
    def _score_exercise(
        self,
        exercise: Dict[str, Any],
        preference_vector: List[float]
    ) -> float:
        """
        Score an exercise based on preference vector.
        Simple heuristic approach for now.
        """
        score = 0.5  # Base score
        
        # Adjust based on intensity
        intensity = exercise.get("intensity", "moderate")
        if intensity == "gentle" and preference_vector[4] > 0.3:  # too_intense preference
            score += 0.2
        elif intensity == "intense" and preference_vector[2] > 0.3:  # too_easy preference
            score += 0.2
        
        # Adjust based on duration
        duration = exercise.get("duration_minutes", 5)
        if duration < 3 and preference_vector[7] > 0.3:  # too_long preference
            score += 0.2
        elif duration > 10 and preference_vector[5] > 0.3:  # too_short preference
            score += 0.2
        
        # Boost if high personalization/relevance preference
        if preference_vector[8] > 0.3 or preference_vector[9] > 0.3:
            score += 0.1
        
        return min(1.0, max(0.0, score))  # Clamp to [0, 1]

