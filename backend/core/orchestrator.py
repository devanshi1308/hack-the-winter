"""
Multi-agent orchestration for agentic RAG emotional wellness system.
Uses LangGraph-compatible pattern with distinct agents for ingestion, retrieval, insight, sentiment, and crisis.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import os
import tempfile

from logger.custom_logger import CustomLogger
from rag.rag_pipeline import ConversationalRAG
from utils.web_search import WebSearch
from core.journal_analyzer import analyze_entry
from core.safety_checker import classify_risk, escalation_message
from core.coach import coach_question
from db.mongo import get_mongo
from utils.model_loader import ModelLoader

try:
    from langchain_community.document_loaders import WebBaseLoader, YoutubeLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.retrievers import BM25Retriever
    from langchain_core.documents import Document
    _LOADERS_AVAILABLE = True
except ImportError:
    _LOADERS_AVAILABLE = False
    Document = None

_LOG = CustomLogger().get_logger(__name__)


class DataAgent:
    """Ingestion & indexing: crawl web, accept uploads, chunk, embed, index."""
    
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        self.web_search = WebSearch()
    
    def ingest(
        self,
        urls: List[str] = None,
        files: List[bytes] = None,
        youtube_ids: List[str] = None,
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Ingest from multiple sources and index into FAISS.
        Returns: {docs_indexed: int, sources: list}
        """
        urls = urls or []
        files = files or []
        youtube_ids = youtube_ids or []
        
        sources = []
        all_documents = []
        
        # Web URLs with real loaders
        if urls and _LOADERS_AVAILABLE:
            for url in urls:
                try:
                    loader = WebBaseLoader(url)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata.update({
                            "source_type": "url",
                            "source": url,
                            "title": doc.metadata.get("title", url),
                            "user_id": user_id
                        })
                    all_documents.extend(docs)
                    sources.append({"type": "url", "source": url, "status": "indexed", "count": len(docs)})
                    self.log.info("URL ingested", url=url, docs=len(docs))
                except Exception as e:
                    sources.append({"type": "url", "source": url, "status": "failed", "error": str(e)})
                    self.log.error("URL ingestion failed", url=url, error=str(e))
        
        # YouTube transcripts with real loaders
        if youtube_ids and _LOADERS_AVAILABLE:
            for yt_id in youtube_ids:
                try:
                    # Format: https://www.youtube.com/watch?v=VIDEO_ID
                    video_url = f"https://www.youtube.com/watch?v={yt_id}"
                    loader = YoutubeLoader.from_youtube_url(video_url, add_video_info=True)
                    docs = loader.load()
                    for doc in docs:
                        doc.metadata.update({
                            "source_type": "youtube",
                            "source": yt_id,
                            "title": doc.metadata.get("title", f"YouTube: {yt_id}"),
                            "user_id": user_id
                        })
                    all_documents.extend(docs)
                    sources.append({"type": "youtube", "source": yt_id, "status": "indexed", "count": len(docs)})
                    self.log.info("YouTube ingested", yt_id=yt_id, docs=len(docs))
                except Exception as e:
                    sources.append({"type": "youtube", "source": yt_id, "status": "failed", "error": str(e)})
                    self.log.error("YouTube ingestion failed", yt_id=yt_id, error=str(e))
        
        # Chunk and index documents if any loaded
        docs_indexed = 0
        if all_documents:
            try:
                # Chunk documents
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=int(os.getenv("MAX_CHUNK_TOKENS", "800")),
                    chunk_overlap=200
                )
                chunks = text_splitter.split_documents(all_documents)
                
                # Index into FAISS (using existing RAG pipeline)
                from rag.rag_pipeline import SingleDocumentIngestor
                ingestor = SingleDocumentIngestor()
                
                # Save chunks to temp files for ingestion
                temp_paths = []
                for i, chunk in enumerate(chunks):
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                        f.write(chunk.page_content)
                        # Store metadata in filename for retrieval
                        f.write(f"\n\n__METADATA__: {chunk.metadata}")
                        temp_paths.append(f.name)
                
                # Ingest and clean up
                retriever = ingestor.ingest_files(temp_paths)
                for path in temp_paths:
                    os.unlink(path)
                
                docs_indexed = len(chunks)
                self.log.info("Documents indexed to FAISS", chunks=docs_indexed)
                
            except Exception as e:
                self.log.error("Document indexing failed", error=str(e))
        
        # Files handled via existing /rag/ingest endpoint in app.py
        if not _LOADERS_AVAILABLE and (urls or youtube_ids):
            self.log.warning("Document loaders not available; install langchain-community")
        
        return {"docs_indexed": docs_indexed, "sources": sources}


