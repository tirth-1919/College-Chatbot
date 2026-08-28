from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator

class AIProvider(ABC):
    """Abstract Base Class for AI Model Providers (Gemini, Ollama, Local Neural Models)"""
    
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> Dict[str, Any]:
        """Generate response given prompt and grounded context"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        context: Optional[str] = None,
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """Stream generated response chunks"""
        pass
