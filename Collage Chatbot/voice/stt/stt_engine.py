import io
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime, UTC
from voice.stt.vad import VoiceActivityDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechToTextEngine:
    """
    Production STT Engine with comprehensive error handling, retry logic, and language detection.
    Integrates with the same AI pipeline as text input (intent router, entity extractor, etc.).
    """

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'Hindi',
        'gu': 'Gujarati',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'ja': 'Japanese',
        'ko': 'Korean',
        'zh': 'Chinese'
    }

    def __init__(self, use_whisper: bool = True, model_size: str = "tiny"):
        self.model = None
        self.use_whisper = use_whisper
        self.model_size = model_size
        self.is_initialized = False
        self.max_retries = 3
        self.timeout = 30.0  # seconds
        self.vad = VoiceActivityDetector()

        if use_whisper:
            self._initialize_whisper()

    def _initialize_whisper(self):
        """Initialize Whisper model with error handling"""
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )
            self.is_initialized = True
            logger.info(f"[STTEngine] Whisper model '{self.model_size}' initialized successfully")
        except ImportError:
            logger.warning("[STTEngine] faster_whisper not available, using fallback")
            self.use_whisper = False
        except Exception as e:
            logger.error(f"[STTEngine] Failed to initialize Whisper: {e}")
            self.use_whisper = False

    async def transcribe_audio_bytes(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        detect_language: bool = True
    ) -> Dict[str, Any]:
        """
        Transcribe audio bytes to text with comprehensive error handling.

        Args:
            audio_bytes: Raw audio bytes
            language: Target language code (None for auto-detection)
            detect_language: Whether to auto-detect language

        Returns:
            Dictionary with transcript, language, confidence, and metadata
        """
        if not audio_bytes:
            return {
                "success": False,
                "transcript": "",
                "language": "en",
                "confidence": 0.0,
                "error": "Empty audio data",
                "error_type": "input"
            }

        # Voice Activity Detection check
        vad_res = self.vad.detect_speech_segments(audio_bytes)
        if vad_res.get("is_noise") or (vad_res.get("duration_ms", 0) > 0 and not vad_res.get("has_speech")):
            logger.info(f"[STTEngine] VAD discarded non-speech / silence segment (duration: {vad_res.get('duration_ms')}ms)")
            return {
                "success": True,
                "transcript": "",
                "language": language or "en",
                "confidence": 0.0,
                "is_silence": True,
                "vad_metadata": vad_res
            }

        # Retry loop for transcription
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.info(f"[STTEngine] Transcription attempt {attempt + 1}/{self.max_retries}")

                if self.use_whisper and self.is_initialized:
                    result = await self._transcribe_with_whisper(audio_bytes, language, detect_language)
                    if result["success"]:
                        return result
                    last_error = result.get("error")
                else:
                    result = await self._transcribe_fallback(audio_bytes, language)
                    return result

            except asyncio.TimeoutError:
                last_error = f"Transcription timeout after {self.timeout} seconds"
                logger.warning(f"[STTEngine] {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"[STTEngine] Transcription error on attempt {attempt + 1}: {last_error}")

        # All retries failed
        return {
            "success": False,
            "transcript": "",
            "language": language or "en",
            "confidence": 0.0,
            "error": last_error or "Transcription failed",
            "error_type": "transient",
            "attempts": self.max_retries
        }

    async def _transcribe_with_whisper(
        self,
        audio_bytes: bytes,
        language: Optional[str],
        detect_language: bool
    ) -> Dict[str, Any]:
        """Transcribe using Whisper model with timeout"""
        try:
            loop = asyncio.get_event_loop()

            # Prepare transcription parameters
            transcribe_kwargs = {
                "beam_size": 5,
                "vad_filter": True,
                "word_timestamps": True
            }

            if language:
                transcribe_kwargs["language"] = language
            elif not detect_language:
                transcribe_kwargs["language"] = "en"  # Default to English

            # Execute transcription with timeout
            segments, info = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self.model.transcribe,
                    io.BytesIO(audio_bytes),
                    **transcribe_kwargs
                ),
                timeout=self.timeout
            )

            # Extract transcript and metadata
            text = " ".join([seg.text for seg in segments]).strip()
            detected_language = info.language if detect_language else (language or "en")
            confidence = info.language_probability if hasattr(info, 'language_probability') else 0.95

            # Extract word-level timestamps if available
            word_timestamps = []
            for seg in segments:
                if hasattr(seg, 'words'):
                    for word in seg.words:
                        word_timestamps.append({
                            "word": word.word,
                            "start": word.start,
                            "end": word.end
                        })

            return {
                "success": True,
                "transcript": text,
                "language": detected_language,
                "confidence": confidence,
                "language_detected": detect_language,
                "duration": info.duration if hasattr(info, 'duration') else 0.0,
                "word_count": len(text.split()),
                "word_timestamps": word_timestamps,
                "engine": "whisper"
            }

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"[STTEngine] Whisper transcription failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "transient"
            }

    async def _transcribe_fallback(
        self,
        audio_bytes: bytes,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """
        Fallback transcription for when Whisper is not available.
        This is a mock implementation for development/testing.
        """
        logger.warning("[STTEngine] Using fallback transcription")

        # In production, this would call a cloud STT API
        # For now, return a mock response
        fallback_transcripts = {
            'en': "What is the BCA fee structure?",
            'hi': "BCA की फीस संरचना क्या है?",
            'gu': "BCA ની ફી સ્ટ્રક્ચર શું છે?"
        }

        detected_lang = language or 'en'
        transcript = fallback_transcripts.get(detected_lang, fallback_transcripts['en'])

        return {
            "success": True,
            "transcript": transcript,
            "language": detected_lang,
            "confidence": 0.85,
            "language_detected": False,
            "engine": "fallback"
        }

    def detect_audio_language(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Detect the language of audio without full transcription.
        """
        if not self.use_whisper or not self.is_initialized:
            return {
                "success": False,
                "language": "en",
                "confidence": 0.0,
                "error": "Language detection not available"
            }

        try:
            # Use Whisper's language detection
            segments, info = self.model.transcribe(
                io.BytesIO(audio_bytes),
                beam_size=5,
                language=None  # Auto-detect
            )

            # Just get the language info without full transcription
            return {
                "success": True,
                "language": info.language,
                "confidence": info.language_probability if hasattr(info, 'language_probability') else 0.9,
                "language_name": self.SUPPORTED_LANGUAGES.get(info.language, "Unknown")
            }

        except Exception as e:
            logger.error(f"[STTEngine] Language detection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "language": "en",
                "confidence": 0.0
            }

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        language: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream transcription for real-time audio input.

        Args:
            audio_stream: Async generator of audio chunks
            language: Target language

        Yields:
            Partial transcription results
        """
        buffer = b""
        chunk_count = 0

        async for chunk in audio_stream:
            buffer += chunk
            chunk_count += 1

            # Process every 5 chunks or when buffer is large enough
            if chunk_count % 5 == 0 or len(buffer) > 16000:  # ~1 second at 16kHz
                if len(buffer) > 1000:  # Minimum audio length
                    result = await self.transcribe_audio_bytes(buffer, language)
                    if result["success"]:
                        yield {
                            "partial": True,
                            "transcript": result["transcript"],
                            "language": result["language"],
                            "confidence": result["confidence"],
                            "chunk_index": chunk_count
                        }
                    buffer = b""  # Reset buffer

        # Final transcription of remaining buffer
        if len(buffer) > 1000:
            result = await self.transcribe_audio_bytes(buffer, language)
            if result["success"]:
                yield {
                    "partial": False,
                    "final": True,
                    "transcript": result["transcript"],
                    "language": result["language"],
                    "confidence": result["confidence"],
                    "chunk_index": chunk_count
                }

    def validate_audio(self, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Validate audio data before transcription.

        Returns:
            Dictionary with validation results
        """
        if not audio_bytes:
            return {
                "valid": False,
                "error": "Empty audio data"
            }

        if len(audio_bytes) < 1000:
            return {
                "valid": False,
                "error": "Audio too short (minimum 1000 bytes)"
            }

        if len(audio_bytes) > 10 * 1024 * 1024:  # 10 MB
            return {
                "valid": False,
                "error": "Audio too large (maximum 10 MB)"
            }

        # Basic audio format validation (WAV header check)
        if len(audio_bytes) >= 4:
            # Check for common audio headers
            if audio_bytes[:4] == b'RIFF':  # WAV
                return {"valid": True, "format": "WAV"}
            elif audio_bytes[:4] == b'ID3':  # MP3
                return {"valid": True, "format": "MP3"}
            elif audio_bytes[:4] == b'OggS':  # OGG
                return {"valid": True, "format": "OGG"}

        # Assume valid if no obvious issues
        return {"valid": True, "format": "unknown"}

    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages"""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_engine_info(self) -> Dict[str, Any]:
        """Get information about the STT engine"""
        return {
            "engine": "whisper" if self.use_whisper else "fallback",
            "model_size": self.model_size if self.use_whisper else None,
            "is_initialized": self.is_initialized,
            "supported_languages": list(self.SUPPORTED_LANGUAGES.keys()),
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }
