from fastapi import FastAPI, Request, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from datetime import date
import json
import os
from typing import List, Optional
import requests
import asyncio
import io
import uuid
from dotenv import load_dotenv
from model.models import CrisisEvent, CrisisEventStatus
from utils.elevenlabs_client import get_elevenlabs
from utils.model_loader import ModelLoader
from prompts.prompt_lib import PROMPT_REGISTRY
from rag.rag_pipeline import SingleDocumentIngestor, ConversationalRAG
from core.recommender import prepare_recommendation
from utils.web_search import WebSearch
from core.safety_checker import classify_risk, escalation_message
from core.orchestrator import Orchestrator
from core.memory import MemoryManager
from model.models import (
    BaselineRequest, BaselineResponse, BaselineScores,
    SafetyCheckRequest, SafetyCheckResponse, SafetyLabel,
    ImageAnalysisRequest, ImageAnalysisResponse,
)
from db.mongo import get_mongo
from logger.custom_logger import CustomLogger
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Load environment variables from .env (local dev)
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Get API Keys from environment only (no API URLs)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

# Conversation history per session
conversation_history = {}

async def call_llm(prompt: str, session_id: str = "default", conversation_context: str = ""):
    """
    Call LLM via LangChain abstraction (OpenAI → Gemini → Groq → fallback).
    Maintains conversation history to avoid repetitive responses.
    """
    # Initialize session history if needed
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    # Add user message to history
    conversation_history[session_id].append({"role": "user", "content": prompt})
    
    # Keep only last 10 messages to avoid token limits
    if len(conversation_history[session_id]) > 10:
        conversation_history[session_id] = conversation_history[session_id][-10:]

    SYSTEM_PROMPT = """You are 'Aura', a compassionate and non-judgmental AI emotional wellness companion. 
Your role is to listen empathetically, validate the user's feelings, and offer reflective questions or gentle coping suggestions.

IMPORTANT RULES:
1. Never repeat the same question or response pattern twice in a row
2. Build on the conversation - reference what the user just said
3. Ask specific follow-up questions based on their actual words
4. Vary your response style - don't always ask "What part feels heaviest?"
5. Show you're truly listening by addressing their specific emotion or situation
6. Keep responses under 50 words, supportive and focused

Do not diagnose or offer professional medical advice."""

    # Try LangChain LLM abstraction
    try:
        llm = ModelLoader().load_llm()
        
        # Build messages for LangChain
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        
        if conversation_context:
            messages.append(SystemMessage(content=f"Recent conversation context: {conversation_context}"))
        
        # Add conversation history
        for msg in conversation_history[session_id][:-1]:  # Exclude last user msg (already added below)
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current prompt
        messages.append(HumanMessage(content=prompt))
        
        # Invoke LLM
        response = llm.invoke(messages)
        assistant_message = getattr(response, "content", None) or str(response)
        assistant_message = (assistant_message or "").strip()
        
        if assistant_message:
            conversation_history[session_id].append({"role": "assistant", "content": assistant_message})
            return assistant_message
    except Exception as e:
        _LOG = CustomLogger().get_logger(__name__)
        _LOG.warning("LangChain LLM call failed, using fallback", error=str(e))
    
    # Smart fallback if LLM fails
    assistant_message = generate_contextual_fallback(prompt, conversation_history[session_id])
    conversation_history[session_id].append({"role": "assistant", "content": assistant_message})
    return assistant_message


def generate_contextual_fallback(current_message: str, history: list) -> str:
    """
    Heuristic, empathetic fallback response when no LLM key is available.
    Uses conversation history to avoid repetitive responses.
    """
    msg = (current_message or "").strip()
    if not msg:
        return "I'm here with you. What's been on your mind today?"

    lower = msg.lower()
    
    # Get last assistant response to avoid repetition
    last_response = ""
    for msg_obj in reversed(history):
        if msg_obj.get("role") == "assistant":
            last_response = msg_obj.get("content", "").lower()
            break
    
    # Detect specific emotions and situations
    if any(w in lower for w in ["pissed", "angry", "mad", "furious", "rage"]):
        if "friend" in lower or "relationship" in lower:
            responses = [
                "Anger toward someone we care about can be really complicated. What do you think triggered this feeling?",
                "It's tough when someone close to us makes us angry. What boundary feels crossed here?",
                "That mix of caring and anger is hard to sit with. What would you want them to understand?",
            ]
        else:
            responses = [
                "That anger sounds intense. What happened that sparked this?",
                "I hear that frustration. What would help you process this feeling right now?",
                "What do you think is underneath the anger?",
            ]
        # Pick response that wasn't just used
        for r in responses:
            if r.lower() not in last_response and last_response not in r.lower():
                return r
        return responses[0]
    
    if any(w in lower for w in ["confused", "don't know", "unsure", "unclear"]):
        responses = [
            "Confusion is valid. Let's explore this together - what feels most cloudy right now?",
            "Not knowing is okay. What's one small piece you do feel clear about?",
            "When things feel unclear, sometimes it helps to name what you do know. What's certain for you right now?",
        ]
        for r in responses:
            if r.lower() not in last_response:
                return r
        return responses[0]
    
    if any(w in lower for w in ["relationship", "dating", "girlfriend", "boyfriend", "ex"]):
        return "Relationship dynamics can be complex. What aspect of this situation feels most pressing to you?"
    
    if any(w in lower for w in ["stuck", "decision", "choose", "choice"]):
        return "Being at a crossroads is uncomfortable. What values or priorities feel most important as you consider this?"
    
    if any(w in lower for w in ["sad", "down", "blue", "depressed"]):
        return "I hear the sadness in what you're sharing. What do you need most in this moment?"
    
    if any(w in lower for w in ["anxious", "worried", "nervous", "anxiety"]):
        return "Anxiety can be overwhelming. What feels most out of control right now?"
    
    if any(w in lower for w in ["stressed", "overwhelmed", "pressure"]):
        return "That sounds like a lot to carry. What's one thing that might lighten the load, even slightly?"
    
    # Generic contextual responses that vary
    if len(msg) < 15:
        return "Tell me more - I'm listening."
    
    responses = [
        "I appreciate you sharing that with me. What else is present for you?",
        "That's important information. How is this affecting you right now?",
        "I'm here with you in this. What matters most to you about this situation?",
        "Thank you for trusting me with this. What would feel supportive right now?",
    ]
    
    for r in responses:
        if r.lower() not in last_response:
            return r
    return responses[0]

@app.get("/health")
async def health():
    db_connected = False
    try:
        mongo = get_mongo()
        # lightweight ping
        mongo.client.admin.command("ping")
        db_connected = True
    except Exception:
        db_connected = False
    return {
        "status": "ok",
        "retriever_ready": True,
        "ai_enabled": bool(OPENAI_API_KEY or GEMINI_API_KEY),
        "llm_provider": "openai" if OPENAI_API_KEY else ("gemini" if GEMINI_API_KEY else "fallback"),
        "db_connected": db_connected,
    }

@app.post("/api/collab/rewrite")
async def collab_rewrite(request: Request):
    """
    Rewrite collaborative messages to be assertive, kind, and specific.
    Uses OpenAI-first LLM via ModelLoader and the collab_rewrite prompt
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    text = (payload.get("text") or "").strip()
    # style is optional; we map it to intent if present
    style = (payload.get("style") or "").strip()
    intent = (payload.get("intent") or style or "clear, concise, and warm").strip()

    if not text:
        raise HTTPException(status_code=400, detail="'text' is required")

    # Build prompt messages
    prompt = PROMPT_REGISTRY.get("collab_rewrite")
    if prompt is None:
        raise HTTPException(status_code=500, detail="Rewrite prompt not available")

    messages = prompt.format_messages(text=text, intent=intent)

    # Invoke LLM (OpenAI → Google → Groq) via ModelLoader
    try:
        llm = ModelLoader().load_llm()
        resp = llm.invoke(messages)
        # LangChain BaseMessage-like with .content
        rewritten = getattr(resp, "content", None) or (resp if isinstance(resp, str) else "")
        rewritten = (rewritten or "").strip()
        if not rewritten:
            raise ValueError("Empty response from LLM")
        return {"rewrittenText": rewritten}
    except Exception as e:
        # Heuristic offline fallback: trim, collapse whitespace, sentence-case first letter
        try:
            cleaned = " ".join(text.split())
            if cleaned:
                guess = cleaned[:1].upper() + cleaned[1:]
                return {"rewrittenText": guess}
        except Exception:
            pass
        _LOG = CustomLogger().get_logger(__name__)
        _LOG.error("collab_rewrite failed", error=str(e))
        raise HTTPException(status_code=502, detail="Failed to rewrite text")

@app.get("/analytics/checkin/questions")
async def get_questions():
    return {
        "questions": [
            {"id": "mood", "text": "How are you feeling today?", "scale": "1=Very Low, 5=Very High"},
            {"id": "stress", "text": "How stressed did you feel today?", "scale": "1=Not at all, 5=Extremely"},
            {"id": "energy", "text": "What's your energy level right now?", "scale": "1=Very Low, 5=Very High"},
            {"id": "connection", "text": "How connected did you feel to others today?", "scale": "1=Not at all, 5=Very Connected"},
            {"id": "motivation", "text": "How motivated did you feel today?", "scale": "1=Not at all, 5=Extremely"}
        ]
    }

@app.post("/analytics/checkin")
async def submit_checkin(request: Request):
    data = await request.json()
    responses = {k: v for k, v in data.items() if k not in ["user_id", "date"]}
    values = list(responses.values())
    avg = sum(values) / len(values) if values else 3
    mood_index = ((avg - 1) / 4) * 100
    
    return {
        "mood_index": round(mood_index, 2),
        "ema7": round(mood_index, 2),
        "ema14": round(mood_index, 2),
        "zscore": 0.0,
        "flag": "SAFE"
    }

@app.post("/ai/analyze-entry")
async def analyze_entry(request: Request):
    data = await request.json()
    text = data.get("journal", "")
    user_id = data.get("user_id")
    session_id = data.get("session_id")
    
    # Real AI analysis
    analysis_prompt = f"""
    Analyze this journal entry for emotional content. Respond in JSON format:
    {{
        "emotions": [list of {{"label": "emotion_name", "score": 0.0-1.0}}],
        "sentiment": -1.0 to 1.0,
        "insights": "brief insight about the emotional state",
        "recommendations": ["list of 2-3 helpful suggestions"]
    }}
    
    Journal entry: "{text}"
    """
    
    ai_response = await call_llm(analysis_prompt, session_id=session_id or "journal")
    
    # Try to parse AI response, fallback if needed
    try:
        # Extract JSON from AI response
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        if start != -1 and end > start:
            ai_data = json.loads(ai_response[start:end])
        else:
            raise ValueError("No JSON found")
    except:
        # Fallback analysis
        emotions = []
        text_lower = text.lower()
        if any(w in text_lower for w in ["happy", "good", "great"]): emotions.append({"label": "Joy", "score": 0.8})
        if any(w in text_lower for w in ["sad", "down", "upset"]): emotions.append({"label": "Sadness", "score": 0.7})
        if any(w in text_lower for w in ["angry", "mad", "frustrated"]): emotions.append({"label": "Anger", "score": 0.6})
        if not emotions: emotions.append({"label": "Reflection", "score": 0.5})
        
        ai_data = {
            "emotions": emotions,
            "sentiment": 0.1,
            "insights": "Continue reflecting on your experiences",
            "recommendations": ["Practice mindfulness", "Consider talking to someone", "Take care of your basic needs"]
        }
    
    result = {
        "safety": {"label": "SAFE"},
        "analysis": {
            "emotions": ai_data.get("emotions", []),
            "sentiment": ai_data.get("sentiment", 0),
            "cognitive_distortions": [],
            "topics": ["reflection"],
            "facet_signals": {"self_awareness": "0", "self_regulation": "0", "motivation": "0", "empathy": "0", "social_skills": "0"},
            "one_line_insight": ai_data.get("insights", "Continue reflecting")
        },
        "recommendation": {
            "exercise_id": "ai_suggested",
            "title": "Personalized Exercise",
            "steps": ai_data.get("recommendations", ["Take a deep breath", "Reflect on your feelings"]),
            "expected_outcome": "Improved emotional awareness",
            "source_doc_id": "ai_generated",
            "followup_question": "How do you feel after trying this?"
        }
    }

    # derive mood_index from sentiment (-1..1 -> 0..100)
    try:
        sentiment = float(result["analysis"]["sentiment"])
        mood_index = max(0.0, min(100.0, ((sentiment + 1.0) / 2.0) * 100.0))
    except Exception:
        mood_index = 50.0

    # best-effort persistence
    try:
        if user_id and session_id:
            mongo = get_mongo()
            # user journal message
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": text,
                "metadata": {"source": "journal", "mood_index": mood_index},
            })
            # assistant analysis summary
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": result["analysis"].get("one_line_insight", ""),
                "metadata": {"source": "analysis", "mood_index": mood_index},
            })
    except Exception:
        pass

    return result

@app.post("/ai/analyze-entry-upload")
async def analyze_entry_upload(
    text: Optional[str] = Form(default=""),
    user_id: Optional[str] = Form(default=None),
    session_id: Optional[str] = Form(default=None),
    mood: Optional[int] = Form(default=None),
    file: Optional[UploadFile] = File(default=None),
):
    """
    Multipart variant of analyze-entry that accepts optional image/audio upload.
    Currently, the uploaded file is acknowledged but not processed; analysis is
    performed on text only. This keeps parity with JSON endpoint while allowing
    clients to send attachments.
    """
    journal_text = text or ""

    # Build prompt (note attachment presence)
    attachment_hint = " An image was attached." if file is not None else ""
    analysis_prompt = f"""
    Analyze this journal entry for emotional content. Respond in JSON format:
    {{
        "emotions": [list of {{"label": "emotion_name", "score": 0.0-1.0}}],
        "sentiment": -1.0 to 1.0,
        "insights": "brief insight about the emotional state",
        "recommendations": ["list of 2-3 helpful suggestions"]
    }}

    Journal entry: "{journal_text}"
    {attachment_hint}
    """

    ai_response = await call_llm(analysis_prompt, session_id=session_id or "journal")

    # Try to parse AI response, fallback if needed
    try:
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        if start != -1 and end > start:
            ai_data = json.loads(ai_response[start:end])
        else:
            raise ValueError("No JSON found")
    except:
        emotions = []
        txt = journal_text.lower()
        if any(w in txt for w in ["happy", "good", "great"]): emotions.append({"label": "Joy", "score": 0.8})
        if any(w in txt for w in ["sad", "down", "upset"]): emotions.append({"label": "Sadness", "score": 0.7})
        if any(w in txt for w in ["angry", "mad", "frustrated"]): emotions.append({"label": "Anger", "score": 0.6})
        if not emotions: emotions.append({"label": "Reflection", "score": 0.5})

        ai_data = {
            "emotions": emotions,
            "sentiment": 0.1,
            "insights": "Continue reflecting on your experiences",
            "recommendations": ["Practice mindfulness", "Consider talking to someone", "Take care of your basic needs"],
        }

    result = {
        "safety": {"label": "SAFE"},
        "analysis": {
            "emotions": ai_data.get("emotions", []),
            "sentiment": ai_data.get("sentiment", 0),
            "cognitive_distortions": [],
            "topics": ["reflection"],
            "facet_signals": {"self_awareness": "0", "self_regulation": "0", "motivation": "0", "empathy": "0", "social_skills": "0"},
            "one_line_insight": ai_data.get("insights", "Continue reflecting"),
        },
        "recommendation": {
            "exercise_id": "ai_suggested",
            "title": "Personalized Exercise",
            "steps": ai_data.get("recommendations", ["Take a deep breath", "Reflect on your feelings"]),
            "expected_outcome": "Improved emotional awareness",
            "source_doc_id": "ai_generated",
            "followup_question": "How do you feel after trying this?",
        },
    }

    # derive mood_index from sentiment
    try:
        sentiment = float(result["analysis"]["sentiment"])
        mood_index = max(0.0, min(100.0, ((sentiment + 1.0) / 2.0) * 100.0))
    except Exception:
        mood_index = 50.0

    # best-effort persistence
    try:
        if user_id and session_id:
            mongo = get_mongo()
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": journal_text,
                "metadata": {"source": "journal", "mood_index": mood_index, "attachment": bool(file)},
            })
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": result["analysis"].get("one_line_insight", ""),
                "metadata": {"source": "analysis", "mood_index": mood_index},
            })
    except Exception:
        pass

    return result

# REAL-TIME CHATBOT
chat_sessions = {}

# Add this to your backend/app.py if it's not there:

@app.post("/chat/mood")
async def chat_mood(request: Request):
    data = await request.json()
    message = data.get("message", "")
    user_id = data.get("user_id")
    session_id = data.get("session_id", "default")
    
    # Safety check first
    if any(word in message.lower() for word in ["die", "kill", "hurt", "suicide"]):
        return {
            "response": "I'm concerned about what you're sharing. Please reach out to someone you trust or contact a crisis helpline. You matter and support is available.",
            "session_id": session_id
        }
    
    # Get conversation context from recent messages
    conversation_context = ""
    try:
        if user_id and session_id:
            mongo = get_mongo()
            recent_msgs = mongo.get_session_messages(session_id=session_id, limit=6)
            if recent_msgs:
                context_parts = []
                for msg in recent_msgs[-6:]:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role and content:
                        context_parts.append(f"{role}: {content[:100]}")
                conversation_context = " | ".join(context_parts)
    except Exception:
        pass
    
    # Real AI chat response with conversation history
    chat_prompt = f"""The user is sharing their emotional state. Respond with empathy and understanding.
Keep under 50 words. Build on what they just said - don't repeat yourself.

User says: "{message}"

Your supportive response:"""
    
    response = await call_llm(chat_prompt, session_id=session_id, conversation_context=conversation_context)
    
    # naive mood index from keywords
    txt = message.lower()
    mood_index = 50
    pos = ["happy", "good", "great", "calm", "okay", "fine"]
    neg = ["sad", "bad", "angry", "upset", "stressed", "anxious", "pissed"]
    mood_index += 10 if any(w in txt for w in pos) else 0
    mood_index -= 10 if any(w in txt for w in neg) else 0
    mood_index = max(0, min(100, mood_index))

    # best-effort persistence
    try:
        if user_id and session_id:
            mongo = get_mongo()
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": message,
                "metadata": {"source": "chat", "mood_index": mood_index},
            })
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": response.strip(),
                "metadata": {"source": "chat", "mood_index": mood_index},
            })
    except Exception:
        pass

    return {
        "response": (response or "").strip(),
        "session_id": session_id
    }

@app.get("/ai/get-baseline-questions")
async def baseline_questions():
    return {
        "questions": [
            {"qid": "SA1", "facet": "self_awareness", "text": "I can recognize my emotions as they arise."},
            {"qid": "SR1", "facet": "self_regulation", "text": "I can stay calm under pressure."},
            {"qid": "M1", "facet": "motivation", "text": "I persist even when tasks are difficult."},
            {"qid": "E1", "facet": "empathy", "text": "I understand others' feelings."},
            {"qid": "SS1", "facet": "social_skills", "text": "I handle disagreements well."}
        ]
    }

@app.post("/ai/score-baseline")
async def score_baseline(request: Request) -> BaselineResponse:
    payload = await request.json()
    req = BaselineRequest(**payload)
    answers = req.answers
    avg = sum(a.value for a in answers) / len(answers) if answers else 3
    score = (avg - 1) / 4

    resp = BaselineResponse(
        scores=BaselineScores(
            self_awareness=round(score + 0.1, 2),
            self_regulation=round(score, 2),
            motivation=round(score + 0.05, 2),
            empathy=round(score + 0.15, 2),
            social_skills=round(score - 0.05, 2),
        ),
        strengths=["empathy"],
        focus=["self_regulation"],
        summary="Assessment completed successfully.",
    )
    return resp

@app.post("/ai/safety-check")
async def safety_check(request: Request) -> SafetyCheckResponse:
    payload = await request.json()
    req = SafetyCheckRequest(**payload)
    risk = classify_risk(req.text, llm=None)  # allow fallback without keys
    label = SafetyLabel(risk.get("label", "SAFE"))
    message = escalation_message() if label == SafetyLabel.ESCALATE else None
    return SafetyCheckResponse(label=label, message=message)

@app.post("/api/vision/analyze")
async def analyze_image(request: Request) -> ImageAnalysisResponse:
    """
    Analyze an image using vision AI.
    """
    _log = CustomLogger().get_logger(__name__)
    
    try:
        payload = await request.json()
    except Exception as e:
        _log.error("Invalid JSON body", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    try:
        req = ImageAnalysisRequest(**payload)
    except Exception as e:
        _log.error("Invalid request schema", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    try:
        # Basic validation for URL reachability if applicable
        if req.input_type == "url":
            try:
                import requests as _req
                r = _req.head(req.image_input, timeout=5, allow_redirects=True)
                if r.status_code >= 400:
                    raise HTTPException(status_code=400, detail="Image URL not reachable")
            except HTTPException:
                raise
            except Exception:
                # If HEAD fails, try GET small download to validate
                try:
                    r = _req.get(req.image_input, timeout=8, stream=True)
                    if r.status_code >= 400:
                        raise HTTPException(status_code=400, detail="Image URL not reachable")
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid or unreachable image URL")

        loader = ModelLoader()
        vision_provider = loader.load_vision_model(provider=req.provider)
        result = vision_provider.analyze(
            image_input=req.image_input,
            input_type=req.input_type,
            task=req.task
        )
        
        # Add timestamp to metadata
        from datetime import datetime
        result["metadata"]["timestamp"] = datetime.utcnow().isoformat()
        
        _log.info("Vision analysis completed", task=req.task, provider=req.provider, labels_count=len(result.get("labels", [])))
        return ImageAnalysisResponse(**result)
    
    except Exception as e:
        _log.error("Vision analysis failed", error=str(e), task=req.task, provider=req.provider)
        # Return fallback response
        return ImageAnalysisResponse(
            labels=["neutral"],
            confidence=[0.5],
            metadata={
                "fallback": True,
                "error": str(e),
                "provider": req.provider,
                "task": req.task
            }
        )

# RAG ENDPOINTS
@app.post("/rag/ingest")
async def rag_ingest(
    files: Optional[List[UploadFile]] = File(default=None),
    user_id: Optional[str] = Form(default=None),
    tags: Optional[List[str]] = Query(default=None),
    use_local: bool = Query(default=False),
    local_dir: str = Query(default="data/docs"),
):
    """
    Ingest one or more uploaded PDFs into the local FAISS vector store and
    record document metadata in MongoDB. Works in "offline" mode when
    embeddings/LLM keys are missing: metadata is saved with status="pending".

    Form fields:
      - files: one or more PDF files
      - user_id: optional user identifier
      - tags: optional repeated tag parameters (?tags=a&tags=b)
    """
    _log = CustomLogger().get_logger(__name__)
    buffers = []
    file_infos = []

    if files and len(files) > 0 and not use_local:
        # Client-uploaded files path
        for f in files:
            content = await f.read()
            if not content:
                continue
            bio = io.BytesIO(content)
            buffers.append(bio)
            file_infos.append({
                "filename": f.filename or "upload.pdf",
                "content_type": f.content_type or "application/pdf",
                "size": len(content),
                "path": None,
            })
    else:
        # Server-side folder ingestion (default)
        try:
            import glob, os
            pdf_paths = glob.glob(os.path.join(local_dir, "**", "*.pdf"), recursive=True)
            if not pdf_paths:
                _log.warning("No PDF files found in local_dir", local_dir=local_dir)
            for p in pdf_paths:
                try:
                    with open(p, "rb") as fh:
                        content = fh.read()
                    if not content:
                        continue
                    bio = io.BytesIO(content)
                    buffers.append(bio)
                    file_infos.append({
                        "filename": os.path.basename(p),
                        "content_type": "application/pdf",
                        "size": len(content),
                        "path": p,
                    })
                except Exception as fe:
                    _log.error("Failed reading local file", path=p, error=str(fe))
        except Exception as e:
            _log.error("Failed to scan local_dir", local_dir=local_dir, error=str(e))

    if not buffers:
        raise HTTPException(status_code=400, detail="No documents found to ingest")

    mongo = get_mongo()

    # Attempt ingestion; fall back to metadata-only if it fails
    vector_dir = "rag/vectorstore"
    data_dir = "rag/uploads"
    indexed = False
    offline = False
    try:
        ingestor = SingleDocumentIngestor(data_dir=data_dir, faiss_dir=vector_dir)

        # SingleDocumentIngestor expects objects with getbuffer(); BytesIO works
        ingestor.ingest_files(buffers)
        indexed = True
    except Exception as e:
        # Offline fallback: continue to save metadata only
        offline = True
        _log.warning("RAG ingestion failed; saving metadata only", error=str(e))

    # Save document metadata per file
    docs_resp = []
    tag_list = tags or []
    for info in file_infos:
        doc_id = uuid.uuid4().hex
        try:
            mongo.add_document({
                "doc_id": doc_id,
                "user_id": user_id or "system",
                "filename": info["filename"],
                "content_type": info["content_type"],
                "size": info["size"],
                "faiss_path": vector_dir,
                "status": "indexed" if indexed else "pending",
                "chunk_count": 0,
                "metadata": {"tags": tag_list, "path": info.get("path")},
            })
        except Exception as e:
            _log.error("Failed to save document metadata", error=str(e))
            # don't fail the whole request; continue
        docs_resp.append({
            "doc_id": doc_id,
            "filename": info["filename"],
            "size": info["size"],
            "status": "indexed" if indexed else "pending",
        })

    return {
        "documents": docs_resp,
        "vectorstore_dir": vector_dir,
        "indexed": indexed,
        "offline": offline,
    }

@app.get("/rag/status")
async def rag_status():
    vector_dir = "rag/vectorstore"
    index_faiss = os.path.join(vector_dir, "index.faiss")
    retriever_ready = os.path.isdir(vector_dir) and os.path.exists(index_faiss)
    return {"retriever_ready": retriever_ready, "vectorstore_dir": vector_dir}

@app.get("/rag/documents")
async def rag_documents(user_id: Optional[str] = None, limit: int = 50):
    try:
        mongo = get_mongo()
        if user_id:
            docs = mongo.list_documents(user_id=user_id, limit=limit)
        else:
            # simple admin listing: last N docs regardless of user
            docs = list(mongo.documents.find({}, {"_id": 0}).sort("uploaded_at", -1).limit(limit))
        return {"documents": docs}
    except Exception as e:
        _LOG.error("rag_documents failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list documents")

@app.post("/ai/get-exercise")
async def get_exercise(request: Request):
    data = await request.json()
    target_facets = data.get("target_facets", [])
    
    # Real AI exercise generation
    exercise_prompt = f"""
    Create a personalized emotional intelligence exercise. Respond in JSON format:
    {{
        "exercise_id": "unique_id",
        "title": "Exercise Name",
        "steps": ["step 1", "step 2", "step 3"],
        "expected_outcome": "what user will gain",
        "followup_question": "question to ask after"
    }}
    
    Target areas: {target_facets}
    Make it practical and doable in 2-5 minutes.
    """
    
    ai_response = await call_llm(exercise_prompt, session_id="exercise")
    
    try:
        start = ai_response.find('{')
        end = ai_response.rfind('}') + 1
        if start != -1 and end > start:
            exercise_data = json.loads(ai_response[start:end])
        else:
            raise ValueError("No JSON found")
    except:
        exercise_data = {
            "exercise_id": "breathing",
            "title": "Mindful Breathing",
            "steps": ["Sit comfortably", "Breathe in for 4", "Hold for 4", "Breathe out for 4", "Repeat 5 times"],
            "expected_outcome": "Increased calm and focus",
            "followup_question": "How do you feel now?"
        }
    
    exercise_data["source_doc_id"] = "ai_generated"
    return {"exercise": exercise_data}

# ==================== AGENTIC RAG QUERY ====================

@app.post("/rag/exercise")
async def rag_exercise(request: Request):
    """
    Agentic RAG endpoint: retrieves relevant chunks from FAISS and synthesizes
    a short, actionable exercise targeting given facets/context. Persists
    user/assistant messages when session_id and user_id are provided.

    Request JSON:
      {
        "user_id": "u1",                # optional but used for persistence
        "session_id": "s1",             # optional but used for persistence
        "query": "how to calm down",     # optional; constructed from facets/tags if absent
        "target_facets": ["self_awareness"],
        "context_tags": ["work", "stress"],
        "duration_hint": "3 minutes"
      }
    """
    payload = await request.json()
    user_id = payload.get("user_id")
    session_id = payload.get("session_id")
    target_facets = payload.get("target_facets", [])
    context_tags = payload.get("context_tags", [])
    duration_hint = payload.get("duration_hint", "3 minutes")
    query = payload.get("query")

    retriever_ready = False
    offline = False
    chunks: List[str] = []

    # Try to load retriever; tolerate missing keys/indices
    try:
        rag = ConversationalRAG(faiss_dir="rag/vectorstore")
        try:
            retriever = rag.load_retriever_from_faiss()
            retriever_ready = True
        except Exception:
            offline = True
            retriever = None
    except Exception:
        offline = True
        retriever = None

    if not query:
        query_parts = target_facets + context_tags + [duration_hint, "exercise"]
        query = " ".join([p for p in query_parts if p]) or "emotional intelligence exercise"

    if retriever_ready and retriever is not None:
        try:
            chunks = rag.search(retriever, query, k=5)
        except Exception:
            offline = True
            chunks = []

    # Synthesize exercise (LLM-backed if available; otherwise fallback)
    exercise = rag.synthesize_exercise(chunks, target_facets, context_tags, duration_hint)
    exercise = prepare_recommendation(exercise)

    # Persist messages if context provided
    try:
        if user_id and session_id:
            mongo = get_mongo()
            # user message
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": query,
                "metadata": {
                    "source": "rag",
                    "target_facets": target_facets,
                    "context_tags": context_tags,
                    "duration_hint": duration_hint,
                },
            })
            # assistant reply (summary)
            summary = f"{exercise.get('title', 'Exercise')} — first steps: "
            steps = exercise.get("steps", [])
            if isinstance(steps, list) and steps:
                preview = "; ".join(steps[:3])
                summary += preview
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": summary,
                "metadata": {
                    "source": "rag",
                    "chunks_found": len(chunks),
                    "retriever_ready": retriever_ready,
                },
            })
    except Exception:
        # best-effort persistence only
        pass

    return {
        "exercise": exercise,
        "chunks": chunks,
        "retriever_ready": retriever_ready,
        "offline": offline,
    }


# ==================== AGENTIC WEB-AUGMENTED RAG ====================

@app.post("/agent/exercise")
async def agent_exercise(request: Request):
    """
    Agentic workflow: prefer local FAISS retriever; if insufficient context
    is found, augment with web search snippets and synthesize a practical
    EI exercise. Best-effort persistence of messages.

    Request JSON:
      {
        "user_id": "u1", "session_id": "s1",
        "query": "how to handle conflict kindly",
        "target_facets": ["social_skills"],
        "context_tags": ["work"],
        "duration_hint": "3 minutes"
      }
    """
    payload = await request.json()
    user_id = payload.get("user_id")
    session_id = payload.get("session_id")
    target_facets = payload.get("target_facets", [])
    context_tags = payload.get("context_tags", [])
    duration_hint = payload.get("duration_hint", "3 minutes")
    query = payload.get("query")

    offline = False
    retriever_ready = False
    chunks: List[str] = []
    web_used = False

    # Load RAG retriever (tolerant of missing embeddings)
    try:
        rag = ConversationalRAG(faiss_dir="rag/vectorstore")
        try:
            retriever = rag.load_retriever_from_faiss()
            retriever_ready = True
        except Exception:
            retriever = None
            offline = True
    except Exception:
        retriever = None
        offline = True

    if not query:
        query_parts = target_facets + context_tags + [duration_hint, "exercise"]
        query = " ".join([p for p in query_parts if p]) or "emotional intelligence exercise"

    # Try local chunks first
    if retriever_ready and retriever is not None:
        try:
            chunks = rag.search(retriever, query, k=5)
        except Exception:
            chunks = []

    # If no or few chunks, augment with web search
    if len(chunks) < 2:
        ws = WebSearch()
        results = ws.search(query, max_results=5)
        if results:
            web_used = True
            # turn results into chunk-like texts
            for r in results:
                text = f"{r.get('title','')}\n{r.get('url','')}\n{r.get('content','')}"
                chunks.append(text)

    # Synthesize exercise from chunks
    exercise = rag.synthesize_exercise(chunks, target_facets, context_tags, duration_hint)
    exercise = prepare_recommendation(exercise)

    # Persist messages (best-effort)
    try:
        if user_id and session_id:
            mongo = get_mongo()
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "user",
                "content": query,
                "metadata": {
                    "source": "agent",
                    "target_facets": target_facets,
                    "context_tags": context_tags,
                    "duration_hint": duration_hint,
                },
            })
            # assistant
            mongo.add_message({
                "session_id": session_id,
                "user_id": user_id,
                "role": "assistant",
                "content": exercise.get("title", "Exercise"),
                "metadata": {
                    "source": "agent",
                    "chunks_used": len(chunks),
                    "web_used": web_used,
                },
            })
    except Exception:
        pass

    return {
        "exercise": exercise,
        "chunks": chunks[:5],
        "web_used": web_used,
        "retriever_ready": retriever_ready,
        "offline": offline,
    }

# ==================== SESSIONS & MESSAGES API ====================

_LOG = CustomLogger().get_logger(__name__)

@app.get("/api/sessions")
async def list_sessions(user_id: Optional[str] = None, limit: int = 50):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        mongo = get_mongo()
        sessions = mongo.list_sessions(user_id=user_id, limit=limit)
        return {"sessions": sessions}
    except Exception as e:
        _LOG.error("list_sessions failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list sessions")

@app.post("/api/sessions")
async def create_session(request: Request):
    payload = await request.json()
    user_id = payload.get("user_id")
    name = payload.get("name", "New Session")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        mongo = get_mongo()
        session_id = payload.get("session_id") or uuid.uuid4().hex
        mongo.create_session({
            "session_id": session_id,
            "user_id": user_id,
            "name": name,
        })
        return {"session_id": session_id, "name": name}
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        _LOG.error("create_session failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.patch("/api/sessions/{session_id}")
async def update_session(session_id: str, request: Request):
    updates = await request.json()
    try:
        mongo = get_mongo()
        ok = mongo.update_session(session_id, updates)
        if not ok:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        _LOG.error("update_session failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to update session")

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    try:
        mongo = get_mongo()
        ok = mongo.delete_session(session_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        _LOG.error("delete_session failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete session")

@app.post("/api/messages")
async def add_message(request: Request):
    payload = await request.json()
    required = ["session_id", "user_id", "role", "content"]
    if any(k not in payload for k in required):
        raise HTTPException(status_code=400, detail=f"Missing fields; required: {required}")
    try:
        mongo = get_mongo()
        message_id = mongo.add_message({
            "session_id": payload["session_id"],
            "user_id": payload["user_id"],
            "role": payload["role"],
            "content": payload["content"],
            "metadata": payload.get("metadata", {}),
        })
        return {"message_id": message_id}
    except Exception as e:
        _LOG.error("add_message failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to add message")

@app.get("/api/messages")
async def get_messages(session_id: Optional[str] = None, limit: int = 100):
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        mongo = get_mongo()
        messages = mongo.get_session_messages(session_id=session_id, limit=limit)
        return {"messages": messages}
    except Exception as e:
        _LOG.error("get_messages failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get messages")

@app.get("/analytics/series")
async def analytics_series(user_id: Optional[str] = None, days: int = 30):
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        mongo = get_mongo()
        series = mongo.get_mood_series(user_id=user_id, days=days)
        return {"series": series}
    except Exception as e:
        _LOG.error("analytics_series failed", error=str(e))
        return {"series": [], "offline": True}

# ==================== TTS/STT ENDPOINTS ====================

@app.post("/api/tts")
async def text_to_speech(request: Request):
    """
    Convert text to speech audio.
    
    Request body:
        {
            "text": "Text to convert to speech",
            "voice_id": "21m00Tcm4TlvDq8ikWAM"  // optional
        }
    
    Returns:
        Audio bytes (MP3 format) or mock audio if ELEVENLABS_API_KEY not set
    """
    data = await request.json()
    text = data.get("text", "")
    voice_id = data.get("voice_id", "21m00Tcm4TlvDq8ikWAM")
    
    if not text:
        return {"error": "Text is required"}
    
    client = get_elevenlabs()
    audio_bytes = client.text_to_speech(text, voice_id=voice_id)
    media_type = "audio/mpeg" if getattr(client, "enabled", False) else "audio/wav"
    filename = "speech.mp3" if media_type == "audio/mpeg" else "speech.wav"
    
    # Return audio as streaming response
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@app.post("/api/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Transcribe audio to text.
    
    Upload an audio file (WAV, MP3, etc.)
    
    Returns:
        {
            "transcript": "Transcribed text",
            "confidence": 0.95
        }
    """
    # Read audio file
    audio_bytes = await file.read()
    
    if not audio_bytes:
        return {"error": "Audio file is required"}
    
    client = get_elevenlabs()
    result = client.speech_to_text(audio_bytes)
    
    return result

