import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: Union[bool, str] = True
    APP_NAME: str = "AIT College AI Assistant"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "ait-secret-key-production-replace-in-real-env-must-be-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Database
    DATABASE_URL: str = "sqlite:///./ait_assistant.db"

    # AI Configuration
    GEMINI_API_KEY: str = ""
    AI_DEFAULT_PROVIDER: str = "gemini"
    AI_FALLBACK_PROVIDER: str = "local"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # AIT Source Configuration
    AIT_OFFICIAL_URL: str = "https://www.aitindia.in"
    AIT_COLLEGE_NAME: str = "Ahmedabad Institute of Technology"
    CRAWLER_USER_AGENT: str = "AIT-Assistant-Bot/1.0 (+https://www.aitindia.in)"
    CRAWLER_MAX_PAGES: int = 50
    CRAWLER_DELAY_SECONDS: float = 1.0

    # Voice Configuration
    VOICE_STT_PROVIDER: str = "faster_whisper"
    VOICE_TTS_PROVIDER: str = "piper"
    VOICE_DEFAULT_LANGUAGE: str = "en"
    AUDIO_CACHE_DIR: str = "./voice/audio_cache"

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
    )

settings = Settings()