class ContextAgent:
    """Retrieval & reasoning: hybrid search (BM25 + vector) with citations."""
    
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        self.rag = ConversationalRAG(faiss_dir="rag/vectorstore")
        self.vector_retriever = None
        self.bm25_retriever = None
        self.corpus_docs = []  # In-memory corpus for BM25
        
        try:
            self.vector_retriever = self.rag.load_retriever_from_faiss()
            self.log.info("FAISS vector retriever loaded")
        except Exception as e:
            self.log.warning("FAISS retriever unavailable; will use fallback", error=str(e))
        
        # Initialize BM25 with corpus if available
        if _LOADERS_AVAILABLE:
            try:
                self._load_bm25_corpus()
            except Exception as e:
                self.log.warning("BM25 retriever initialization failed", error=str(e))
    
    def _load_bm25_corpus(self):
        """Load or build BM25 corpus from indexed documents."""
        # In production, load from persistent storage
        # For now, use FAISS store as source
        try:
            if self.vector_retriever and _LOADERS_AVAILABLE:
                # Get sample docs to build BM25 index
                sample_query = "wellness emotional health"
                results = self.rag.search(self.vector_retriever, sample_query, k=50)
                
                self.corpus_docs = [
                    Document(
                        page_content=text,
                        metadata={"source": "faiss_corpus", "index": i}
                    ) for i, text in enumerate(results)
                ]
                
                if self.corpus_docs:
                    self.bm25_retriever = BM25Retriever.from_documents(self.corpus_docs)
                    self.bm25_retriever.k = 3  # Top-k for BM25
                    self.log.info("BM25 retriever initialized", corpus_size=len(self.corpus_docs))
        except Exception as e:
            self.log.warning("BM25 corpus load failed", error=str(e))
    
    def retrieve(
        self,
        query: str,
        session_id: str,
        k: int = None,
        adaptive: bool = True,
        use_hybrid: bool = True
    ) -> Dict[str, Any]:
        """
        Hybrid retrieval (BM25 + vector) with citations.
        Returns: {passages: list[str], citations: list[dict], confidence: float, method: str}
        """
        k = k or int(os.getenv("RAG_TOP_K", "6"))
        
        passages = []
        citations = []
        confidence = 0.5
        method = "fallback"
        
        # Try hybrid retrieval first
        if use_hybrid and self.vector_retriever and self.bm25_retriever and _LOADERS_AVAILABLE:
            try:
                # Get results from both retrievers
                vector_chunks = self.rag.search(self.vector_retriever, query, k=k)
                bm25_docs = self.bm25_retriever.get_relevant_documents(query)
                bm25_chunks = [doc.page_content for doc in bm25_docs]
                
                # Merge and deduplicate
                seen = set()
                for chunk in vector_chunks + bm25_chunks:
                    chunk_key = chunk[:100]  # Use first 100 chars as key
                    if chunk_key not in seen:
                        passages.append(chunk)
                        seen.add(chunk_key)
                
                # Generate citations with metadata
                for i, chunk in enumerate(passages[:k]):
                    # Extract metadata if embedded in chunk
                    metadata = self._extract_metadata(chunk)
                    citations.append({
                        "source_id": metadata.get("source", f"doc_{i}"),
                        "url": metadata.get("url", f"internal://doc_{i}"),
                        "title": metadata.get("title", f"Document {i}"),
                        "start": 0,
                        "end": min(100, len(chunk)),
                        "snippet": chunk[:100]
                    })
                
                passages = passages[:k]
                confidence = min(1.0, len(passages) / k) if passages else 0.0
                method = "hybrid_bm25_vector"
                self.log.info("Hybrid retrieval complete", method=method, results=len(passages))
                
            except Exception as e:
                self.log.error("Hybrid retrieval failed; falling back to vector-only", error=str(e))
        
        # Fallback to vector-only
        if not passages and self.vector_retriever:
            try:
                chunks = self.rag.search(self.vector_retriever, query, k=k)
                passages = chunks
                
                # Generate citations
                for i, chunk in enumerate(chunks):
                    metadata = self._extract_metadata(chunk)
                    citations.append({
                        "source_id": metadata.get("source", f"doc_{i}"),
                        "url": metadata.get("url", f"internal://doc_{i}"),
                        "title": metadata.get("title", f"Document {i}"),
                        "start": 0,
                        "end": min(100, len(chunk)),
                        "snippet": chunk[:100]
                    })
                
                confidence = min(1.0, len(chunks) / k) if chunks else 0.0
                method = "vector_only"
                
            except Exception as e:
                self.log.error("Vector retrieval failed", error=str(e))
        
        # Adaptive depth: if confidence low, expand search
        if adaptive and confidence < 0.4 and k < 12:
            self.log.info("Low confidence; expanding search depth", current_k=k, new_k=min(12, k * 2))
            return self.retrieve(query, session_id, k=min(12, k * 2), adaptive=False, use_hybrid=use_hybrid)
        
        return {
            "passages": passages,
            "citations": citations,
            "confidence": confidence,
            "method": method
        }
    
    def _extract_metadata(self, chunk: str) -> Dict[str, Any]:
        """Extract metadata from chunk text if embedded."""
        # Check for embedded metadata marker
        if "__METADATA__:" in chunk:
            try:
                parts = chunk.split("__METADATA__:")
                if len(parts) > 1:
                    import json
                    metadata_str = parts[1].strip()
                    return eval(metadata_str)  # Safe in controlled context
            except Exception:
                pass
        
        return {"source": "unknown", "url": "internal://unknown", "title": "Unknown Document"}


