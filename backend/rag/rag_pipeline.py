import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Any

from dotenv import load_dotenv  # type: ignore
from langchain_community.document_loaders import PyPDFLoader  # type: ignore
from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
from langchain_community.vectorstores import FAISS  # type: ignore
from langchain_core.chat_history import BaseChatMessageHistory  # type: ignore
from langchain_community.chat_message_histories import ChatMessageHistory  # type: ignore
from langchain_core.runnables.history import RunnableWithMessageHistory  # type: ignore

from utils.model_loader import ModelLoader
from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from prompts.prompt_lib import PROMPT_REGISTRY  
from model.models import PromptType


class SingleDocumentIngestor:
    """
    Ingests one or more uploaded PDFs, builds a FAISS index locally,
    and returns a similarity retriever (k=5). Mirrors your original class.
    """

    def __init__(self, data_dir: str = "data/single_document_chat", faiss_dir: str = "faiss_index"):
        try:
            self.log = CustomLogger().get_logger(__name__)
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)

            self.faiss_dir = Path(faiss_dir)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)

            self.model_loader = ModelLoader()

            self.log.info(
                "SingleDocumentIngestor initialized successfully",
                temp_path=str(self.data_dir),
                faiss_path=str(self.faiss_dir),
            )
        except Exception as e:
            print(f"Error initializing SingleDocumentIngestor: {e}")
            raise DocumentPortalException("Initialization error in SingleDocumentIngestor", sys)

    def ingest_files(self, uploaded_files) -> Any:
        """
        Save incoming PDFs to temp dir, load pages as Documents, chunk, embed, save FAISS, return retriever.
        """
        try:
            documents = []

            for uploaded_file in uploaded_files:
                unique_file_name = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.pdf"
                temp_path = self.data_dir / unique_file_name
                with open(temp_path, "wb") as f_out:
                    f_out.write(uploaded_file.getbuffer())
                self.log.info("PDF saved for ingestion", filename=getattr(uploaded_file, "name", unique_file_name))
                loader = PyPDFLoader(str(temp_path))
                docs = loader.load()
                documents.extend(docs)

            self.log.info("PDF files loaded", count=len(documents))
            return self._create_retriever(documents)

        except Exception as e:
            self.log.error("Document Ingestion Failed", error=str(e))
            raise DocumentPortalException("Error ingesting files", sys)

    def _create_retriever(self, documents):
        """
        Split documents, create FAISS, persist, return similarity retriever (k=5).
        """
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=300)
            chunks = splitter.split_documents(documents)
            self.log.info("Documents split into chunks", count=len(chunks))

            embeddings = self.model_loader.load_embeddings()
            vectorstore = FAISS.from_documents(documents=chunks, embedding=embeddings)

            # Save FAISS index to disk
            vectorstore.save_local(str(self.faiss_dir))
            self.log.info("FAISS index created and saved", path=str(self.faiss_dir))

            retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
            self.log.info("Retriever created successfully")
            return retriever

        except Exception as e:
            self.log.error("Error creating retriever", error=str(e))
            raise DocumentPortalException("Error creating FAISS retriever", sys)


