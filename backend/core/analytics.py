import json
import math
from pathlib import Path
from typing import List, Dict, Any, Optional


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