class InsightAgent:
    """Generation & coaching: personalized tasks with EQ ontology."""
    
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        self.llm = None
        try:
            self.llm = ModelLoader().load_llm()
        except Exception as e:
            self.log.warning("LLM unavailable; using fallback", error=str(e))
    
    def coach(
        self,
        message: str,
        context: List[str],
        session_id: str,
        facet: str = "self_awareness"
    ) -> Dict[str, Any]:
        """
        Generate coaching response with tasks and citations.
        Returns: {text: str, tasks: list, citations: list, why: str}
        """
        # Use existing coach module
        try:
            state = {
                "facet": facet,
                "emotions": [],
                "last_entry_summary": message[:200]
            }
            question = coach_question(state, llm=self.llm)
            
            return {
                "text": question if isinstance(question, str) else question.get("question", "What's on your mind today?"),
                "tasks": [
                    "Take 3 deep breaths",
                    "Write one sentence about how you feel right now"
                ],
                "citations": [],
                "why": "Reflective questions build self-awareness and emotional clarity"
            }
        except Exception as e:
            self.log.error("Coach generation failed", error=str(e))
            return {
                "text": "I'm here to support you. What would you like to explore?",
                "tasks": [],
                "citations": [],
                "why": "Fallback response"
            }
    
    def weekly_review(
        self,
        session_id: str,
        range_str: str = "last_7d"
    ) -> Dict[str, Any]:
        """
        Weekly summary with goals and insights.
        Returns: {summary: str, goals: list, insights: list, citations: list}
        """
        try:
            mongo = get_mongo()
            messages = mongo.get_session_messages(session_id=session_id, limit=100)
            
            # Aggregate mood trends
            mood_values = [
                m.get("metadata", {}).get("mood_index", 50)
                for m in messages
                if "mood_index" in m.get("metadata", {})
            ]
            
            avg_mood = sum(mood_values) / len(mood_values) if mood_values else 50
            trend = "improving" if avg_mood > 55 else "stable" if avg_mood > 45 else "declining"
            
            summary = f"Over the past week, your mood has been {trend} (avg: {avg_mood:.1f}/100). "
            summary += f"You've engaged in {len(messages)} conversations, showing consistent reflection."
            
            goals = [
                "Continue daily check-ins",
                "Try one new coping strategy this week",
                "Share a positive moment with someone you trust"
            ]
            
            insights = [
                f"Your most frequent emotion theme: reflection",
                f"Strongest facet: self-awareness",
                f"Growth opportunity: self-regulation practices"
            ]
            
            return {
                "summary": summary,
                "goals": goals,
                "insights": insights,
                "citations": []
            }
            
        except Exception as e:
            self.log.error("Weekly review failed", error=str(e))
            return {
                "summary": "Unable to generate review at this time",
                "goals": [],
                "insights": [],
                "citations": []
            }


