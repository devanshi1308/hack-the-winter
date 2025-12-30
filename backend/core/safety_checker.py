import json
import re
from typing import Dict, Any, List

from logger.custom_logger import CustomLogger
from utils.model_loader import ModelLoader
from prompts.prompt_lib import PROMPT_REGISTRY  # expects "safety_check"

_LOG = CustomLogger().get_logger(__name__)

def _ensure_llm(llm=None):
    if llm is not None:
        return llm
    try:
        return ModelLoader().load_llm()
    except Exception as e:
        _LOG.error("Failed to load LLM in safety_checker", error=str(e))
        return None  # allow keyword fallback


def _json_salvage(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("Could not parse JSON from LLM output.")


# A lightweight keyword/phrase heuristic as a guard-rail and fallback
_STRONG_INTENT = [
    r"\bi (?:want|wish|plan|am going|gonna)\s+to\s+(?:die|kill myself|end my life)\b",
    r"\bi (?:will|might)\s+(?:kill myself|end my life)\b",
    r"\bi can(?:not|'t)\s+go on\b",
    r"\bi (?:want|need)\s+to\s+(?:disappear|end it all)\b",
    r"\bsuicide\b",
    r"\bself-?harm\b",
]

_METHOD_MENTION = [
    r"\b(overdose|take pills|poison|jump|hang|cut|cutting|slit|shoot|knife|train|bridge)\b",
]

_IMMINENCE = [
    r"\bright now\b",
    r"\btoday\b",
    r"\btonight\b",
    r"\bthis (?:morning|evening|afternoon)\b",
]


def _keyword_risk(text: str) -> bool:
    t = (text or "").lower()
    if not t.strip():
        return False

    # If any strong intent phrase matched  escalate
    for pat in _STRONG_INTENT:
        if re.search(pat, t):
            return True

    # If method + desire/intent context appears  escalate
    method_hit = any(re.search(p, t) for p in _METHOD_MENTION)
    desire_hit = bool(re.search(r"\bi (?:want|plan|intend|need)\b", t))
    if method_hit and desire_hit:
        return True

    # If suicide mentioned + imminence cue  escalate
    suicide_hit = "suicide" in t or "end my life" in t or "kill myself" in t
    imminence_hit = any(re.search(p, t) for p in _IMMINENCE)
    if suicide_hit and imminence_hit:
        return True

    # Generic strong despair + imminence
    despair = bool(re.search(r"\b(hopeless|no point|worthless|nothing matters)\b", t))
    if despair and imminence_hit:
        return True

    return False


def classify_risk(text: str, llm) -> dict:
    """
    Classify a journal/message for imminent self-harm risk.
    Returns: {"label": "SAFE" | "ESCALATE"}
    Strategy:
      1) Try LLM with strict JSON prompt
      2) Validate label
      3) ALSO run keyword fallback; if it flags risk, escalate regardless
      4) On any exception, rely on keyword fallback
    """
    # Keyword heuristic first as a quick screen
    kw_flag = _keyword_risk(text)

    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            prompt = PROMPT_REGISTRY["safety_check"]  # ChatPromptTemplate
            messages = prompt.format_messages(text=text or "")
            resp = chat.invoke(messages)
            raw = getattr(resp, "content", None) or str(resp)

            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = _json_salvage(raw)

            label = str(parsed.get("label", "SAFE")).upper()
            if label not in {"SAFE", "ESCALATE"}:
                label = "SAFE"

            # If keyword flag trips, override to ESCALATE
            if kw_flag:
                label = "ESCALATE"

            _LOG.info("classify_risk result", label=label)
            return {"label": label}
        except Exception as e:
            _LOG.error("LLM safety_check failed; using keyword fallback", error=str(e))

    # Fallback purely on keywords
    return {"label": "ESCALATE" if kw_flag else "SAFE"}


def escalation_message(locale: str = "en") -> str:
    """
    Compassionate, non-judgmental message shown when risk is detected.
    Keep generic (no medical advice). You can localize per `locale` if needed.
    """
    if (locale or "en").lower().startswith("en"):
        return (
            "I'm really sorry you're going through this. You’re not alone, and your safety matters. "
            "If you feel in immediate danger, please contact your local emergency services right now. "
            "You might also consider reaching out to someone you trust or a trained listener in your region. "
            "If you’d like, I can keep things simple here—we can take one small step at a time."
        )

    # Simple default for other locales; customize as you add translations
    return (
        "I'm sorry you're going through this. Your safety matters. "
        "If you're in immediate danger, please contact local emergency services. "
        "Consider reaching out to someone you trust or a trained listener in your area."
    )
