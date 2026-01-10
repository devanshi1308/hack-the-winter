import os
import sys
import base64
import io
import json
from typing import Any, Dict
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

    def load_vision_model(self, provider: str = "gemini"):
        """Load and return a vision provider (wrapper for image analysis)."""
        if provider == "gemini":
            api_key = self.api_keys.get("GOOGLE_API_KEY")
            if not api_key:
                log.error("Gemini API key not configured")
                raise DocumentPortalException("GOOGLE_API_KEY not found. Vision analysis requires Gemini API.")
            log.info("Loading vision model", provider="gemini")
            return VisionProvider(provider="gemini", api_key=api_key)
        else:
            log.error("Unknown vision provider", provider=provider)
            raise DocumentPortalException(f"Unknown vision provider: {provider}")


class VisionProvider:
    """Wrapper class for vision analysis using different providers."""
    
    def __init__(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self._log = CustomLogger().get_logger(__name__)
        if provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.genai = genai
                self._log.info("VisionProvider initialized", provider="gemini")
            except Exception as e:
                self._log.error("Failed to initialize Gemini vision", error=str(e))
                raise DocumentPortalException(f"Failed to initialize Gemini: {str(e)}")
    
    def analyze(self, image_input: str, input_type: str, task: str = "emotion"):
        """
        Analyze an image using the configured provider.
        """
        try:
            if input_type == "base64":
                image_data = self._prepare_base64_image(image_input)
            elif input_type == "url":
                image_data = image_input
            else:
                raise ValueError(f"Invalid input_type: {input_type}")
            
            if self.provider == "gemini":
                return self._analyze_with_gemini(image_data, input_type, task)
            else:
                raise DocumentPortalException(f"Provider {self.provider} not supported")
        except Exception as e:
            self._log.error("Vision analysis failed", error=str(e), task=task)
            raise
    
    def _prepare_base64_image(self, base64_str: str):
        """Decode base64 image and return a PIL Image for Gemini API."""
        try:
            # Remove data URI prefix if present
            if "," in base64_str:
                base64_str = base64_str.split(",", 1)[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(base64_str)
            self._log.info("Base64 image decoded", size=len(image_bytes))
            
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                self._log.info("PIL Image created successfully")
                return img
            except Exception as pe:
                # If PIL unavailable or fails, fall back to raw bytes
                self._log.warning("PIL failed to open image; falling back to bytes", error=str(pe))
                return image_bytes
        except Exception as e:
            self._log.error("Failed to decode base64 image", error=str(e))
            raise DocumentPortalException(f"Invalid base64 image: {str(e)}")
    
    def _analyze_with_gemini(self, image_data, input_type: str, task: str):
        """Use Gemini's vision capabilities to analyze an image."""
        try:
            # Use gemini-2.0-flash for vision tasks
            model = self.genai.GenerativeModel("gemini-2.5-flash")
            
            prompt = self._get_vision_prompt(task)
            self._log.info("Starting Gemini vision analysis", task=task, input_type=input_type)
            
            if input_type == "url":
                # For URL, we need to download and convert to PIL Image
                try:
                    import requests
                    from PIL import Image
                    
                    response = requests.get(image_data, timeout=10)
                    response.raise_for_status()
                    img = Image.open(io.BytesIO(response.content)).convert("RGB")
                    self._log.info("URL image downloaded and converted", url=image_data)
                    response = model.generate_content([prompt, img])
                except Exception as url_error:
                    self._log.error("Failed to fetch image from URL", error=str(url_error), url=image_data)
                    raise DocumentPortalException(f"Failed to fetch image from URL: {str(url_error)}")
            else:  # base64 -> PIL Image or bytes
                response = model.generate_content([prompt, image_data])
            
            # Parse response
            result_text = response.text
            self._log.info("Gemini response received", response_length=len(result_text))
            
            return self._parse_vision_response(result_text, task)
        
        except Exception as e:
            self._log.error("Gemini vision analysis failed", error=str(e), task=task)
            raise DocumentPortalException(f"Gemini analysis failed: {str(e)}")
    
    def _get_vision_prompt(self, task: str) -> str:
        """Get the appropriate prompt based on the task."""
        prompts = {
            "emotion": """Analyze the emotions visible in this image. Look at facial expressions, body language, and overall mood.
            Return your response as a JSON object with this exact structure:
            {
                "emotions": [
                    {"label": "happy", "confidence": 0.85},
                    {"label": "excited", "confidence": 0.65}
                ]
            }
            Only include emotions you can detect with reasonable confidence (>0.3).""",
            
            "scene": """Describe what you see in this image. Identify objects, activities, and concepts.
            Return your response as a JSON object with this exact structure:
            {
                "objects": ["person", "mountain", "sky"],
                "activities": ["hiking", "exploring"],
                "concepts": ["adventure", "nature"]
            }""",
            
            "text": """Extract and recognize all text visible in this image.
            Return your response as a JSON object with this exact structure:
            {
                "text": ["line 1 of text", "line 2 of text"]
            }
            If no text is found, return {"text": []}"""
        }
        return prompts.get(task, prompts["emotion"])
    
    def _parse_vision_response(self, response_text: str, task: str):
        """Parse Gemini response and normalize to standard format."""
        try:
            # Clean the response text
            response_text = response_text.strip()
            
            # Try to extract JSON from markdown code blocks
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                json_str = response_text[start:end].strip()
            else:
                # Try to find JSON object
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                
                if start != -1 and end > start:
                    json_str = response_text[start:end]
                else:
                    raise ValueError("No JSON found in response")
            
            # Parse the JSON
            data = json.loads(json_str)
            self._log.info("Successfully parsed JSON response", data_keys=list(data.keys()))
            
            # Normalize to standard format
            labels = []
            confidence = []
            
            if task == "emotion" and "emotions" in data:
                for item in data["emotions"]:
                    labels.append(item.get("label", "unknown"))
                    confidence.append(float(item.get("confidence", 0.5)))
                self._log.info("Parsed emotions", count=len(labels))
                
            elif task == "scene":
                if "objects" in data:
                    labels.extend(data["objects"])
                    confidence.extend([0.7] * len(data.get("objects", [])))
                if "activities" in data:
                    labels.extend(data["activities"])
                    confidence.extend([0.7] * len(data.get("activities", [])))
                if "concepts" in data:
                    labels.extend(data.get("concepts", []))
                    confidence.extend([0.6] * len(data.get("concepts", [])))
                self._log.info("Parsed scene", count=len(labels))
                
            elif task == "text" and "text" in data:
                labels = data["text"]
                confidence = [0.9] * len(labels)
                self._log.info("Parsed text", count=len(labels))
            
            # Return empty arrays if nothing was found
            if not labels:
                self._log.warning("No data extracted from response", task=task)
                labels = ["no_detection"]
                confidence = [0.0]
            
            return {
                "labels": labels,
                "confidence": confidence,
                "metadata": {
                    "provider": self.provider,
                    "task": task,
                    "source": "vision_api",
                    "raw_response": response_text[:500]  # Include truncated raw response for debugging
                }
            }
        
        except json.JSONDecodeError as e:
            self._log.error("Failed to parse vision response JSON", error=str(e), response=response_text[:200])
            # Return fallback with actual response text for debugging
            return {
                "labels": ["parse_error"],
                "confidence": [0.0],
                "metadata": {
                    "provider": self.provider,
                    "task": task,
                    "fallback": True,
                    "error": "parse_error",
                    "error_detail": str(e),
                    "raw_response": response_text[:500]
                }
            }
        except Exception as e:
            self._log.error("Unexpected error parsing response", error=str(e), response=response_text[:200])
            return {
                "labels": ["error"],
                "confidence": [0.0],
                "metadata": {
                    "provider": self.provider,
                    "task": task,
                    "fallback": True,
                    "error": str(e)
                }
            }


if __name__ == "__main__":
    # Test code - only runs when executing this file directly
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