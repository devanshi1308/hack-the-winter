"""
ElevenLabs TTS/STT integration with mock fallbacks.

Real audio generation/transcription activates when ELEVENLABS_API_KEY is set.
Otherwise, returns mock responses for testing.
"""

import os
from typing import Optional, Dict, Any
import io

from logger.custom_logger import CustomLogger

_LOG = CustomLogger().get_logger(__name__)


class ElevenLabsClient:
    """
    ElevenLabs API client with graceful fallback to mocks.
    
    Features:
    - Text-to-Speech (TTS): Convert text to audio
    - Speech-to-Text (STT): Transcribe audio to text
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Accept a single key or a comma-separated list; pick the first non-empty
        raw_key = api_key or os.getenv("ELEVENLABS_API_KEY") or ""
        if "," in raw_key:
            parts = [p.strip() for p in raw_key.split(",") if p.strip()]
            self.api_key = parts[0] if parts else ""
        else:
            self.api_key = raw_key
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                # Import only if we have an API key
                import elevenlabs  # type: ignore
                self.client = elevenlabs.ElevenLabs(api_key=self.api_key)
                _LOG.info("ElevenLabs client initialized with real API")
            except ImportError:
                _LOG.warning("elevenlabs package not installed, using mock responses")
                self.enabled = False
            except Exception as e:
                _LOG.error("Failed to initialize ElevenLabs client", error=str(e))
                self.enabled = False
        else:
            _LOG.info("ElevenLabs API key not set, using mock responses")
    
    def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice: Rachel
        model: str = "eleven_monolingual_v1"
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID
            model: Model to use for generation
            
        Returns:
            Audio bytes (MP3 format)
        """
        if not self.enabled:
            return self._mock_tts(text)
        
        try:
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id=model
            )
            
            # Collect audio chunks
            audio_bytes = b"".join(audio_generator)
            _LOG.info("TTS generated successfully", text_length=len(text))
            return audio_bytes
            
        except Exception as e:
            _LOG.error("TTS generation failed, using mock", error=str(e))
            return self._mock_tts(text)
    
    def speech_to_text(
        self,
        audio_bytes: bytes,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.
        
        Args:
            audio_bytes: Audio file bytes (WAV, MP3, etc.)
            language: Language code
            
        Returns:
            Dict with keys: transcript, confidence
        """
        if not self.enabled:
            return self._mock_stt(audio_bytes)
        
        try:
            # ElevenLabs STT (if available in their API)
            # Note: As of 2025, ElevenLabs may not have STT - using Whisper as fallback
            return self._whisper_fallback(audio_bytes, language)
            
        except Exception as e:
            _LOG.error("STT transcription failed, using mock", error=str(e))
            return self._mock_stt(audio_bytes)
    
    def _whisper_fallback(self, audio_bytes: bytes, language: str) -> Dict[str, Any]:
        """
        Use OpenAI Whisper for STT as fallback.
        """
        try:
            import openai  # type: ignore
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Create file-like object
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.mp3"
            
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
            
            _LOG.info("STT transcribed via Whisper", length=len(transcript.text))
            return {
                "transcript": transcript.text,
                "confidence": 0.95  # Whisper doesn't provide confidence scores
            }
            
        except ImportError:
            _LOG.warning("openai package not installed for Whisper fallback")
            return self._mock_stt(audio_bytes)
        except Exception as e:
            _LOG.error("Whisper transcription failed", error=str(e))
            return self._mock_stt(audio_bytes)
    
    def _mock_tts(self, text: str) -> bytes:
        """
        Return mock audio as a small valid WAV tone to ensure browser playback.
        """
        _LOG.debug("Using mock TTS (WAV tone)", text_length=len(text))
        import math
        import struct

        sample_rate = 44100
        duration_s = 0.6
        freq = 440.0
        num_samples = int(sample_rate * duration_s)
        amplitude = 0.2

        # Generate PCM 16-bit mono samples
        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            sample = int(32767 * amplitude * math.sin(2 * math.pi * freq * t))
            frames += struct.pack('<h', sample)

        # Build WAV header
        byte_rate = sample_rate * 2  # mono, 16-bit
        block_align = 2
        subchunk2_size = len(frames)
        chunk_size = 36 + subchunk2_size

        header = bytearray()
        header.extend(b'RIFF')
        header.extend(struct.pack('<I', chunk_size))
        header.extend(b'WAVE')
        header.extend(b'fmt ')
        header.extend(struct.pack('<I', 16))           # Subchunk1Size (PCM)
        header.extend(struct.pack('<H', 1))            # AudioFormat (PCM)
        header.extend(struct.pack('<H', 1))            # NumChannels (mono)
        header.extend(struct.pack('<I', sample_rate))  # SampleRate
        header.extend(struct.pack('<I', byte_rate))    # ByteRate
        header.extend(struct.pack('<H', block_align))  # BlockAlign
        header.extend(struct.pack('<H', 16))           # BitsPerSample
        header.extend(b'data')
        header.extend(struct.pack('<I', subchunk2_size))

        return bytes(header + frames)
    
    def _mock_stt(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Return mock transcript for testing.
        """
        _LOG.debug("Using mock STT", audio_length=len(audio_bytes))
        return {
            "transcript": "This is a mock transcription. Enable ELEVENLABS_API_KEY or OPENAI_API_KEY for real transcription.",
            "confidence": 0.0
        }
    
    def list_voices(self) -> list:
        """
        List available voices.
        
        Returns:
            List of voice objects with id, name, description
        """
        if not self.enabled:
            return self._mock_voices()
        
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    "voice_id": v.voice_id,
                    "name": v.name,
                    "category": getattr(v, "category", "generated"),
                    "description": getattr(v, "description", "")
                }
                for v in voices.voices
            ]
        except Exception as e:
            _LOG.error("Failed to list voices", error=str(e))
            return self._mock_voices()
    
    def _mock_voices(self) -> list:
        """Return mock voice list."""
        return [
            {
                "voice_id": "21m00Tcm4TlvDq8ikWAM",
                "name": "Rachel (Mock)",
                "category": "premade",
                "description": "Mock voice for testing"
            },
            {
                "voice_id": "AZnzlk1XvdvUeBnXmlld",
                "name": "Domi (Mock)",
                "category": "premade",
                "description": "Mock voice for testing"
            }
        ]


# Global instance
_elevenlabs_client: Optional[ElevenLabsClient] = None


def get_elevenlabs() -> ElevenLabsClient:
    """Get or create global ElevenLabs client."""
    global _elevenlabs_client
    if _elevenlabs_client is None:
        _elevenlabs_client = ElevenLabsClient()
    return _elevenlabs_client
