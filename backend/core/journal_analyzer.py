import json
import math
import re
from typing import Any, Dict, List

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from prompts.prompt_lib import PROMPT_REGISTRY  # expects "analyze_journal"

_LOG = CustomLogger().get_logger(__name__)

def _ensure_llm(llm=None):
    if llm is not None:
        return llm
    try:
        return ModelLoader().load_llm()
    except Exception as e:
        _LOG.error("Failed to load LLM in journal_analyzer", error=str(e))
        return None  # allow fallbacks


def _json_salvage(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end+1])
    raise ValueError("Could not salvage JSON from LLM output")


def _clamp(v: float, lo: float, hi: float) -> float:
    try:
        return max(lo, min(hi, float(v)))
    except Exception:
        return 0.0


def _normalize_emotions(items: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    norm: List[Dict[str, Any]] = []
    for it in items or []:
        label = str(it.get("label", "")).strip().lower()
        try:
            score = float(it.get("score", 0.0))
        except Exception:
            score = 0.0
        norm.append({"label": label, "score": _clamp(score, 0.0, 1.0)})
    norm.sort(key=lambda x: x["score"], reverse=True)
    return norm[:top_k]


def _ensure_all_facets(fsignals: Dict[str, str]) -> Dict[str, str]:
    keys = ["self_awareness", "self_regulation", "motivation", "empathy", "social_skills"]
    out = {k: "0" for k in keys}
    for k, v in (fsignals or {}).items():
        if k in out and v in {"+", "-", "0"}:
            out[k] = v
    return out


def apply_distortion_rules(text: str) -> list[str]:
    """
    Lightweight keyword/phrase rules for common cognitive distortions.
    Returns a de-duplicated list of labels.
    """
    if not text:
        return []
    t = text.lower()

    distortions: List[str] = []
    # All-or-nothing / overgeneralization
    if re.search(r"\b(always|never|everyone|no one|nobody|everybody)\b", t):
        distortions.append("all_or_nothing")

    # Must/should statements
    if re.search(r"\b(should|must|have to|ought to)\b", t):
        distortions.append("must_statements")

    # Mind reading
    if re.search(r"\b(they|he|she|boss|team)\s+(must|probably|likely)\s+think", t):
        distortions.append("mind_reading")

    # Catastrophizing
    if re.search(r"\b(disaster|ruined|catastrophe|catastrophic|terrible|awful)\b", t):
        distortions.append("catastrophizing")

    # Personalization / blame
    if re.search(r"\b(my fault|all my fault|blame me|because of me)\b", t):
        distortions.append("personalization")

    # Labeling
    if re.search(r"\b(i am|i'm)\s+(a\s+)?(failure|loser|stupid|worthless)\b", t):
        distortions.append("labeling")

    # Emotional reasoning
    if re.search(r"\b(i feel (like|that) .* therefore|because i feel)\b", t):
        distortions.append("emotional_reasoning")

    # Filtering negatives
    if re.search(r"\b(nothing went well|only bad|everything went wrong)\b", t):
        distortions.append("mental_filter")

    return sorted(list(set(distortions)))


def extract_signals(text: str, mood: int, context: dict, llm) -> dict:
    """
    Calls the LLM with the strict-JSON analyze_journal prompt.
    Returns a dict with keys:
      emotions, sentiment, cognitive_distortions, topics, facet_signals, one_line_insight
    """
    chat = _ensure_llm(llm)
    if chat is None:
        # Conservative defaults if no LLM is available
        return {
            "emotions": [{"label": "unsure", "score": 0.0}],
            "sentiment": 0.0,
            "cognitive_distortions": [],
            "topics": [],
            "facet_signals": _ensure_all_facets({}),
            "one_line_insight": "Could not analyze entry reliably.",
        }

    try:
        prompt = PROMPT_REGISTRY["analyze_journal"]  # ChatPromptTemplate
        messages = prompt.format_messages(
            journal=text,
            mood=mood,
            context_json=json.dumps(context or {}, ensure_ascii=False),
        )
        resp = chat.invoke(messages)
        raw = getattr(resp, "content", None) or str(resp)

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = _json_salvage(raw)

        # Minimal key presence checks; fill later in analyze_entry
        return parsed

    except Exception as e:
        _LOG.error("extract_signals failed; returning defaults", error=str(e))
        return {
            "emotions": [{"label": "unsure", "score": 0.0}],
            "sentiment": 0.0,
            "cognitive_distortions": [],
            "topics": [],
            "facet_signals": _ensure_all_facets({}),
            "one_line_insight": "Could not analyze entry reliably.",
        }


def analyze_entry(payload: dict, llm) -> dict:
    """
    Orchestrates analysis:
      1) LLM extraction
      2) Heuristic distortion rules (merge with LLM output)
      3) Normalization & clamping
      4) Sensible fallbacks
    Returns a dict suitable for downstream recommendation.
    """
    journal = (payload or {}).get("journal", "") or ""
    try:
        mood = int((payload or {}).get("mood", 3))
    except Exception:
        mood = 3
    context = (payload or {}).get("context", {}) or {}

    # 1) LLM extraction
    parsed = extract_signals(journal, mood, context, llm)

    # 2) Merge distortions
    llm_distortions = parsed.get("cognitive_distortions", []) or []
    rule_distortions = apply_distortion_rules(journal)
    merged_distortions = sorted(list(set([*llm_distortions, *rule_distortions])))

    # 3) Normalize fields
    emotions = _normalize_emotions(parsed.get("emotions", []), top_k=3)
    sentiment = _clamp(parsed.get("sentiment", 0.0), -1.0, 1.0)

    topics_raw = parsed.get("topics", []) or []
    topics = [str(t).strip().lower() for t in topics_raw if str(t).strip()]

    facet_signals = _ensure_all_facets(parsed.get("facet_signals", {}))

    one_line = parsed.get("one_line_insight", "") or ""
    if not one_line.strip():
        if sentiment <= -0.3:
            one_line = "Likely trigger detected; watch for early cues and quick escalation."
        else:
            one_line = "Notice what helped today and repeat it."

    # If journal is effectively empty, force neutral defaults regardless of LLM output
    if not journal.strip():
        emotions = [{"label": "neutral", "score": 0.0}]
        sentiment = 0.0
        topics = []
        facet_signals = _ensure_all_facets({})
        if not one_line:
            one_line = "Try noting one emotion and one trigger next time."

    result = {
        "emotions": emotions,
        "sentiment": sentiment,
        "cognitive_distortions": merged_distortions,
        "topics": topics,
        "facet_signals": facet_signals,
        "one_line_insight": one_line,
    }

    # Log a short preview for debugging
    try:
        _LOG.info(
            "analyze_entry complete",
            sentiment=sentiment,
            top_emotion=(emotions[0]["label"] if emotions else None),
            topics_preview=",".join(topics[:3]),
        )
    except Exception:
        pass

    return result
