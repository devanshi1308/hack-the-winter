import json
import re
from typing import Dict, Any, Optional

from logger.custom_logger import CustomLogger
from utils.model_loader import ModelLoader
from prompts.prompt_lib import PROMPT_REGISTRY

_LOG = CustomLogger().get_logger(__name__)


# ==================== KEYWORD PATTERNS ====================

# Strong intent phrases indicating immediate risk
_STRONG_INTENT = [
    r"\bi (?:want|wish|plan|am going|gonna)\s+to\s+(?:die|kill myself|end my life)\b",
    r"\bi (?:will|might)\s+(?:kill myself|end my life)\b",
    r"\bi can(?:not|'t)\s+(?:go on|live like this|take it anymore)\b",
    r"\bi (?:want|need)\s+to\s+(?:disappear|end it all)\b",
    r"\b(?:suicide|suicidal)\b",
    r"\bself-?harm\b",
    r"\bhurt myself\b",
]

# Method mentions (overdose, hanging, etc.)
_METHOD_MENTION = [
    r"\b(overdose|take pills|poison|jump(?:ing)?|hang(?:ing)?|cut(?:ting)?|slit|shoot(?:ing)?|knife|train|bridge)\b",
]

# Imminence indicators
_IMMINENCE = [
    r"\bright now\b",
    r"\btoday\b",
    r"\btonight\b",
    r"\bthis (?:morning|evening|afternoon)\b",
    r"\bsoon\b",
    r"\bcan'?t wait\b",
]

# Despair/hopelessness indicators
_DESPAIR = [
    r"\bhopeless\b",
    r"\bno point\b",
    r"\bworthless\b",
    r"\bnothing matters\b",
    r"\bgive up\b",
    r"\bno reason to (?:live|go on)\b",
    r"\beveryone (?:would be|is) better (?:off )?without me\b",
]

# Farewell/goodbye patterns
_FAREWELL = [
    r"\bgoodbye\b",
    r"\bfarewell\b",
    r"\blast (?:time|message|words)\b",
    r"\btake care of (?:yourself|my)\b",
    r"\bi'?m sorry for everything\b",
]


# ==================== HELPER FUNCTIONS ====================

def _ensure_llm(llm=None):
    """Load LLM or allow fallback to None for keyword-only mode."""
    if llm is not None:
        return llm
    try:
        return ModelLoader().load_llm()
    except Exception as e:
        _LOG.error("Failed to load LLM in safety_checker", error=str(e))
        return None


