import os
import asyncio
import time
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime, UTC
import logging
from ai.providers.base import AIProvider
from backend.app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    """
    Enhanced Gemini provider with retry logic, rate-limit awareness, and error handling.
    Implements exponential backoff, transient error detection, and graceful fallback.
    """

    # Transient errors that should be retried
    TRANSIENT_ERRORS = [
        "timeout", "deadline", "connection", "network", "unavailable",
        "503", "502", "500", "429", "rate limit", "quota exceeded"
    ]

    # Non-retryable errors
    NON_RETRYABLE_ERRORS = [
        "authentication", "authorization", "invalid api key", "permission denied",
        "400", "401", "403", "404"
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self._initialize_client()

        # Retry configuration
        self.max_retries = 3
        self.base_retry_delay = 1.0  # seconds
        self.max_retry_delay = 32.0  # seconds
        self.timeout = 30.0  # seconds

        # Rate limiting configuration
        self.rate_limit_backoff = 60.0  # seconds when rate limited
        self.last_rate_limit_time = None
        self.request_count = 0
        self.rate_limit_window = 60  # seconds
        self.max_requests_per_window = 60

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.retry_count = 0

    def _initialize_client(self):
        if self.api_key:
            try:
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=FutureWarning)
                    warnings.simplefilter("ignore", category=UserWarning)
                    import google.generativeai as genai
                    genai.configure(api_key=self.api_key)
                    self.client = genai.GenerativeModel(
                        model_name="gemini-1.5-flash",
                        generation_config={
                            "temperature": 0.2,
                            "top_p": 0.95,
                            "top_k": 40,
                            "max_output_tokens": 1024,
                        }
                    )
                logger.info("[GeminiProvider] Successfully initialized Google GenAI SDK")
            except Exception as e:
                logger.error(f"[GeminiProvider] Failed to initialize Google GenAI SDK: {e}")
                self.client = None
        else:
            logger.warning("[GeminiProvider] No API key provided")

    def _is_transient_error(self, error: str) -> bool:
        """Check if an error is transient and should be retried"""
        error_lower = error.lower()
        return any(transient in error_lower for transient in self.TRANSIENT_ERRORS)

    def _is_non_retryable_error(self, error: str) -> bool:
        """Check if an error is non-retryable"""
        error_lower = error.lower()
        return any(non_retryable in error_lower for non_retryable in self.NON_RETRYABLE_ERRORS)

    def _calculate_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay"""
        delay = self.base_retry_delay * (2 ** attempt)
        return min(delay, self.max_retry_delay)

    def _should_rate_limit(self) -> bool:
        """Check if we should rate limit based on recent request history"""
        if self.last_rate_limit_time:
            time_since_limit = (datetime.now(UTC) - self.last_rate_limit_time).total_seconds()
            if time_since_limit < self.rate_limit_backoff:
                return True

        return False

    def _check_rate_limit(self, error: str) -> bool:
        """Check if error indicates rate limiting"""
        error_lower = error.lower()
        return "429" in error_lower or "rate limit" in error_lower or "quota exceeded" in error_lower

    def _handle_rate_limit(self):
        """Handle rate limiting with backoff"""
        self.last_rate_limit_time = datetime.now(UTC)
        logger.warning(f"[GeminiProvider] Rate limit detected, backing off for {self.rate_limit_backoff} seconds")
        time.sleep(self.rate_limit_backoff)

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """
        Generate response with retry logic and rate limit awareness.

        Args:
            prompt: User prompt
            system_instruction: System instruction for the model
            context: Additional context for grounding
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with response data
        """
        if not self.client or not self.api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY_NOT_CONFIGURED",
                "text": "",
                "error_type": "configuration",
                "attempts": 0,
                "retry_count": 0
            }

        full_prompt = ""
        if system_instruction:
            full_prompt += f"System Instructions:\n{system_instruction}\n\n"
        if context:
            full_prompt += f"Authoritative Context (STRICT GROUND TRUTH):\n{context}\n\n"
        full_prompt += f"User Query:\n{prompt}"

        self.total_requests += 1

        # Check rate limiting
        if self._should_rate_limit():
            logger.warning("[GeminiProvider] Currently rate limited, waiting...")
            await asyncio.sleep(self.rate_limit_backoff)

        # Retry loop
        last_error = None
        last_response_text = None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"[GeminiProvider] Attempt {attempt + 1}/{self.max_retries + 1}")

                # Execute with timeout
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, self.client.generate_content, full_prompt),
                    timeout=self.timeout
                )

                if response and response.text:
                    response_text = response.text.strip()
                    # Validate non-empty response
                    if len(response_text) > 5:  # Minimum reasonable response length
                        self.successful_requests += 1
                        logger.info(f"[GeminiProvider] Request successful on attempt {attempt + 1}")
                        return {
                            "success": True,
                            "text": response_text,
                            "model": "gemini-1.5-flash",
                            "raw": response,
                            "attempts": attempt + 1,
                            "retry_count": attempt
                        }
                    else:
                        last_response_text = response_text
                        last_error = f"Response too short: {len(response_text)} characters"
                        logger.warning(f"[GeminiProvider] {last_error}")
                        # Retry if we have attempts left
                        if attempt < self.max_retries:
                            continue
                else:
                    last_error = "Empty response from Gemini"
                    logger.warning(f"[GeminiProvider] {last_error}")

            except asyncio.TimeoutError:
                last_error = f"Request timeout after {self.timeout} seconds"
                logger.warning(f"[GeminiProvider] {last_error}")

            except Exception as e:
                last_error = str(e)
                logger.error(f"[GeminiProvider] Error on attempt {attempt + 1}: {last_error}")

                # Check for rate limiting
                if self._check_rate_limit(last_error):
                    self._handle_rate_limit()
                    continue

                # Check for non-retryable errors
                if self._is_non_retryable_error(last_error):
                    logger.error(f"[GeminiProvider] Non-retryable error: {last_error}")
                    break

                # Check if we should retry
                if attempt < self.max_retries and self._is_transient_error(last_error):
                    self.retry_count += 1
                    delay = self._calculate_retry_delay(attempt)
                    logger.info(f"[GeminiProvider] Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    break

        # All retries failed
        self.failed_requests += 1
        logger.error(f"[GeminiProvider] All retries failed. Last error: {last_error}")

        # Return safe error message instead of empty text
        return {
            "success": False,
            "error": last_error or "Unknown error",
            "text": "I couldn't generate a response right now. Please try asking the question again.",
            "error_type": "transient" if self._is_transient_error(last_error or "") else "permanent",
            "attempts": self.max_retries + 1,
            "retry_count": self.retry_count
        }

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response with retry logic.

        Args:
            prompt: User prompt
            system_instruction: System instruction
            context: Additional context
            temperature: Temperature for generation

        Yields:
            Chunks of generated text
        """
        res = await self.generate_response(prompt, system_instruction, context, temperature)
        if res["success"]:
            text = res["text"]
            # Stream tokens in small chunks
            words = text.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
                yield chunk
                await asyncio.sleep(0.02)
        else:
            error_msg = f"[Gemini Unavailable: {res.get('error', 'Unknown Error')}]"
            logger.error(f"[GeminiProvider] Stream error: {error_msg}")
            yield error_msg

    def get_statistics(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "retry_count": self.retry_count,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "is_rate_limited": self._should_rate_limit(),
            "last_rate_limit_time": self.last_rate_limit_time.isoformat() if self.last_rate_limit_time else None
        }

    def reset_statistics(self):
        """Reset provider statistics"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.retry_count = 0
        self.last_rate_limit_time = None
        logger.info("[GeminiProvider] Statistics reset")