@app.get("/api/voices")
async def list_voices():
    """
    List available TTS voices.
    
    Returns:
        List of voice objects with id, name, category, description
    """
    client = get_elevenlabs()
    voices = client.list_voices()
    return {"voices": voices}


# ==================== ADAPTIVE CHAT WITH ORCHESTRATOR ====================

# Initialize orchestrator
orchestrator = Orchestrator()

@app.post("/api/chat/{session_id}")
async def adaptive_chat(session_id: str, request: Request):
    """
    Adaptive chat endpoint with multi-agent orchestration.
    Modes: qa (default), reflection, weekly
    """
    payload = await request.json()
    message = payload.get("message", "")
    user_id = payload.get("user_id")
    mode = payload.get("mode", "qa")
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    try:
        # Initialize memory
        memory = MemoryManager(session_id=session_id, user_id=user_id)
        memory.initialize()
        
        # Orchestrate response
        result = orchestrator.process_message(
            message=message,
            session_id=session_id,
            user_id=user_id,
            mode=mode
        )
        
        # Save to memory
        memory.save_interaction(
            user_message=message,
            assistant_reply=result.get("text", ""),
            tags=[mode]
        )
        
        # Optional TTS
        audio_url = None
        if payload.get("generate_audio"):
            try:
                tts_client = get_elevenlabs()
                audio_bytes = tts_client.text_to_speech(result["text"])
                # In production, upload to S3 and return URL
                audio_url = "data:audio/mp3;base64,..."  # stub
            except Exception:
                pass
        
        # Best-effort persistence with mood_index metadata (to power analytics)
        try:
            mongo = get_mongo()
            # derive mood_index: prefer sentiment (-1..1), else keyword heuristic
            sentiment_val = result.get("sentiment")
            if isinstance(sentiment_val, (int, float)):
                mood_index = max(0.0, min(100.0, ((float(sentiment_val) + 1.0) / 2.0) * 100.0))
            else:
                txt = (message or "").lower()
                mood_index = 50
                pos = ["happy", "good", "great", "calm", "okay", "fine"]
                neg = ["sad", "bad", "angry", "upset", "stressed", "anxious", "pissed"]
                mood_index += 10 if any(w in txt for w in pos) else 0
                mood_index -= 10 if any(w in txt for w in neg) else 0
                mood_index = max(0, min(100, mood_index))

            if user_id and session_id:
                mongo.add_message({
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": message,
                    "metadata": {"source": "agentic_chat", "mood_index": mood_index},
                })
                mongo.add_message({
                    "session_id": session_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": result.get("text", ""),
                    "metadata": {"source": "agentic_chat", "mood_index": mood_index},
                })
        except Exception:
            pass

        return {
            "text": result.get("text"),
            "citations": result.get("citations", []),
            "tasks": result.get("tasks", []),
            "why": result.get("why"),
            "audio_url": audio_url,
            "sentiment": result.get("sentiment"),
            "crisis_check": result.get("crisis_check")
        }
        
    except Exception as e:
        _LOG.error("Adaptive chat failed", error=str(e))
        raise HTTPException(status_code=500, detail="Chat processing failed")


