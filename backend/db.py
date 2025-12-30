import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING
from logger.custom_logger import CustomLogger
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import time
load_dotenv()

_LOG = CustomLogger().get_logger(__name__)

# Global client instance
_client: Optional[AsyncIOMotorClient] = None
_database: Optional[AsyncIOMotorDatabase] = None

#1234
async def init_db() -> AsyncIOMotorDatabase:
    """Initialize MongoDB connection and return database instance."""
    global _client, _database
    
    if _database is not None:
        return _database
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "raai_db")
    
    try:
        _client = AsyncIOMotorClient(mongo_uri)
        _database = _client[db_name]
        
        # Test connection
        await _client.admin.command('ping')
        _LOG.info("MongoDB connection established", db_name=db_name)
        
        # Create indexes
        await create_indexes()
        
        return _database
    except Exception as e:
        _LOG.error("Failed to connect to MongoDB", error=str(e))
        raise


async def close_db():
    """Close MongoDB connection."""
    global _client, _database
    if _client:
        _client.close()
        _client = None
        _database = None
        _LOG.info("MongoDB connection closed")


async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance, initializing if needed."""
    if _database is None:
        return await init_db()
    return _database


async def get_collection(name: str) -> AsyncIOMotorCollection:
    """Get collection by name."""
    db = await get_database()
    return db[name]


async def create_indexes():
    """Create necessary indexes for performance and constraints."""
    db = await get_database()
    
    try:
        # Users collection indexes
        users = db.users
        await users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("role", ASCENDING)]),
            IndexModel([("team_id", ASCENDING)])
        ])
        
        # Checkins collection indexes
        checkins = db.checkins
        await checkins.create_indexes([
            IndexModel([("user_id", ASCENDING), ("date", ASCENDING)], unique=True),
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("date", ASCENDING)])
        ])
        
        # Challenges collection indexes
        challenges = db.challenges
        await challenges.create_indexes([
            IndexModel([("team_id", ASCENDING)]),
            IndexModel([("created_by", ASCENDING)]),
            IndexModel([("start_date", ASCENDING)])
        ])
        
        # Participation collection indexes
        participation = db.participation
        await participation.create_indexes([
            IndexModel([("challenge_id", ASCENDING), ("user_id", ASCENDING)], unique=True),
            IndexModel([("challenge_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)])
        ])
        
        # Matches collection indexes
        matches = db.matches
        await matches.create_indexes([
            IndexModel([("mentee_id", ASCENDING), ("mentor_id", ASCENDING)], unique=True),
            IndexModel([("mentee_id", ASCENDING)]),
            IndexModel([("mentor_id", ASCENDING)]),
            IndexModel([("status", ASCENDING)])
        ])
        
        _LOG.info("Database indexes created successfully")
        
    except Exception as e:
        _LOG.error("Error creating database indexes", error=str(e))
        # Don't raise - indexes might already exist


# Collection helper functions
class Collections:
    """Helper class for accessing collections."""
    
    @staticmethod
    async def users() -> AsyncIOMotorCollection:
        return await get_collection("users")
    
    @staticmethod
    async def checkins() -> AsyncIOMotorCollection:
        return await get_collection("checkins")
    
    @staticmethod
    async def challenges() -> AsyncIOMotorCollection:
        return await get_collection("challenges")
    
    @staticmethod
    async def participation() -> AsyncIOMotorCollection:
        return await get_collection("participation")
    
    @staticmethod
    async def matches() -> AsyncIOMotorCollection:
        return await get_collection("matches")
    
    @staticmethod
    async def resources() -> AsyncIOMotorCollection:
        return await get_collection("resources")


# Utility functions for common operations
async def find_user_by_email(email: str) -> Optional[dict]:
    """Find user by email address."""
    users = await Collections.users()
    return await users.find_one({"email": email})


async def find_user_by_id(user_id: str) -> Optional[dict]:
    """Find user by ID."""
    users = await Collections.users()
    return await users.find_one({"_id": user_id})


async def upsert_checkin(checkin_data: dict) -> dict:
    """Upsert checkin data (update if exists, insert if not)."""
    checkins = await Collections.checkins()
    filter_query = {"user_id": checkin_data["user_id"], "date": checkin_data["date"]}
    
    result = await checkins.replace_one(
        filter_query,
        checkin_data,
        upsert=True
    )
    
    if result.upserted_id:
        checkin_data["_id"] = result.upserted_id
    
    return checkin_data


async def get_user_checkins(user_id: str, days: int = 30) -> list:
    """Get recent checkins for a user."""
    checkins = await Collections.checkins()
    cursor = checkins.find(
        {"user_id": user_id}
    ).sort("date", DESCENDING).limit(days)
    
    return await cursor.to_list(length=days)


async def get_team_participation_stats(team_id: str, min_users: int = 5) -> Optional[dict]:
    """Get team participation statistics, respecting k-anonymity."""
    users = await Collections.users()
    team_size = await users.count_documents({"team_id": team_id})
    
    if team_size < min_users:
        return None  # Respect k-anonymity
    
    # Aggregate recent checkins and participation
    checkins = await Collections.checkins()
    participation = await Collections.participation()
    
    # Get average mood trends (no individual data)
    pipeline = [
        {"$match": {"team_id": team_id}},
        {"$lookup": {
            "from": "checkins",
            "localField": "_id",
            "foreignField": "user_id", 
            "as": "checkins"
        }},
        {"$unwind": "$checkins"},
        {"$group": {
            "_id": "$checkins.date",
            "avg_mood_index": {"$avg": "$checkins.mood_index"},
            "participant_count": {"$sum": 1}
        }},
        {"$sort": {"_id": -1}},
        {"$limit": 30}
    ]
    
    users_coll = await Collections.users()
    mood_trends = await users_coll.aggregate(pipeline).to_list(length=30)
    
    # Get participation rate
    active_participants = await participation.distinct("user_id", {
        "last_completed": {"$gte": "2024-01-01"}  # Adjust date as needed
    })
    
    participation_rate = len(active_participants) / team_size if team_size > 0 else 0
    
    return {
        "team_size": team_size,
        "participation_rate": round(participation_rate, 3),
        "mood_trends": mood_trends,
        "anonymized": True
    }

async def get_user_checkins_safe(user_id: str, days: int = 30) -> list:
    """Get recent checkins for a user with fallback."""
    try:
        return await get_user_checkins(user_id, days)
    except Exception as e:
        print(f"Database query failed: {e}")
        return []  # Return empty list as fallback

async def upsert_checkin_safe(checkin_data: dict) -> dict:
    """Upsert checkin data with fallback."""
    try:
        return await upsert_checkin(checkin_data)
    except Exception as e:
        print(f"Database save failed: {e}")
        # Return the data with an ID to simulate saving
        checkin_data["_id"] = f"offline_{int(time.time())}"
        return checkin_data


uri = os.getenv("MONGO_URI")  


client = MongoClient(uri, server_api=ServerApi('1'))


try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)