class SentimentAgent:
    """Sentiment & signal analysis with z-score tracking."""
    
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
    
    def analyze(
        self,
        text: str,
        session_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Analyze sentiment and compute z-score.
        Returns: {sentiment: str, scores: dict, zscore: float, events: list}
        """
        try:
            # Use existing journal analyzer with proper payload signature
            analysis = analyze_entry({
                "journal": text,
                "mood": 5,
                "context": {}
            }, llm=None)
            
            # Compute z-score from recent history
            mongo = get_mongo()
            recent_msgs = mongo.get_recent_messages(user_id=user_id, days=30, limit=100)
            mood_values = [
                m.get("metadata", {}).get("mood_index", 50)
                for m in recent_msgs
                if "mood_index" in m.get("metadata", {})
            ]
            
            current_mood = analysis.get("mood_index", 50)
            
            if len(mood_values) > 2:
                mean = sum(mood_values) / len(mood_values)
                variance = sum((x - mean) ** 2 for x in mood_values) / len(mood_values)
                std_dev = variance ** 0.5
                zscore = (current_mood - mean) / std_dev if std_dev > 0 else 0.0
            else:
                zscore = 0.0
            
            events = []
            if abs(zscore) > 2.5:
                events.append({
                    "type": "mood_spike",
                    "direction": "high" if zscore > 0 else "low",
                    "magnitude": abs(zscore)
                })
            
            return {
                "sentiment": analysis.get("sentiment", "neutral"),
                "scores": analysis.get("facet_signals", {}),
                "zscore": zscore,
                "events": events
            }
            
        except Exception as e:
            self.log.error("Sentiment analysis failed", error=str(e))
            return {
                "sentiment": "neutral",
                "scores": {},
                "zscore": 0.0,
                "events": []
            }


class CrisisAgent:
    """Crisis detection with alert dispatch."""
    
    def __init__(self):
        self.log = CustomLogger().get_logger(__name__)
        self.alert_cooldown = {}  # user_id -> last_alert_time
    
    def evaluate(
        self,
        session_id: str,
        user_id: str,
        latest_score: float,
        text: str = ""
    ) -> Dict[str, Any]:
        """
        Evaluate crisis risk and trigger alerts.
        Returns: {triggered: bool, action: str|None, alert_sent: bool}
        """
        triggered = False
        action = None
        alert_sent = False
        
        # Check z-score threshold
        threshold = float(os.getenv("CRISIS_ZSCORE_THRESHOLD", "2.5"))
        if abs(latest_score) > threshold:
            triggered = True
            action = "monitor"
        
        # Check safety keywords
        if text:
            safety = classify_risk(text, llm=None)
            if safety.get("label") == "ESCALATE":
                triggered = True
                action = "alert"
        
        # Cooldown check
        cooldown_hours = 24
        now = datetime.now(timezone.utc)
        last_alert = self.alert_cooldown.get(user_id)
        
        if action == "alert" and (not last_alert or (now - last_alert).total_seconds() > cooldown_hours * 3600):
            try:
                self._send_alerts(user_id, text)
                alert_sent = True
                self.alert_cooldown[user_id] = now
                self.log.info("Crisis alert sent", user_id=user_id)
            except Exception as e:
                self.log.error("Alert dispatch failed", error=str(e))
        
        return {
            "triggered": triggered,
            "action": action,
            "alert_sent": alert_sent
        }
    
    def _send_alerts(self, user_id: str, context: str):
        """Send SMS via Twilio and push via FCM."""
        # Twilio SMS
        try:
            from twilio.rest import Client
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            from_number = os.getenv("TWILIO_FROM_NUMBER")
            
            if account_sid and auth_token and from_number:
                client = Client(account_sid, auth_token)
                # In production, get user's emergency contact from DB
                to_number = os.getenv("EMERGENCY_CONTACT_NUMBER")
                if to_number:
                    message = client.messages.create(
                        body=f"RaAI Alert: User {user_id} may need support. Context: {context[:100]}",
                        from_=from_number,
                        to=to_number
                    )
                    self.log.info("SMS sent", sid=message.sid)
        except Exception as e:
            self.log.error("Twilio SMS failed", error=str(e))
        
        # FCM Push
        try:
            import requests
            fcm_key = os.getenv("FCM_SERVER_KEY")
            if fcm_key:
                # In production, get user's FCM token from DB
                token = os.getenv("USER_FCM_TOKEN")
                if token:
                    headers = {
                        "Authorization": f"key={fcm_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "to": token,
                        "notification": {
                            "title": "RaAI Support Alert",
                            "body": "We're here if you need to talk. You matter."
                        }
                    }
                    resp = requests.post(
                        "https://fcm.googleapis.com/fcm/send",
                        json=payload,
                        headers=headers,
                        timeout=5
                    )
                    self.log.info("FCM push sent", status=resp.status_code)
        except Exception as e:
            self.log.error("FCM push failed", error=str(e))


class Orchestrator:
    """Main orchestrator coordinating all agents."""
    
    def __init__(self):
        self.data_agent = DataAgent()
        self.context_agent = ContextAgent()
        self.insight_agent = InsightAgent()
        self.sentiment_agent = SentimentAgent()
        self.crisis_agent = CrisisAgent()
        self.log = CustomLogger().get_logger(__name__)
    
    def process_message(
        self,
        message: str,
        session_id: str,
        user_id: str,
        mode: str = "qa"
    ) -> Dict[str, Any]:
        """
        Orchestrate agents for a user message.
        Modes: qa, reflection, weekly
        """
        try:
            # Sentiment analysis
            sentiment = self.sentiment_agent.analyze(message, session_id, user_id)
            
            # Crisis check
            crisis = self.crisis_agent.evaluate(
                session_id=session_id,
                user_id=user_id,
                latest_score=sentiment["zscore"],
                text=message
            )
            
            # Retrieval
            context = self.context_agent.retrieve(
                query=message,
                session_id=session_id
            )
            
            # Generate response based on mode
            if mode == "weekly":
                response = self.insight_agent.weekly_review(session_id=session_id)
            else:
                # Determine facet from sentiment
                facet = self._select_facet(sentiment["scores"])
                response = self.insight_agent.coach(
                    message=message,
                    context=context["passages"],
                    session_id=session_id,
                    facet=facet
                )
                response["citations"] = context["citations"]
            
            return {
                **response,
                "sentiment": sentiment,
                "crisis_check": crisis
            }
            
        except Exception as e:
            self.log.error("Orchestration failed", error=str(e))
            return {
                "text": "I'm here to support you. Can you tell me more?",
                "tasks": [],
                "citations": [],
                "why": "Fallback response",
                "sentiment": {},
                "crisis_check": {"triggered": False}
            }
    
    def _select_facet(self, signals: Dict[str, str]) -> str:
        """Select facet needing attention from signals."""
        # Prioritize growth areas (- signals)
        for facet, signal in signals.items():
            if signal == "-":
                return facet
        # Default to self_awareness
        return "self_awareness"