@app.post("/api/ingest")
async def api_ingest(request: Request):
    """
    Ingest from URLs, files, YouTube.
    Request: {urls?: list, files?: list, youtube_ids?: list, user_id?: str}
    """
    payload = await request.json()
    urls = payload.get("urls", [])
    youtube_ids = payload.get("youtube_ids", [])
    user_id = payload.get("user_id", "system")
    
    try:
        result = orchestrator.data_agent.ingest(
            urls=urls,
            youtube_ids=youtube_ids,
            user_id=user_id
        )
        return result
    except Exception as e:
        _LOG.error("Ingest failed", error=str(e))
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.get("/api/analytics/mood_timeline")
async def mood_timeline(session_id: Optional[str] = None, user_id: Optional[str] = None, days: int = 30):
    """Get mood timeline for analytics dashboard."""
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    
    try:
        mongo = get_mongo()
        series = mongo.get_mood_series(user_id=user_id, days=days)
        return {"timeline": series}
    except Exception as e:
        _LOG.error("Mood timeline failed", error=str(e))
        return {"timeline": [], "offline": True}


@app.post("/api/weekly-review")
async def weekly_review_endpoint(request: Request):
    """
    Generate weekly review summary.
    Request: {session_id: str, user_id: str}
    """
    payload = await request.json()
    session_id = payload.get("session_id")
    user_id = payload.get("user_id")
    
    if not session_id or not user_id:
        raise HTTPException(status_code=400, detail="session_id and user_id required")
    
    try:
        result = orchestrator.insight_agent.weekly_review(session_id=session_id)
        return result
    except Exception as e:
        _LOG.error("Weekly review failed", error=str(e))
        raise HTTPException(status_code=500, detail="Weekly review failed")