def _json_salvage(text: str) -> Dict[str, Any]:
    """Extract JSON from LLM response that might have extra text."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not parse JSON from LLM output.")


def _keyword_risk(text: str) -> Dict[str, Any]:
    """
    Perform keyword-based risk detection.
    
    Returns:
        Dict with 'flagged' (bool) and 'reasons' (list of matched categories)
    """
    t = (text or "").lower()
    if not t.strip():
        return {"flagged": False, "reasons": []}
    
    reasons = []
    
    # Check strong intent
    for pat in _STRONG_INTENT:
        if re.search(pat, t):
            reasons.append("strong_intent")
            break
    
    # Check method mention
    method_hit = any(re.search(p, t) for p in _METHOD_MENTION)
    if method_hit:
        reasons.append("method_mention")
    
    # Check imminence
    imminence_hit = any(re.search(p, t) for p in _IMMINENCE)
    if imminence_hit:
        reasons.append("imminence")
    
    # Check despair
    despair_hit = any(re.search(p, t) for p in _DESPAIR)
    if despair_hit:
        reasons.append("despair")
    
    # Check farewell
    farewell_hit = any(re.search(p, t) for p in _FAREWELL)
    if farewell_hit:
        reasons.append("farewell")
    
    # Escalate if strong intent OR (method + desire/intent context)
    desire_hit = bool(re.search(r"\bi (?:want|plan|intend|need)\b", t))
    
    # Decision logic
    if "strong_intent" in reasons:
        return {"flagged": True, "reasons": reasons}
    
    if method_hit and desire_hit:
        if "method_mention" not in reasons:
            reasons.append("method_mention")
        reasons.append("intent_with_method")
        return {"flagged": True, "reasons": reasons}
    
    if ("despair" in reasons or "farewell" in reasons) and imminence_hit:
        reasons.append("despair_with_imminence")
        return {"flagged": True, "reasons": reasons}
    
    # If any reasons but not critical combination, return flagged=True for monitoring
    if reasons:
        return {"flagged": True, "reasons": reasons}
    
    return {"flagged": False, "reasons": []}


def _compute_risk_score(
    label: str, 
    keyword_result: Dict[str, Any], 
    text: str
) -> int:
    """
    Compute risk score (0-100) based on label and signals.
    
    Args:
        label: "SAFE" or "ESCALATE"
        keyword_result: Result from _keyword_risk()
        text: Original text
    
    Returns:
        Risk score (0-100)
    """
    score = 0
    
    # Base score from label
    if label == "ESCALATE":
        score = 70  # High baseline for escalation
    else:
        score = 10  # Low baseline for safe
    
    # Keyword signals add to score
    reasons = keyword_result.get("reasons", [])
    
    if "strong_intent" in reasons:
        score += 20
    if "method_mention" in reasons:
        score += 10
    if "imminence" in reasons:
        score += 10
    if "despair" in reasons:
        score += 5
    if "farewell" in reasons:
        score += 5
    if "intent_with_method" in reasons:
        score += 15
    if "despair_with_imminence" in reasons:
        score += 10
    
    # Additional text analysis
    text_lower = (text or "").lower()
    if "imminent" in text_lower or "right now" in text_lower:
        score += 10
    if "plan" in text_lower and any(w in text_lower for w in ["suicide", "die", "kill myself"]):
        score += 10
    
    # Cap at 100
    return min(score, 100)


def _compute_risk_band(risk_score: int) -> str:
    """
    Convert risk score to risk band.
    
    Args:
        risk_score: Score from 0-100
    
    Returns:
        "green" (< 30), "yellow" (30-60), or "red" (> 60)
    """
    if risk_score < 30:
        return "green"
    elif risk_score <= 60:
        return "yellow"
    else:
        return "red"


# ==================== MAIN API ====================

def classify_risk(
    text: str, 
    llm=None, 
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Classify a journal/message for imminent self-harm risk.
    
    Strategy:
      1) Run keyword heuristic first (fast screen + fallback)
      2) Try LLM with strict JSON prompt for semantic analysis
      3) Combine signals: if keywords flag risk, escalate regardless of LLM
      4) Compute risk_score (0-100) and risk_band (green/yellow/red)
      5) Return comprehensive result
    
    Args:
        text: User input text to analyze
        llm: Optional pre-loaded LLM instance
        user_id: Optional user identifier for logging
        session_id: Optional session identifier for logging
    
    Returns:
        Dict with:
            - label: "SAFE" or "ESCALATE"
            - risk_score: 0-100
            - risk_band: "green", "yellow", or "red"
            - signals: {"keywords": {...}, "llm": str}
            - policy_message: Non-clinical boundary statement
    """
    # Keyword heuristic first
    keyword_result = _keyword_risk(text)
    kw_flag = keyword_result.get("flagged", False)
    
    signals = {
        "keywords": keyword_result,
        "llm": None
    }
    
    label = "SAFE"
    policy_message = (
        "This system is not a crisis or clinical service. If you or someone you know is at risk, "
        "please seek immediate help from a professional or emergency services. We do not provide "
        "medical advice or intervention."
    )
    
    # Try LLM analysis
    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            prompt = PROMPT_REGISTRY.get("safety_check")
            if prompt is None:
                _LOG.warning("safety_check prompt not found in registry")
            else:
                messages = prompt.format_messages(text=text or "")
                resp = chat.invoke(messages)
                raw = getattr(resp, "content", None) or str(resp)
                
                try:
                    parsed = json.loads(raw)
                except Exception:
                    parsed = _json_salvage(raw)
                
                llm_label = str(parsed.get("label", "SAFE")).upper()
                if llm_label not in {"SAFE", "ESCALATE"}:
                    llm_label = "SAFE"
                
                signals["llm"] = llm_label
                label = llm_label
                
        except Exception as e:
            _LOG.error("LLM safety_check failed; using keyword fallback", error=str(e))
            signals["llm"] = None
    
    # If keywords flag risk, override to ESCALATE (keywords act as veto)
    if kw_flag:
        label = "ESCALATE"
        _LOG.info("Keywords flagged risk; overriding to ESCALATE", 
                 reasons=keyword_result.get("reasons"))
    
    # Compute risk score and band
    risk_score = _compute_risk_score(label, keyword_result, text)
    risk_band = _compute_risk_band(risk_score)
    
    # Log result
    _LOG.info(
        "classify_risk result",
        label=label,
        risk_score=risk_score,
        risk_band=risk_band,
        keyword_flagged=kw_flag,
        llm_available=chat is not None,
        user_id=user_id,
        session_id=session_id
    )
    
    return {
        "label": label,
        "risk_score": risk_score,
        "risk_band": risk_band,
        "signals": signals,
        "policy_message": policy_message
    }


def escalation_message(locale: str = "en") -> str:
    """
    Compassionate, non-judgmental message shown when risk is detected.
    Keep generic (no medical advice). Localize per `locale` if needed.
    
    Args:
        locale: Language/locale code (default: "en")
    
    Returns:
        Escalation message string
    """
    if (locale or "en").lower().startswith("en"):
        return (
            "I'm really sorry you're going through this. You're not alone, and your safety matters. "
            "If you feel in immediate danger, please contact your local emergency services right now. "
            "You might also consider reaching out to someone you trust or a trained listener in your region. "
            "If you'd like, I can keep things simple here—we can take one small step at a time."
        )
    
    # Default for other locales
    return (
        "I'm sorry you're going through this. Your safety matters. "
        "If you're in immediate danger, please contact local emergency services. "
        "Consider reaching out to someone you trust or a trained listener in your area."
    )


def get_crisis_resources(country_code: str = "US") -> Dict[str, Any]:
    """
    Return crisis helpline resources by country.
    """
    resources = {
        "US": {
            "name": "988 Suicide & Crisis Lifeline",
            "phone": "988",
            "text": "Text 988",
            "website": "https://988lifeline.org"
        },
        "UK": {
            "name": "Samaritans",
            "phone": "116 123",
            "website": "https://www.samaritans.org"
        },
        "CA": {
            "name": "Talk Suicide Canada",
            "phone": "1-833-456-4566",
            "text": "Text 45645",
            "website": "https://talksuicide.ca"
        },
        "AU": {
            "name": "Lifeline Australia",
            "phone": "13 11 14",
            "website": "https://www.lifeline.org.au"
        },
        "IN": {
            "name": "AASRA",
            "phone": "91-9820466726",
            "website": "http://www.aasra.info"
        }
    }
    
    return resources.get(country_code, {
        "name": "International Association for Suicide Prevention",
        "website": "https://www.iasp.info/resources/Crisis_Centres/"
    })