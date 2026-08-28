import os
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from ai.providers.base import AIProvider
from backend.app.config import settings

class GeminiProvider(AIProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.api_key:
            try:
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
            except Exception as e:
                print(f"[GeminiProvider] Warning: Failed to initialize Google GenAI SDK: {e}")
                self.client = None

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        if not self.client or not self.api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY_NOT_CONFIGURED",
                "text": ""
            }

        full_prompt = ""
        if system_instruction:
            full_prompt += f"System Instructions:\n{system_instruction}\n\n"
        if context:
            full_prompt += f"Authoritative Context (STRICT GROUND TRUTH):\n{context}\n\n"
        full_prompt += f"User Query:\n{prompt}"

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.client.generate_content, full_prompt)
            return {
                "success": True,
                "text": response.text if response and response.text else "",
                "model": "gemini-1.5-flash",
                "raw": response
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "text": ""
            }

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
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
            yield f"[Gemini Unavailable: {res.get('error', 'Unknown Error')}]"