@app.post("/api/safety/event")
async def create_crisis_event(request: Request):
    """
    Persist a new crisis event (risk detection) to MongoDB.
    """
    try:
        payload = await request.json()
        event = CrisisEvent(**payload)
        mongo = get_mongo()
        event_data = event.dict()
        event_id = mongo.add_crisis_event(event_data)
        return {"event_id": event_id}
    except Exception as e:
        _LOG = CustomLogger().get_logger(__name__)
        _LOG.error("create_crisis_event failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to persist crisis event")

@app.get("/api/safety/events")
async def list_crisis_events(user_id: Optional[str] = None, status: Optional[str] = None, risk_band: Optional[str] = None, limit: int = 50):
    """
    List crisis events, optionally filtered by user_id, status, and/or risk_band.
    """
    try:
        mongo = get_mongo()
        events = mongo.list_crisis_events(user_id=user_id, status=status, risk_band=risk_band, limit=limit)
        return {"events": events}
    except Exception as e:
        _LOG = CustomLogger().get_logger(__name__)
        _LOG.error("list_crisis_events failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list crisis events")

@app.post("/api/alerts/test")
async def test_alert(request: Request):
    """Test alert dispatch (admin only in production)."""
    payload = await request.json()
    user_id = payload.get("user_id", "test_user")
    text = payload.get("text", "Test alert")
    
    try:
        crisis_agent = orchestrator.crisis_agent
        result = crisis_agent.evaluate(
            session_id="test",
            user_id=user_id,
            latest_score=3.0,
            text=text
        )
        return result
    except Exception as e:
        _LOG.error("Alert test failed", error=str(e))
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)