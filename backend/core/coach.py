from __future__ import annotations

import re
from typing import Dict, Any, List, Optional

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from prompts.prompt_lib import PROMPT_REGISTRY  


_LOG = CustomLogger().get_logger(__name__)

def _ensure_llm(llm=None):
    """Return provided llm or load a default chat model."""
    if llm is not None:
        return llm
    try:
        return ModelLoader().load_llm()
    except Exception as e:
        _LOG.error("Failed to load LLM in coach module", error=str(e))
        return None  # allow fallbacks


def _truncate_words(text: str, max_words: int) -> str:
    words = text.strip().split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"


def _sanitize_coach_output(text: str, max_words: int = 90, max_sentences: int = 2) -> str:
    """Clean LLM output, keep 1–2 sentences, and ensure a reflective question is present."""
    t = (text or "").strip()
    if not t:
        return "I hear you. What feels most present for you right now?"

    # Remove code fences and obvious metadata lines
    lines = []
    for line in t.splitlines():
        s = line.strip().strip("` ")
        if not s:
            continue
        lower = s.lower()
        if lower.startswith(("facet:", "emotions:", "last_entry_summary:", "state:", "metadata:")):
            continue
        lines.append(s)
    t = " ".join(lines)

    # Split into sentences conservatively
    import re
    parts = re.split(r"(?<=[.!?])\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return "I’m with you in this. What would feel most supportive right now?"

    # Keep the first N sentences
    selected = parts[:max_sentences]
    out = " ".join(selected)

    # Word limit
    words = out.split()
    if len(words) > max_words:
        out = " ".join(words[:max_words]).rstrip(",.;:") + "…"

    # Ensure at least one question
    if "?" not in out:
        out = out.rstrip(". ") + " What feels most important to explore next?"

    return out


def _facet_fallback_question(facet: str, emotions: List[Dict[str, Any]], last_summary: str) -> str:
    """Facet-aware default question when LLM isn't available."""
    emo = (emotions[0]["label"] if emotions else "").lower()
    facet = (facet or "").lower()

    if facet == "self_regulation":
        if emo in {"anger", "anxiety", "fear", "stress"}:
            return "What was the very first cue in your body before the emotion rose?"
        return "What small action helps you regain calm when emotions rise?"

    if facet == "self_awareness":
        return "What emotion did you notice first, and what triggered it?"

    if facet == "empathy":
        return "What might the other person be feeling or needing right now?"

    if facet == "social_skills":
        return "What outcome do you want from the next conversation about this?"

    if facet == "motivation":
        return "What is one five-minute step you can take today toward your goal?"

    return "What did you notice in yourself just before the feeling emerged?"


def _fallback_insight(user_reply: str) -> str:
    s = user_reply.strip()
    if not s:
        return "Noted: you paused to reflect on your experience."
    s = s.replace("\n", " ")
    s = _truncate_words(s, 20)
    return f"Noted: you identified “{s}” as meaningful."

def coach_question(state: Dict[str, Any], llm=None) -> str:
    """
    Generate exactly one brief reflective question (≤ ~20 words).
    state: { "facet": str, "emotions": [{"label": str, "score": float}], "last_entry_summary": str }
    """
    facet = (state or {}).get("facet", "")
    emotions = (state or {}).get("emotions", []) or []
    last_summary = (state or {}).get("last_entry_summary", "") or ""

    # try LLM first if available
    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            prompt = PROMPT_REGISTRY["coach_question"]
            messages = prompt.format_messages(
                facet=facet,
                emotions_json=str(emotions),
                last_entry_summary=last_summary
            )
            resp = chat.invoke(messages)
            raw = getattr(resp, "content", None) or str(resp)
            q = _sanitize_coach_output(raw, max_words=90, max_sentences=2)
            return q
        except Exception as e:
            _LOG.error("coach_question LLM failed; using fallback", error=str(e))

    # without LLM
    return _facet_fallback_question(facet, emotions, last_summary)


def coach_followup(user_id: str, last_exchange: Dict[str, Any], llm=None) -> Dict[str, str]:
    """
    Turn user's reflection reply into one neutral, short insight line.
    last_exchange: { "facet": str, "user_reply": str }
    Returns: { "insight_line": str }
    """
    facet = (last_exchange or {}).get("facet", "")
    user_reply = (last_exchange or {}).get("user_reply", "") or ""

    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            system = (
                "You are an empathetic EI coach. "
                "Summarize the user's reflection in ONE short, neutral insight sentence. "
                "Avoid advice, judgments, or multiple sentences. ≤ 25 words."
            )
            user = (
                f"Facet: {facet}\n"
                f"User reflection: {user_reply}\n"
                "Return only the insight sentence."
            )
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            resp = chat.invoke(messages)
            text = getattr(resp, "content", None) or str(resp)
            # Keep to one short line
            line = text.strip().splitlines()[0].strip()
            line = _truncate_words(line, 25)
            # Remove trailing quotes
            line = line.strip(" '\"")
            return {"insight_line": line}
        except Exception as e:
            _LOG.error("coach_followup LLM failed; using fallback", error=str(e))

    # without LLM
    return {"insight_line": _fallback_insight(user_reply)}


# Team collaboration functions
def rewrite_message(text: str, intent: str = "assertive_kind", llm=None) -> Dict[str, Any]:
    """
    Rewrite a message to be more assertive, kind, and specific.
    Returns: {"rewrite": str, "removed_terms": List[str]}
    """
    from core.journal_analyzer import apply_distortion_rules
    
    # Identify problematic patterns first
    removed_terms = []
    
    # Check for heat words using distortion rules
    distortions = apply_distortion_rules(text)
    if distortions:
        removed_terms.extend(distortions)
    
    # Additional heat word patterns
    heat_patterns = ["always", "never", "you should", "you need to", "obviously", "clearly"]
    text_lower = text.lower()
    for pattern in heat_patterns:
        if pattern in text_lower:
            removed_terms.append(pattern)
    
    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            prompt = PROMPT_REGISTRY.get("collab_rewrite")
            if prompt:
                messages = prompt.format_messages(text=text, intent=intent)
                resp = chat.invoke(messages)
                rewritten = getattr(resp, "content", None) or str(resp)
                rewritten = rewritten.strip()
                
                return {
                    "rewrite": rewritten[:500],  # Cap length
                    "removed_terms": list(set(removed_terms))  # Deduplicate
                }
        except Exception as e:
            _LOG.error("rewrite_message LLM failed; using minimal rewrite", error=str(e))
    
    # Fallback: minimal cleanup
    cleaned = text.replace("you should", "consider").replace("you need to", "it might help to")
    cleaned = cleaned.replace("obviously", "").replace("clearly", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    
    return {
        "rewrite": cleaned,
        "removed_terms": list(set(removed_terms))
    }


def meeting_debrief(notes: str, llm=None) -> Dict[str, Any]:
    """
    Structure meeting notes into tensions, feelings/needs, agreements, next steps.
    Returns: {"tensions": [], "feelings_needs": [], "agreements": [], "next_steps": []}
    """
    chat = _ensure_llm(llm)
    if chat is not None:
        try:
            prompt = PROMPT_REGISTRY.get("collab_debrief")
            if prompt:
                messages = prompt.format_messages(notes=notes)
                resp = chat.invoke(messages)
                raw = getattr(resp, "content", None) or str(resp)
                
                # Try to parse JSON
                import json
                try:
                    # Remove markdown formatting if present
                    cleaned = raw.strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    
                    result = json.loads(cleaned.strip())
                    
                    # Validate structure
                    expected_keys = ["tensions", "feelings_needs", "agreements", "next_steps"]
                    if all(key in result for key in expected_keys):
                        return result
                        
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            _LOG.error("meeting_debrief LLM failed; using fallback structure", error=str(e))
    
    # Fallback: simple keyword-based extraction
    lines = [line.strip() for line in notes.split('\n') if line.strip()]
    
    tensions = []
    feelings_needs = []
    agreements = []
    next_steps = []
    
    for line in lines:
        line_lower = line.lower()
        if any(word in line_lower for word in ["conflict", "tension", "disagreement", "issue", "problem"]):
            tensions.append(line[:200])
        elif any(word in line_lower for word in ["feel", "need", "want", "concerned", "frustrated"]):
            feelings_needs.append(line[:200])
        elif any(word in line_lower for word in ["agree", "decided", "consensus", "commit"]):
            agreements.append(line[:200])
        elif any(word in line_lower for word in ["action", "todo", "next", "follow up", "will"]):
            next_steps.append({"owner": "TBD", "due": "TBD", "task": line[:200]})
    
    return {
        "tensions": tensions,
        "feelings_needs": feelings_needs,
        "agreements": agreements,
        "next_steps": next_steps
    }