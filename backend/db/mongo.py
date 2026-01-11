import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, DuplicateKeyError, OperationFailure

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
        
        # Production-ready connection settings
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,  # 5s to select server
                connectTimeoutMS=10000,          # 10s to establish connection
                socketTimeoutMS=30000,           # 30s for socket operations
                maxPoolSize=50,                  # Max connections in pool
                minPoolSize=5,                   # Min connections to maintain
                maxIdleTimeMS=45000,             # Close idle connections after 45s
                waitQueueTimeoutMS=10000,        # 10s wait for connection from pool
                retryWrites=True,                # Retry failed writes
                retryReads=True,                 # Retry failed reads
                w='majority',                    # Write concern: wait for majority
                journal=True                     # Wait for journal write
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            _LOG.info("MongoDB connected successfully", db=self.db_name)
            
            # Initialize collections and indexes
            self._setup_collections()
            
            # Run schema migrations
            self._run_schema_migrations()
            
        except ConnectionFailure as e:
            _LOG.error("MongoDB connection failed", error=str(e))
            raise DocumentPortalException("Cannot connect to MongoDB", None)
    
    def _create_index_safe(self, collection: Collection, *args, **kwargs) -> None:
        """
        Create index with error handling.
        Skips if index already exists with same spec.
        """
        try:
            collection.create_index(*args, **kwargs)
        except OperationFailure as e:
            if "already exists" in str(e).lower():
                _LOG.debug("Index already exists", collection=collection.name)
            else:
                _LOG.warning("Index creation failed", collection=collection.name, error=str(e))
        except Exception as e:
            _LOG.error("Unexpected error creating index", collection=collection.name, error=str(e))
    
    def _setup_collections(self):
        """Create collections and indexes if they don't exist."""
        
        # USERS COLLECTION
        self.users: Collection = self.db.users
        
        self._create_index_safe(self.users, "user_id", unique=True, name="user_id_unique")
        self._create_index_safe(self.users, "email", unique=True, sparse=True, name="email_unique")
        self._create_index_safe(self.users, "created_at", name="created_at_idx")
        
        # SESSIONS COLLECTION
        self.sessions: Collection = self.db.sessions
        
        self._create_index_safe(self.sessions, "session_id", unique=True, name="session_id_unique")
        
        # Compound index covers both user_id queries and user_id+created_at queries
        self._create_index_safe(
            self.sessions,
            [("user_id", ASCENDING), ("created_at", DESCENDING)],
            name="user_sessions_by_date"
        )
        
        # Index for analytics (activation stats)
        self._create_index_safe(self.sessions, "created_at", name="created_at_idx")
        
        # MESSAGES COLLECTION
        self.messages: Collection = self.db.messages
        
        # Primary access: get messages for session chronologically
        self._create_index_safe(
            self.messages,
            [("session_id", ASCENDING), ("timestamp", ASCENDING)],
            name="session_messages_chronological"
        )
        
        # Analytics: retention, mood tracking
        self._create_index_safe(
            self.messages,
            [("user_id", ASCENDING), ("timestamp", DESCENDING)],
            name="user_messages_by_date"
        )
        
        # Timestamp for analytics time range queries
        self._create_index_safe(self.messages, "timestamp", name="timestamp_idx")
        
        # Feedback for helpfulness analytics
        self._create_index_safe(
            self.messages,
            [("metadata.feedback", ASCENDING), ("timestamp", DESCENDING)],
            name="feedback_by_date"
        )
        
        # Optional text search
        if os.getenv("ENABLE_TEXT_SEARCH", "false").lower() == "true":
            self._create_index_safe(
                self.messages,
                [("content", TEXT)],
                name="content_text_search"
            )
        
        # TTL for episodic memory
        self._create_index_safe(
            self.messages,
            "expireAt",
            expireAfterSeconds=0,
            name="episodic_memory_ttl"
        )
        
        # DOCUMENTS COLLECTION
        self.documents: Collection = self.db.documents
        
        self._create_index_safe(self.documents, "doc_id", unique=True, name="doc_id_unique")
        self._create_index_safe(
            self.documents,
            [("user_id", ASCENDING), ("uploaded_at", DESCENDING)],
            name="user_docs_by_date"
        )
        
        # CRISIS EVENTS COLLECTION
        self.crisis_events: Collection = self.db.crisis_events
        
        self._create_index_safe(self.crisis_events, "event_id", unique=True, name="event_id_unique")
        
        # Compound for common query patterns
        self._create_index_safe(
            self.crisis_events,
            [("user_id", ASCENDING), ("status", ASCENDING), ("timestamp", DESCENDING)],
            name="user_status_events"
        )
        
        # Risk band filtering
        self._create_index_safe(
            self.crisis_events,
            [("risk_band", ASCENDING), ("timestamp", DESCENDING)],
            name="risk_band_events"
        )
        
        # Session-based queries
        self._create_index_safe(
            self.crisis_events,
            [("session_id", ASCENDING), ("timestamp", DESCENDING)],
            name="session_events"
        )
        
        # Timestamp for analytics
        self._create_index_safe(self.crisis_events, "timestamp", name="timestamp_idx")
        
        # TTL for safety events
        self._create_index_safe(
            self.crisis_events,
            "expireAt",
            expireAfterSeconds=0,
            name="safety_events_ttl"
        )
        
        _LOG.info("MongoDB collections and indexes initialized")

    def _run_schema_migrations(self):
        """Run schema migrations to ensure data consistency."""
        try:
            # Ensure timestamps
            missing_ts = self.messages.count_documents({"timestamp": {"$exists": False}})
            if missing_ts > 0:
                _LOG.info("Migrating messages missing timestamp", count=missing_ts)
                self.messages.update_many(
                    {"timestamp": {"$exists": False}},
                    {"$set": {"timestamp": datetime.now(timezone.utc)}}
                )
            
            # Ensure sessions have created_at
            missing_ca = self.sessions.count_documents({"created_at": {"$exists": False}})
            if missing_ca > 0:
                _LOG.info("Migrating sessions missing created_at", count=missing_ca)
                self.sessions.update_many(
                    {"created_at": {"$exists": False}},
                    {"$set": {"created_at": datetime.now(timezone.utc)}}
                )
            
            # Ensure users have created_at
            missing_user_created = self.users.count_documents({"created_at": {"$exists": False}})
            if missing_user_created > 0:
                _LOG.info("Migrating users missing created_at", count=missing_user_created)
                self.users.update_many(
                    {"created_at": {"$exists": False}},
                    {"$set": {"created_at": datetime.now(timezone.utc)}}
                )
            
            # Ensure crisis events have timestamp
            missing_event_ts = self.crisis_events.count_documents({"timestamp": {"$exists": False}})
            if missing_event_ts > 0:
                _LOG.info("Migrating crisis events missing timestamp", count=missing_event_ts)
                self.crisis_events.update_many(
                    {"timestamp": {"$exists": False}},
                    {"$set": {"timestamp": datetime.now(timezone.utc)}}
                )
            
            # Ensure messages have metadata
            missing_meta = self.messages.count_documents({"metadata": {"$exists": False}})
            if missing_meta > 0:
                _LOG.info("Migrating messages missing metadata", count=missing_meta)
                self.messages.update_many(
                    {"metadata": {"$exists": False}},
                    {"$set": {"metadata": {}}}
                )
            
            _LOG.info("Schema migrations completed")
            
        except Exception as e:
            _LOG.error("Schema migration failed", error=str(e))
    
    # CRISIS EVENT OPERATIONS
    
    def add_crisis_event(self, event_data: Dict[str, Any]) -> str:
        """Add crisis event to collection."""
        try:
            if "event_id" not in event_data or not event_data["event_id"]:
                event_data["event_id"] = f"evt_{uuid.uuid4().hex[:12]}"
            
            event_data["timestamp"] = datetime.now(timezone.utc)
            event_data.setdefault("status", "triggered")
            event_data.setdefault("resolution_steps", [])
            
            self.crisis_events.insert_one(event_data)
            _LOG.info("Crisis event created", event_id=event_data["event_id"])
            return event_data["event_id"]
            
        except DuplicateKeyError:
            raise ValueError(f"Crisis event {event_data.get('event_id')} already exists")

    def get_crisis_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve crisis event by event_id."""
        return self.crisis_events.find_one({"event_id": event_id}, {"_id": 0})

    def list_crisis_events(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        risk_band: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List crisis events with optional filters."""
        query = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        if risk_band:
            query["risk_band"] = risk_band
        
        return list(self.crisis_events.find(query, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit))

    def update_crisis_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update crisis event fields."""
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.crisis_events.update_one({"event_id": event_id}, {"$set": updates})
        return result.modified_count > 0
    
    def add_resolution_step(self, event_id: str, step: str, actor: str = "system") -> bool:
        """Add resolution step to crisis event."""
        resolution_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "actor": actor
        }
        
        result = self.crisis_events.update_one(
            {"event_id": event_id},
            {
                "$push": {"resolution_steps": resolution_entry},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
        return result.modified_count > 0
    
    # (Include all other operations from original file - user, session, message, document operations)
    # I'll skip copying them here for brevity since they're identical
    
    def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create user profile."""
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
            
            self.users.insert_one(user_data)
            _LOG.info("User created", user_id=user_data.get("user_id"))
            return user_data["user_id"]
        except DuplicateKeyError:
            raise ValueError(f"User {user_data.get('user_id')} already exists")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.users.find_one({"user_id": user_id}, {"_id": 0})
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.users.update_one({"user_id": user_id}, {"$set": updates})
        return result.modified_count > 0
    
    def update_baseline_scores(self, user_id: str, scores: Dict[str, float]) -> bool:
        return self.update_user(user_id, {"baseline_scores": scores})
    
    def create_session(self, session_data: Dict[str, Any]) -> str:
        try:
            session_data["created_at"] = datetime.now(timezone.utc)
            session_data.setdefault("is_pinned", False)
            session_data.setdefault("message_count", 0)
            session_data.setdefault("metadata", {})
            
            self.sessions.insert_one(session_data)
            _LOG.info("Session created", session_id=session_data.get("session_id"))
            return session_data["session_id"]
        except DuplicateKeyError:
            raise ValueError(f"Session {session_data.get('session_id')} already exists")
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.find_one({"session_id": session_id}, {"_id": 0})
    
    def list_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.sessions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", DESCENDING).limit(limit))
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        updates["updated_at"] = datetime.now(timezone.utc)
        result = self.sessions.update_one({"session_id": session_id}, {"$set": updates})
        return result.modified_count > 0
    
    def pin_session(self, session_id: str, pinned: bool = True) -> bool:
        return self.update_session(session_id, {"is_pinned": pinned})
    
    def delete_session(self, session_id: str) -> bool:
        self.messages.delete_many({"session_id": session_id})
        result = self.sessions.delete_one({"session_id": session_id})
        _LOG.info("Session deleted", session_id=session_id)
        return result.deleted_count > 0
    
    def add_message(self, message_data: Dict[str, Any]) -> str:
        message_data["timestamp"] = datetime.now(timezone.utc)
        message_data.setdefault("metadata", {})
        
        result = self.messages.insert_one(message_data)
        self.sessions.update_one(
            {"session_id": message_data["session_id"]},
            {"$inc": {"message_count": 1}}
        )
        return str(result.inserted_id)
    
    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return list(self.messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", ASCENDING).limit(limit))
    
    def get_recent_messages(self, user_id: str, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return list(self.messages.find({"user_id": user_id, "timestamp": {"$gte": cutoff}}, {"_id": 0}).sort("timestamp", DESCENDING).limit(limit))
    
    def add_document(self, doc_data: Dict[str, Any]) -> str:
        try:
            doc_data["uploaded_at"] = datetime.now(timezone.utc)
            doc_data.setdefault("status", "indexed")
            doc_data.setdefault("chunk_count", 0)
            doc_data.setdefault("metadata", {})
            
            self.documents.insert_one(doc_data)
            _LOG.info("Document added", doc_id=doc_data.get("doc_id"))
            return doc_data["doc_id"]
        except DuplicateKeyError:
            raise ValueError(f"Document {doc_data.get('doc_id')} already exists")
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.documents.find_one({"doc_id": doc_id}, {"_id": 0})
    
    def list_documents(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return list(self.documents.find({"user_id": user_id}, {"_id": 0}).sort("uploaded_at", DESCENDING).limit(limit))
    
    def delete_document(self, doc_id: str) -> bool:
        result = self.documents.delete_one({"doc_id": doc_id})
        return result.deleted_count > 0
    
    def get_mood_series(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        pipeline = [
            {"$match": {
                "user_id": user_id,
                "timestamp": {"$gte": cutoff},
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
        if self.client:
            self.client.close()
            _LOG.info("MongoDB connection closed")


_mongo_instance: Optional[MongoDB] = None


def get_mongo() -> MongoDB:
    global _mongo_instance
    if _mongo_instance is None:
        _mongo_instance = MongoDB()
    return _mongo_instance