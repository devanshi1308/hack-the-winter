import os
import sys
from dotenv import load_dotenv
from utils.config_loader import load_config
from langchain_google_genai import GoogleGenerativeAI, ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)

class ModelLoader:
    """A Utility Class for Loading the Embedding Models and LLM Models"""
    def __init__(self):
        load_dotenv()
        self._validate_env()
        self.config = load_config()
        log.info("Configuration loaded successfully", config_keys = list(self.config.keys()))

    def _validate_env(self):
        """Validate necessary environment variables and Ensure API Keys exists."""
        # Check for at least one API key (more lenient)
        google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        self.api_keys = {
            "GOOGLE_API_KEY": google_key,
            "GROQ_API_KEY": groq_key,
            "OPENAI_API_KEY": openai_key
        }
        
        # Check if at least one provider is available
        available_providers = [k for k, v in self.api_keys.items() if v]
        
        if not available_providers:
            log.error("No API keys found", 
                     hint="Set at least one: GOOGLE_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY")
            raise DocumentPortalException(
                "No LLM API keys configured. Please set at least one: GOOGLE_API_KEY, GROQ_API_KEY, or OPENAI_API_KEY"
            )
        
        log.info("Available LLM providers", providers=available_providers)


    def load_embeddings(self):
        """Load and Return the Embedding Model"""
        try:
            log.info("Loading embedding model.....")
            model_name = self.config["embedding_model"]["model_name"]
            
            # Check if Google API key is available
            if not self.api_keys.get("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY not found. Embeddings require Google Gemini API.")
            
            return GoogleGenerativeAIEmbeddings(model = model_name)
        except Exception as e:
            log.error("Error loading embedding model", error = str(e))
            raise DocumentPortalException(f"Failed to load embedding model: {str(e)}")

    def load_llm(self):
        """Load and Return the LLM Model with priority: OpenAI → Gemini → Groq"""

        llm_block = self.config["llm"]

        # Priority order: OpenAI first, then Google, then Groq
        provider_priority = []
        if self.api_keys.get("OPENAI_API_KEY"):
            provider_priority.append("openai")
        if self.api_keys.get("GOOGLE_API_KEY"):
            provider_priority.append("google")
        if self.api_keys.get("GROQ_API_KEY"):
            provider_priority.append("groq")

        if not provider_priority:
            log.error("No LLM API keys available")
            raise ValueError("No LLM API keys configured")

        # Try each provider in priority order
        last_error = None
        for provider_key in provider_priority:
            try:
                if provider_key not in llm_block:
                    continue
                
                llm_config = llm_block[provider_key]
                provider = llm_config.get("provider")
                model_name = llm_config.get("model_name")
                temperature = llm_config.get("temperature", 0.2)
                max_tokens = llm_config.get("max_output_tokens", 2048)

                log.info("Loading LLM", provider=provider, model=model_name, temperature=temperature, max_tokens=max_tokens)

                if provider == "openai":
                    llm = ChatOpenAI(
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    log.info("Loaded LLM successfully", class_name="ChatOpenAI")
                    return llm

                elif provider == "google":
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        temperature=temperature,
                        max_output_tokens=max_tokens
                    )
                    log.info("Loaded LLM successfully", class_name="ChatGoogleGenerativeAI")
                    return llm
                
                elif provider == "groq":
                    llm = ChatGroq(
                        model=model_name,
                        temperature=temperature
                    )
                    log.info("Loaded LLM successfully", class_name="ChatGroq")
                    return llm

            except Exception as e:
                last_error = e
                log.warning("LLM provider failed, trying next", provider=provider_key, error=str(e))
                continue

        # All providers failed
        log.error("All LLM providers failed", error=str(last_error))
        raise DocumentPortalException(f"Could not load any LLM provider. Last error: {str(last_error)}")

if __name__ == "__main__":
    loader = ModelLoader()
    
    # Test embedding model loading
    embeddings = loader.load_embeddings()
    print(f"Embedding Model Loaded: {embeddings}")
    
    # Test the ModelLoader
    result=embeddings.embed_query("Hello, how are you?")
    print(f"Embedding Result: {result}")
    
    # Test LLM loading based on YAML config
    llm = loader.load_llm()
    print(f"LLM Loaded: {llm}")
    
    # Test the ModelLoader
    result=llm.invoke("Hello, how are you?")
    print(f"LLM Result: {result}")
