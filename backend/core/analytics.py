from db.mongo import get_mongo
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import json
import math
from pathlib import Path


# --- Analytics Aggregations ---

def get_activation_stats(days: int = 30) -> Dict[str, Any]:
    """
    Return count of unique users who activated (created account) in the last N days.
    
    Args:
        days: Number of days to look back
    
    Returns:
        {
            "activated_users": int,
            "since": str (ISO datetime),
            "days": int
        }
    """
    try:
        mongo = get_mongo()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Count users created since the cutoff date
        count = mongo.users.count_documents({"created_at": {"$gte": since}})
        
        return {
            "activated_users": count,
            "since": since.isoformat(),
            "days": days
        }
    except Exception as e:
        return {
            "activated_users": 0,
            "since": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "days": days,
            "error": str(e)
        }


def get_retention_stats(days: int = 30) -> Dict[str, Any]:
    """
    Return retention: unique users with message activity in last N days.
    
    Args:
        days: Number of days to look back
    
    Returns:
        {
            "retained_users": int,
            "active_sessions": int,
            "since": str (ISO datetime),
            "days": int
        }
    """
    try:
        mongo = get_mongo()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Aggregate unique users with messages since cutoff
        pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {"_id": "$user_id"}},
            {"$count": "total"}
        ]
        
        result = list(mongo.messages.aggregate(pipeline))
        retained_count = result[0]["total"] if result else 0
        
        # Also count active sessions
        session_pipeline = [
            {"$match": {"created_at": {"$gte": since}}},
            {"$count": "total"}
        ]
        session_result = list(mongo.sessions.aggregate(session_pipeline))
        session_count = session_result[0]["total"] if session_result else 0
        
        return {
            "retained_users": retained_count,
            "active_sessions": session_count,
            "since": since.isoformat(),
            "days": days
        }
    except Exception as e:
        return {
            "retained_users": 0,
            "active_sessions": 0,
            "since": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "days": days,
            "error": str(e)
        }


def get_helpfulness_stats(days: int = 30) -> Dict[str, Any]:
    """
    Return helpfulness: count and rate of positive feedback in last N days.
    
    Looks for messages with metadata.feedback field.
    
    Args:
        days: Number of days to look back
    
    Returns:
        {
            "helpful_feedback": int,
            "total_feedback": int,
            "helpfulness_rate": float (0-1),
            "since": str (ISO datetime),
            "days": int
        }
    """
    try:
        mongo = get_mongo()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Find all messages with feedback since cutoff
        feedback_messages = list(mongo.messages.find({
            "metadata.feedback": {"$exists": True},
            "timestamp": {"$gte": since}
        }, {"metadata.feedback": 1}))
        
        total = len(feedback_messages)
        helpful = sum(
            1 for msg in feedback_messages
            if msg.get("metadata", {}).get("feedback") in ["helpful", "positive", "thumbs_up", True]
        )
        
        rate = (helpful / total) if total > 0 else 0.0
        
        return {
            "helpful_feedback": helpful,
            "total_feedback": total,
            "helpfulness_rate": round(rate, 3),
            "since": since.isoformat(),
            "days": days
        }
    except Exception as e:
        return {
            "helpful_feedback": 0,
            "total_feedback": 0,
            "helpfulness_rate": 0.0,
            "since": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "days": days,
            "error": str(e)
        }


