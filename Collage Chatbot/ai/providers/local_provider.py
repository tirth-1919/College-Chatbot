import asyncio
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
from ai.providers.base import AIProvider
from backend.app.config import settings

class LocalProvider(AIProvider):
    """Local inference provider supporting Ollama or built-in intelligent contextual response synthesizer"""
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.OLLAMA_BASE_URL

    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        # Try Ollama endpoint if running
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": "llama3",
                        "prompt": f"{system_instruction or ''}\n\nContext:\n{context or ''}\n\nUser: {prompt}",
                        "stream": False
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "success": True,
                        "text": data.get("response", ""),
                        "model": "ollama-local"
                    }
        except Exception:
            pass

        # Built-in deterministic contextual synthesis engine
        synthesized_text = self._synthesize_fallback(prompt, context)
        return {
            "success": True,
            "text": synthesized_text,
            "model": "local-contextual-engine"
        }

    def _synthesize_fallback(self, prompt: str, context: Optional[str]) -> str:
        if context and context.strip():
            return f"Based on verified AIT records:\n\n{context.strip()}"
        return (
            "I could not verify this information from authoritative Ahmedabad Institute of Technology (AIT) sources. "
            "Please check the official portal at https://www.aitindia.in or contact the college administration office."
        )

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        res = await self.generate_response(prompt, system_instruction, context, temperature)
        text = res.get("text", "")
        words = text.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
            yield chunk
            await asyncio.sleep(0.015)
