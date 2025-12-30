import re
from typing import Dict, List, Any

from logger.custom_logger import CustomLogger

_LOG = CustomLogger().get_logger(__name__)

_NEGATIVE_AROUSAL_EMOTIONS = {
    "anger", "anxiety", "fear", "panic", "stress", "frustration", "irritation"
}
_CONFLICT_TOPICS = {
    "conflict", "teamwork", "relationship", "relationships", "feedback",
    "argument", "misunderstanding", "disagreement", "boss", "manager", "colleague"
}
_SOCIAL_CONTEXT_TOPICS = {
    "meeting", "conversation", "communication", "presentation", "negotiation",
    "one-on-one", "1:1", "team", "call", "interview"
}


def _norm_lower(s: str | None) -> str:
    return (s or "").strip().lower()


def _has_overlap(a: List[str], b: set[str]) -> bool:
    al = {_norm_lower(x) for x in (a or []) if _norm_lower(x)}
    return not al.isdisjoint(b)


def choose_target(signals: Dict[str, str], sentiment: float, top_emotions: str, topics: List[str]) -> str:

    top_emotion = _norm_lower(top_emotions)
    topics_l = [_norm_lower(t) for t in (topics or []) if _norm_lower(t)]
    sig = {k: (v if v in {"+", "-", "0"} else "0") for k, v in (signals or {}).items()}

    # 1) If user is highly negative or high-arousal emotion → regulate first
    if sentiment <= -0.4 or top_emotion in _NEGATIVE_AROUSAL_EMOTIONS:
        return "self_regulation"

    # 2) Low self-awareness blocks everything else → build awareness
    if sig.get("self_awareness") == "-":
        return "self_awareness"

    # 3) If empathy signal is low and conflict/relationship topics dominate → empathy
    if sig.get("empathy") == "-" and _has_overlap(topics_l, _CONFLICT_TOPICS):
        return "empathy"

    # 4) If social skills signal is low and social/communication contexts present → social skills
    if sig.get("social_skills") == "-" and _has_overlap(topics_l, _SOCIAL_CONTEXT_TOPICS | _CONFLICT_TOPICS):
        return "social_skills"

    # 5) Motivation dip without acute distress → motivation
    if sig.get("motivation") == "-":
        return "motivation"

    # 6) Otherwise, default gently to awareness (safest universally helpful skill)
    return "self_awareness"


def compose_query(target_facet: str, top_emotion: str | None, topics: List[str], duration_hint: str = "2min") -> str:

    words: List[str] = []
    tf = _norm_lower(target_facet)
    if tf:
        words.append(tf)
    te = _norm_lower(top_emotion or "")
    if te:
        words.append(te)
    for t in (topics or [])[:2]:
        tt = _norm_lower(t)
        if tt:
            words.append(tt)
    dh = _norm_lower(duration_hint or "2min")
    if dh:
        words.append(dh)
    words.append("exercise")

    # sanitize: keep letters, digits, and spaces
    query = " ".join(words)
    query = re.sub(r"[^a-z0-9\s]+", " ", query)
    query = re.sub(r"\s+", " ", query).strip()
    _LOG.info("compose_query", query=query)
    return query


def _sanitize_step(s: Any) -> str:
    text = str(s or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text[:200]  # keep steps concise


def _fallback_exercise() -> Dict[str, Any]:
    return {
        "exercise_id": "SR_box_breath_2min",
        "title": "Box Breathing (2 minutes)",
        "steps": ["Inhale 4", "Hold 4", "Exhale 4", "Hold 4", "Repeat 6–8 cycles"],
        "expected_outcome": "Lower physiological arousal and regain a sense of control.",
        "source_doc_id": "fallback_ei_coach",
        "followup_question": "What changed in your body after two rounds?"
    }


def prepare_recommendation(rag_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize / validate a synthesized micro-exercise JSON from RAG/LLM
    On missing/invalid fields, returns a safe fallback exercise.
    """
    try:
        if not isinstance(rag_result, dict):
            _LOG.warning("prepare_recommendation: non-dict input; using fallback")
            return _fallback_exercise()

        required = [
            "exercise_id", "title", "steps",
            "expected_outcome", "source_doc_id", "followup_question"
        ]
        if any(k not in rag_result for k in required):
            _LOG.warning("prepare_recommendation: missing keys; using fallback", missing=[k for k in required if k not in rag_result])
            return _fallback_exercise()

        ex_id = str(rag_result.get("exercise_id", "")).strip() or "unnamed_exercise"
        title = str(rag_result.get("title", "")).strip() or "Practice"
        steps_raw = rag_result.get("steps", [])
        if not isinstance(steps_raw, list) or not steps_raw:
            return _fallback_exercise()
        steps = [_sanitize_step(s) for s in steps_raw if _sanitize_step(s)]
        steps = steps[:6] if steps else _fallback_exercise()["steps"]

        expected = str(rag_result.get("expected_outcome", "")).strip() or "Practice the skill momentarily."
        source_id = str(rag_result.get("source_doc_id", "")).strip() or "unknown"
        followup = str(rag_result.get("followup_question", "")).strip() or "What did you notice as you practiced?"

        rec = {
            "exercise_id": ex_id[:80],
            "title": title[:120],
            "steps": steps,
            "expected_outcome": expected[:240],
            "source_doc_id": source_id[:120],
            "followup_question": followup[:140],
        }
        _LOG.info("prepare_recommendation ok", title=rec["title"])
        return rec

    except Exception as e:
        _LOG.error("prepare_recommendation failed; using fallback", error=str(e))
        return _fallback_exercise()
