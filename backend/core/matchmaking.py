import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from sklearn.metrics.pairwise import cosine_similarity


def build_profile_text(user: Dict[str, Any]) -> str:
    """
    Build text representation of user profile for embeddings.
    Uses only safe, non-sensitive data (no journals).
    """
    parts = []
    
    # Basic profile
    if user.get("bio"):
        parts.append(f"Bio: {user['bio']}")
    
    # Strengths and focus areas
    strengths = user.get("strengths", [])
    if strengths:
        parts.append(f"Strengths: {', '.join(strengths)}")
    
    focus = user.get("focus", [])
    if focus:
        parts.append(f"Focus areas: {', '.join(focus)}")
    
    # Tags/interests
    tags = user.get("tags", [])
    if tags:
        parts.append(f"Interests: {', '.join(tags)}")
    
    # Availability
    availability = user.get("availability", [])
    if availability:
        parts.append(f"Available: {', '.join(availability)}")
    
    # Role context
    role = user.get("role", "")
    if role:
        parts.append(f"Role: {role}")
    
    return " ".join(parts) if parts else f"User profile for {user.get('user_id', 'unknown')}"


def vectorize(user: Dict[str, Any], embedder=None) -> np.ndarray:
    """
    Create embedding vector for user profile.
    Returns normalized vector for similarity calculations.
    """
    if embedder is None:
        try:
            from utils.model_loader import ModelLoader
            embedder = ModelLoader().load_embeddings()
        except Exception:
            # Fallback to zero vector if embedder unavailable
            return np.zeros(384)  # Common embedding dimension
    
    try:
        profile_text = build_profile_text(user)
        embedding = embedder.embed_query(profile_text)
        
        # Normalize vector
        vector = np.array(embedding)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector
    except Exception:
        # Return zero vector on error
        return np.zeros(len(embedding) if 'embedding' in locals() else 384)


def calculate_facet_overlap(mentee: Dict[str, Any], mentor: Dict[str, Any]) -> float:
    """
    Calculate overlap between mentee's focus areas and mentor's strengths.
    Returns score 0-1.
    """
    mentee_focus = set(mentee.get("focus", []))
    mentor_strengths = set(mentor.get("strengths", []))
    
    if not mentee_focus or not mentor_strengths:
        return 0.0
    
    overlap = mentee_focus.intersection(mentor_strengths)
    return len(overlap) / len(mentee_focus)


def calculate_time_overlap(mentee: Dict[str, Any], mentor: Dict[str, Any]) -> float:
    """
    Calculate availability time overlap.
    Returns score 0-1.
    """
    mentee_times = set(mentee.get("availability", []))
    mentor_times = set(mentor.get("availability", []))
    
    if not mentee_times or not mentor_times:
        return 0.0
    
    overlap = mentee_times.intersection(mentor_times)
    union = mentee_times.union(mentor_times)
    
    return len(overlap) / len(union) if union else 0.0


def calculate_soft_preferences(mentee: Dict[str, Any], mentor: Dict[str, Any]) -> float:
    """
    Calculate soft preference compatibility (tags, interests).
    Returns score 0-1.
    """
    mentee_tags = set(mentee.get("tags", []))
    mentor_tags = set(mentor.get("tags", []))
    
    if not mentee_tags or not mentor_tags:
        return 0.0
    
    overlap = mentee_tags.intersection(mentor_tags)
    union = mentee_tags.union(mentor_tags)
    
    return len(overlap) / len(union) if union else 0.0


def score_pair(mentee: Dict[str, Any], mentor: Dict[str, Any], 
               mentee_vector: Optional[np.ndarray] = None,
               mentor_vector: Optional[np.ndarray] = None,
               embedder=None) -> float:
    """
    Calculate compatibility score between mentee and mentor.
    Formula: 0.55*embed_sim + 0.25*facet_overlap + 0.10*time_overlap + 0.10*soft_prefs
    Returns score 0-1.
    """
    # 1. Embedding similarity (55%)
    if mentee_vector is None:
        mentee_vector = vectorize(mentee, embedder)
    if mentor_vector is None:
        mentor_vector = vectorize(mentor, embedder)
    
    # Calculate cosine similarity
    try:
        # Reshape for sklearn
        v1 = mentee_vector.reshape(1, -1)
        v2 = mentor_vector.reshape(1, -1)
        embed_sim = cosine_similarity(v1, v2)[0][0]
        # Ensure positive (cosine can be negative)
        embed_sim = max(0, embed_sim)
    except Exception:
        embed_sim = 0.0
    
    # 2. Facet overlap (25%)
    facet_overlap = calculate_facet_overlap(mentee, mentor)
    
    # 3. Time overlap (10%)
    time_overlap = calculate_time_overlap(mentee, mentor)
    
    # 4. Soft preferences (10%)
    soft_prefs = calculate_soft_preferences(mentee, mentor)
    
    # Weighted combination
    total_score = (
        0.55 * embed_sim +
        0.25 * facet_overlap +
        0.10 * time_overlap +
        0.10 * soft_prefs
    )
    
    return min(1.0, max(0.0, total_score))


def topk_matches(mentee: Dict[str, Any], mentors: List[Dict[str, Any]], 
                 k: int = 5, embedder=None) -> List[Dict[str, Any]]:
    """
    Find top-K mentor matches for a mentee.
    Returns sorted list of matches with scores.
    """
    if not mentors:
        return []
    
    # Pre-compute mentee vector once
    mentee_vector = vectorize(mentee, embedder)
    
    matches = []
    for mentor in mentors:
        # Skip if same user or inappropriate role pairing
        if mentor.get("user_id") == mentee.get("user_id"):
            continue
        
        # Ensure mentor has appropriate role
        mentor_role = mentor.get("role", "")
        if mentor_role not in ["mentor", "counselor"]:
            continue
        
        # Calculate compatibility score
        score = score_pair(mentee, mentor, mentee_vector, None, embedder)
        
        match_data = {
            "mentor_id": mentor.get("user_id"),
            "mentor_name": mentor.get("name", "Unknown"),
            "mentor_role": mentor_role,
            "score": round(score, 3),
            "strengths": mentor.get("strengths", []),
            "availability": mentor.get("availability", []),
            "bio": mentor.get("bio", "")[:200]  # Truncate long bios
        }
        matches.append(match_data)
    
    # Sort by score (descending) and return top-k
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches[:k]


def validate_mentorship_consent(user: Dict[str, Any]) -> bool:
    """
    Check if user has consented to mentorship matching.
    Returns True if consent given or if no consent field (assume consent).
    """
    consent = user.get("consent", {})
    return consent.get("mentorship_matching", True)  # Default to True


def create_match_proposal(mentee_id: str, mentor_id: str, score: float) -> Dict[str, Any]:
    """
    Create a match proposal record for database storage.
    """
    from datetime import datetime
    
    return {
        "mentee_id": mentee_id,
        "mentor_id": mentor_id,
        "score": score,
        "status": "proposed",
        "created_at": datetime.utcnow(),
        "accepted_at": None,
        "declined_at": None
    }