class ConversationalRAG:
    """
    Conversation-aware RAG that:
      - contextualizes user questions using chat history,
      - retrieves relevant chunks,
      - stuffs into a QA chain with your prompts,
      - maintains per-session memory via RunnableWithMessageHistory.

    Also includes EI-specific exercise recommendation functionality.
    """

    def __init__(self, faiss_dir: str = "rag/vectorstore", llm=None):
        try:
            load_dotenv()
            self.log = CustomLogger().get_logger(__name__)
            self.faiss_dir = faiss_dir
            # allow dependency injection; if not provided, try to load but don't hard-fail
            if llm is not None:
                self.llm = llm
            else:
                try:
                    self.llm = self._load_llm()
                except Exception as e:
                    # degrade gracefully; methods will fallback when llm is None
                    try:
                        self.log.warning("LLM load failed; continuing with fallbacks", error=str(e))
                    except Exception:
                        pass
                    self.llm = None
            self.contextualize_prompt = PROMPT_REGISTRY["contextualize_question"]
            self.qa_prompt = PROMPT_REGISTRY["context_qa"]

            self.log.info("ConversationalRAG initialized", faiss_dir=faiss_dir)
        except Exception as e:
            try:
                self.log.error("Error during ConversationalRAG init", error=str(e))
            except Exception:
                pass
            # don't raise here to keep construction lenient in unit tests
            self.llm = None

    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            self.log.info("Loaded LLM successfully", class_name=llm.__class__.__name__)
            return llm
        except Exception as e:
            self.log.error("Error loading LLM", error=str(e))
            raise DocumentPortalException("Error loading LLM", sys)

    def load_retriever_from_faiss(self) -> Any:
        """
        Load an on-disk FAISS index and return a similarity retriever (k=5).
        """
        try:
            embeddings = ModelLoader().load_embeddings()
            if not os.path.isdir(self.faiss_dir):
                raise FileNotFoundError(f"FAISS index directory not found at {self.faiss_dir}")

            # allow_dangerous_deserialization=True to avoid LC pickling guard issues
            vectorstore = FAISS.load_local(self.faiss_dir, embeddings, allow_dangerous_deserialization=True)
            self.log.info("FAISS retriever loaded successfully", index_path=self.faiss_dir)
            return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

        except Exception as e:
            self.log.error("Error loading FAISS retriever", error=str(e))
            raise DocumentPortalException("Error loading FAISS retriever", sys)

    def index_documents(self, documents: List[Any]):
        """
        Index documents and save FAISS vectorstore.
        """
        try:
            embeddings = ModelLoader().load_embeddings()
            vectorstore = FAISS.from_documents(documents=documents, embedding=embeddings)
            
            # Create directory if it doesn't exist
            os.makedirs(self.faiss_dir, exist_ok=True)
            vectorstore.save_local(self.faiss_dir)
            
            self.log.info("Documents indexed and saved", count=len(documents), path=self.faiss_dir)
            return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        except Exception as e:
            self.log.error("Error indexing documents", error=str(e))
            raise DocumentPortalException("Error indexing documents", sys)

    def search(self, retriever: Any, query: str, k: int = 5) -> List[str]:
        """
        Search for relevant chunks using the retriever.
        Returns list of chunk texts.
        """
        try:
            if hasattr(retriever, "get_relevant_documents"):
                docs = retriever.get_relevant_documents(query)
            else:
                # Runnable-style retrievers use invoke()
                docs = retriever.invoke(query)
            chunks = [doc.page_content for doc in docs[:k]]
            self.log.info("Search completed", query=query[:50], chunks_found=len(chunks))
            return chunks
        except Exception as e:
            self.log.error("Error in search", error=str(e))
            return []

    def synthesize_exercise(self, chunks: List[str], target_facets: List[str], 
                           context_tags: List[str], duration_hint: str) -> dict:
        """
        Synthesize an exercise recommendation from retrieved chunks.
        """
        try:
            chunks_block = "\n\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(chunks)])
            
            prompt = PROMPT_REGISTRY["recommend_exercise"]
            messages = prompt.format_messages(
                target_facets=target_facets,
                context_tags=context_tags,
                duration_hint=duration_hint,
                chunks_block=chunks_block
            )
            
            resp = self.llm.invoke(messages)
            raw = getattr(resp, "content", None) or str(resp)
            
            # Try to parse JSON
            import json
            try:
                # Clean JSON if wrapped in markdown
                cleaned = raw.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                
                exercise_data = json.loads(cleaned.strip())
                return exercise_data
            except json.JSONDecodeError:
                # Fallback to basic exercise
                return {
                    "exercise_id": "fallback_exercise",
                    "title": "Mindful Breathing",
                    "steps": ["Find a quiet space", "Breathe in for 4 counts", "Hold for 4 counts", "Exhale for 4 counts", "Repeat 5 times"],
                    "expected_outcome": "Increased calm and focus",
                    "source_doc_id": "fallback",
                    "followup_question": "How do you feel after this breathing exercise?"
                }
                
        except Exception as e:
            self.log.error("Error synthesizing exercise", error=str(e))
            # Return fallback exercise
            return {
                "exercise_id": "fallback_exercise", 
                "title": "Basic Mindfulness",
                "steps": ["Take three deep breaths", "Notice your surroundings", "Focus on the present moment"],
                "expected_outcome": "Improved awareness and calm",
                "source_doc_id": "fallback",
                "followup_question": "What did you notice during this exercise?"
            }

    def get_exercise(self, retriever: Any, target_facets: List[str], 
                    context_tags: List[str], duration_hint: str) -> dict:
        """
        Complete exercise recommendation pipeline.
        """
        # Build query
        query_parts = target_facets + context_tags + [duration_hint, "exercise"]
        query = " ".join(query_parts)
        
        # Search and synthesize
        chunks = self.search(retriever, query, k=5)
        exercise = self.synthesize_exercise(chunks, target_facets, context_tags, duration_hint)
        
        # Validate and prepare
        from core.recommender import prepare_recommendation
        return prepare_recommendation(exercise)