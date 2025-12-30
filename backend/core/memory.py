"""
Memory augmentation system for RaAI.
Implements long-term profile, episodic memory, and vector memory per session.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import json

from logger.custom_logger import CustomLogger
from db.mongo import get_mongo

_LOG = CustomLogger().get_logger(__name__)


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
    """
    
    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.mongo = get_mongo()
        self.log = CustomLogger().get_logger(__name__)
    
    def add_episode(self, content: str, role: str, tags: List[str] = None):
        """Store an episode (conversation turn)."""
        try:
            self.mongo.add_message({
                "session_id": self.session_id,
                "user_id": self.user_id,
                "role": role,
                "content": content,
                "metadata": {
                    "episodic": True,
                    "tags": tags or [],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            })
            self.log.info("Episode added", session_id=self.session_id)
        except Exception as e:
            self.log.error("Failed to add episode", error=str(e))
    
    def get_episodes(self, limit: int = 50, tag_filter: str = None) -> List[Dict[str, Any]]:
        """Retrieve episodes, optionally filtered by tag."""
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
        """Generate a summary of recent episodes."""
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
