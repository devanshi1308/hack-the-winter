"""
MongoDB data layer for RaAI emotional wellness system.

Collections:
- users: user profiles with EQ baseline scores and preferences
- sessions: chat sessions with metadata and configuration
- messages: conversation turns within sessions
- documents: metadata for uploaded PDFs and RAG sources
"""

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, DuplicateKeyError

from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException


_LOG = CustomLogger().get_logger(__name__)


class MongoDB:
    """
    Lightweight MongoDB wrapper for RaAI.
    Provides collection access and common CRUD patterns.
    """

    def __init__(self, uri: Optional[str] = None, db_name: Optional[str] = None):
        """
        Initialize MongoDB connection.
        
        Args:
            uri: MongoDB connection string (defaults to env MONGO_URI)
            db_name: Database name (defaults to env MONGO_DB or 'raai')
        """
        self.uri = uri or os.getenv("MONGO_URI", "mongodb://localhost:27017/")
        self.db_name = db_name or os.getenv("MONGO_DB", "raai")
        
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            _LOG.info("MongoDB connected successfully", db=self.db_name)
            
            # Initialize collections and indexes
            self._setup_collections()
            
        except ConnectionFailure as e:
            _LOG.error("MongoDB connection failed", error=str(e))
            raise DocumentPortalException("Cannot connect to MongoDB", None)
    
    def _setup_collections(self):
        """Create collections and indexes if they don't exist."""
        # Users collection
        self.users: Collection = self.db.users
        self.users.create_index("user_id", unique=True)
        self.users.create_index("email", unique=True, sparse=True)
        
        # Sessions collection
        self.sessions: Collection = self.db.sessions
        self.sessions.create_index("session_id", unique=True)
        self.sessions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        
        # Messages collection
        self.messages: Collection = self.db.messages
        self.messages.create_index([("session_id", ASCENDING), ("timestamp", ASCENDING)])
        self.messages.create_index("user_id")
        
        # Documents collection (RAG sources)
        self.documents: Collection = self.db.documents
        self.documents.create_index("doc_id", unique=True)
        self.documents.create_index("user_id")
        self.documents.create_index([("uploaded_at", DESCENDING)])
        
        _LOG.info("MongoDB collections and indexes initialized")
    
    # ==================== USER OPERATIONS ====================
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """
        Create a new user profile.
        
        Args:
            user_data: User profile with keys like user_id, email, baseline_scores, etc.
            
        Returns:
            user_id of created user
        """
        try:
            user_data["created_at"] = datetime.now(timezone.utc)
            user_data.setdefault("baseline_scores", {
                "self_awareness": 0.0,
                "self_regulation": 0.0,
                "motivation": 0.0,
                "empathy": 0.0,
                "social_skills": 0.0
            })
            user_data.setdefault("preferences", {})
            user_data.setdefault("consent", {"mentorship_matching": True})
            
            result = self.users.insert_one(user_data)
            _LOG.info("User created", user_id=user_data.get("user_id"))
            return user_data["user_id"]
            
        except DuplicateKeyError:
            _LOG.warning("User already exists", user_id=user_data.get("user_id"))
            raise ValueError(f"User {user_data.get('user_id')} already exists")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user by user_id."""
        return self.users.find_one({"user_id": user_id}, {"_id": 0})
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Update user profile fields."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.users.update_one({"user_id": user_id}, {"$set": updates})
        return result.modified_count > 0
    
    def update_baseline_scores(self, user_id: str, scores: Dict[str, float]) -> bool:
        """Update user's EQ baseline scores."""
        return self.update_user(user_id, {"baseline_scores": scores})
    
    # ==================== SESSION OPERATIONS ====================
    
    def create_session(self, session_data: Dict[str, Any]) -> str:
        """
        Create a new chat session.
        
        Args:
            session_data: Session with keys like session_id, user_id, name, etc.
            
        Returns:
            session_id of created session
        """
        try:
            session_data["created_at"] = datetime.now(timezone.utc)
            session_data.setdefault("is_pinned", False)
            session_data.setdefault("message_count", 0)
            session_data.setdefault("metadata", {})
            
            result = self.sessions.insert_one(session_data)
            _LOG.info("Session created", session_id=session_data.get("session_id"))
            return session_data["session_id"]
            
        except DuplicateKeyError:
            _LOG.warning("Session already exists", session_id=session_data.get("session_id"))
            raise ValueError(f"Session {session_data.get('session_id')} already exists")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session by session_id."""
        return self.sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    def list_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all sessions for a user, most recent first."""
        cursor = self.sessions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", DESCENDING).limit(limit)
        return list(cursor)
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session metadata."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.sessions.update_one({"session_id": session_id}, {"$set": updates})
        return result.modified_count > 0
    
    def pin_session(self, session_id: str, pinned: bool = True) -> bool:
        """Pin or unpin a session."""
        return self.update_session(session_id, {"is_pinned": pinned})
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        # Delete messages first
        self.messages.delete_many({"session_id": session_id})
        # Delete session
        result = self.sessions.delete_one({"session_id": session_id})
        _LOG.info("Session deleted", session_id=session_id)
        return result.deleted_count > 0
    
    # ==================== MESSAGE OPERATIONS ====================
    
    def add_message(self, message_data: Dict[str, Any]) -> str:
        """
        Add a message to a session.
        
        Args:
            message_data: Message with keys like session_id, role, content, etc.
            
        Returns:
            message_id (ObjectId as string)
        """
        message_data["timestamp"] = datetime.now(timezone.utc)
        message_data.setdefault("metadata", {})
        
        result = self.messages.insert_one(message_data)
        
        # Increment session message count
        self.sessions.update_one(
            {"session_id": message_data["session_id"]},
            {"$inc": {"message_count": 1}}
        )
        
        return str(result.inserted_id)
    
    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve messages for a session, chronologically."""
        cursor = self.messages.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", ASCENDING).limit(limit)
        return list(cursor)
    
    def get_recent_messages(self, user_id: str, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages across all sessions for analytics."""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
        
        cursor = self.messages.find(
            {"user_id": user_id, "timestamp": {"$gte": cutoff_dt}},
            {"_id": 0}
        ).sort("timestamp", DESCENDING).limit(limit)
        return list(cursor)
    
    # ==================== DOCUMENT OPERATIONS ====================
    
    def add_document(self, doc_data: Dict[str, Any]) -> str:
        """
        Add uploaded document metadata.
        
        Args:
            doc_data: Document metadata with keys like doc_id, user_id, filename, etc.
            
        Returns:
            doc_id
        """
        try:
            doc_data["uploaded_at"] = datetime.now(timezone.utc)
            doc_data.setdefault("status", "indexed")
            doc_data.setdefault("chunk_count", 0)
            doc_data.setdefault("metadata", {})
            
            result = self.documents.insert_one(doc_data)
            _LOG.info("Document added", doc_id=doc_data.get("doc_id"))
            return doc_data["doc_id"]
            
        except DuplicateKeyError:
            _LOG.warning("Document already exists", doc_id=doc_data.get("doc_id"))
            raise ValueError(f"Document {doc_data.get('doc_id')} already exists")
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata by doc_id."""
        return self.documents.find_one({"doc_id": doc_id}, {"_id": 0})
    
    def list_documents(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all documents for a user."""
        cursor = self.documents.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("uploaded_at", DESCENDING).limit(limit)
        return list(cursor)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete document metadata (does not delete from vector store)."""
        result = self.documents.delete_one({"doc_id": doc_id})
        return result.deleted_count > 0
    
    # ==================== ANALYTICS HELPERS ====================
    
    def get_mood_series(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get mood index time series for analytics.
        Aggregates from messages with mood_index metadata.
        """
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)
        
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "timestamp": {"$gte": cutoff_dt},
                "metadata.mood_index": {"$exists": True}
            }},
            {"$project": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "mood_index": "$metadata.mood_index"
            }},
            {"$group": {
                "_id": "$date",
                "avg_mood": {"$avg": "$mood_index"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        return list(self.messages.aggregate(pipeline))
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            _LOG.info("MongoDB connection closed")


# Global instance (lazy initialization)
_mongo_instance: Optional[MongoDB] = None


def get_mongo() -> MongoDB:
    """
    Get or create global MongoDB instance.
    Falls back gracefully if connection fails.
    """
    global _mongo_instance
    if _mongo_instance is None:
        try:
            _mongo_instance = MongoDB()
        except Exception as e:
            _LOG.error("Failed to initialize MongoDB", error=str(e))
            raise
    return _mongo_instance