def get_safety_stats(days: int = 30) -> Dict[str, Any]:
    """
    Return count and breakdown of safety (crisis) events in last N days.
    
    Args:
        days: Number of days to look back
    
    Returns:
        {
            "total_events": int,
            "by_status": {triggered: int, acknowledged: int, resolved: int},
            "by_risk_band": {green: int, yellow: int, red: int},
            "since": str (ISO datetime),
            "days": int
        }
    """
    try:
        mongo = get_mongo()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Count total events
        total = mongo.crisis_events.count_documents({"timestamp": {"$gte": since}})
        
        # Breakdown by status
        status_pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_results = list(mongo.crisis_events.aggregate(status_pipeline))
        by_status = {item["_id"]: item["count"] for item in status_results}
        
        # Breakdown by risk_band
        risk_pipeline = [
            {"$match": {"timestamp": {"$gte": since}}},
            {"$group": {"_id": "$risk_band", "count": {"$sum": 1}}}
        ]
        risk_results = list(mongo.crisis_events.aggregate(risk_pipeline))
        by_risk_band = {item["_id"]: item["count"] for item in risk_results}
        
        return {
            "total_events": total,
            "by_status": by_status,
            "by_risk_band": by_risk_band,
            "since": since.isoformat(),
            "days": days
        }
    except Exception as e:
        return {
            "total_events": 0,
            "by_status": {},
            "by_risk_band": {},
            "since": (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(),
            "days": days,
            "error": str(e)
        }


# --- Check-in Analytics ---

def likert_questions() -> List[Dict[str, Any]]:
    """Return list of daily Likert questions from data/likert_questions.json"""
    path = Path("data/likert_questions.json")
    if not path.exists():
        # Fallback questions
        return [
            {"id": "mood", "text": "How would you rate your overall mood today?", "scale": "1=Very Low, 5=Very High"},
            {"id": "stress", "text": "How stressed did you feel today?", "scale": "1=Not at all, 5=Extremely"},
            {"id": "energy", "text": "How energetic did you feel today?", "scale": "1=Very Low, 5=Very High"},
            {"id": "connection", "text": "How connected did you feel to others today?", "scale": "1=Not at all, 5=Very Connected"},
            {"id": "motivation", "text": "How motivated did you feel today?", "scale": "1=Not at all, 5=Extremely"}
        ]
    
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # Return fallback if file exists but can't be parsed
        return likert_questions()


def score_checkin(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Likert responses (1-5) to MoodIndex (0-100).
    
    Expected payload: {user_id, date?, mood, stress, energy, connection, motivation, sleep?}
    
    Returns: original payload + mood_index
    """
    # Extract Likert values (1-5), default to 3 if missing
    mood = float(payload.get("mood", 3))
    stress = float(payload.get("stress", 3))
    energy = float(payload.get("energy", 3))
    connection = float(payload.get("connection", 3))
    motivation = float(payload.get("motivation", 3))
    
    # Normalize to 0-1 range
    valence = (mood - 1) / 4  # mood as valence proxy
    stress_rev = (5 - stress) / 4  # reverse stress (lower stress = better)
    energy_norm = (energy - 1) / 4
    connection_norm = (connection - 1) / 4
    motivation_norm = (motivation - 1) / 4
    
    # Weighted MoodIndex calculation
    mood_index = 100 * (
        0.30 * valence +
        0.25 * stress_rev +
        0.15 * energy_norm +
        0.15 * connection_norm +
        0.15 * motivation_norm
    )
    
    # Ensure 0-100 range
    mood_index = max(0, min(100, mood_index))
    
    result = payload.copy()
    result["mood_index"] = round(mood_index, 2)
    return result


def ema(series: List[float], k: int) -> float:
    """
    Calculate Exponential Moving Average over k periods.
    Simple alpha = 2/(k+1) formula.
    """
    if not series:
        return 0.0
    
    if len(series) == 1:
        return series[0]
    
    alpha = 2.0 / (k + 1)
    ema_val = series[0]  # Start with first value
    
    for value in series[1:]:
        ema_val = alpha * value + (1 - alpha) * ema_val
    
    return round(ema_val, 2)


def zscore(series: List[float]) -> float:
    """
    Calculate z-score of the last point relative to the series mean/std.
    Returns 0 if insufficient data or zero std.
    """
    if len(series) < 2:
        return 0.0
    
    mean_val = sum(series) / len(series)
    variance = sum((x - mean_val) ** 2 for x in series) / len(series)
    std_val = math.sqrt(variance)
    
    if std_val == 0:
        return 0.0
    
    last_value = series[-1]
    z = (last_value - mean_val) / std_val
    return round(z, 3)


def flag_from_trend(series: List[float]) -> str:
    """
    Generate flag based on z-score trend analysis.
    Returns "SAFE" or "WATCH" based on z <= -1.5 threshold.
    """
    if len(series) < 3:  # Need minimum data for trend analysis
        return "SAFE"
    
    z = zscore(series)
    return "WATCH" if z <= -1.5 else "SAFE"


def compute_series_stats(mood_indices: List[float]) -> Dict[str, Any]:
    """
    Compute all analytics for a mood index series.
    Returns dict with ema7, ema14, zscore, and flag.
    """
    if not mood_indices:
        return {"ema7": 0.0, "ema14": 0.0, "zscore": 0.0, "flag": "SAFE"}
    
    return {
        "ema7": ema(mood_indices, 7),
        "ema14": ema(mood_indices, 14),
        "zscore": zscore(mood_indices),
        "flag": flag_from_trend(mood_indices)
    }