import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, validator

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    DEBUG: Union[bool, str] = True
    APP_NAME: str = "AIT College AI Assistant"
    HOST: str = "0.0.0.0"
    PORT: int = 5001
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "ait-secret-key-production-replace-in-real-env-must-be-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REAUTH_TOKEN_EXPIRE_MINUTES: int = 10  # 10 mins for destructive re-auth token

    # Database
    DATABASE_URL: str = "sqlite:///./ait_assistant.db"

    # Redis Configuration
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    CACHE_TTL: int = 3600  # Default cache TTL in seconds

    # AI Configuration
    GEMINI_API_KEY: str = ""
    AI_DEFAULT_PROVIDER: str = "gemini"
    AI_FALLBACK_PROVIDER: str = "local"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # AIT Source Configuration
    AIT_OFFICIAL_BASE_URL: str = "https://www.aitindia.in"
    AIT_OFFICIAL_URL: str = "https://www.aitindia.in"
    AIT_COLLEGE_NAME: str = "Ahmedabad Institute of Technology"
    CRAWLER_USER_AGENT: str = "AIT-Assistant-Bot/1.0 (+https://www.aitindia.in)"
    CRAWLER_MAX_PAGES: int = 50
    CRAWLER_DELAY_SECONDS: float = 1.0

    # Synchronization & Automated ML Pipeline
    KNOWLEDGE_SYNC_ENABLED: bool = True
    KNOWLEDGE_SYNC_INTERVAL_HOURS: int = 24
    INTENT_AUTO_TRAIN_ENABLED: bool = True
    INTENT_RETRAIN_THRESHOLD: int = 10
    INTENT_MIN_ACCURACY: float = 0.85
    INTENT_MIN_F1: float = 0.85
    RAG_AUTO_REINDEX_ENABLED: bool = True

    # Semantic Intent Intelligence
    SEMANTIC_INTENT_ENABLED: bool = True
    SEMANTIC_INTENT_THRESHOLD: float = 0.60
    SEMANTIC_CONTEXT_ENABLED: bool = True
    SEMANTIC_CONTEXT_TTL: int = 1800  # 30 minutes in seconds

    # Voice Configuration
    VOICE_STT_PROVIDER: str = "faster_whisper"
    VOICE_TTS_PROVIDER: str = "piper"
    VOICE_DEFAULT_LANGUAGE: str = "en"
    AUDIO_CACHE_DIR: str = "./voice/audio_cache"
    VAD_ENABLED: bool = True
    VAD_THRESHOLD: float = 0.5
    VAD_MIN_SPEECH_DURATION_MS: int = 250
    VAD_SILENCE_TIMEOUT_MS: int = 800

    # Notification Config - Email (SMTP)
    SMTP_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_SENDER_EMAIL: str = "noreply@aitindia.in"
    SMTP_SENDER_NAME: str = "AIT AI Assistant"

    # Notification Config - SMS (Twilio / Provider)
    SMS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # WhatsApp Meta Business API Config
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "ait_whatsapp_verify_token_secure"
    WHATSAPP_WEBHOOK_SECRET: str = ""

    # ClamAV Antivirus Daemon
    CLAMAV_ENABLED: bool = False
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_TIMEOUT_SECONDS: int = 10
    CLAMAV_FAIL_SAFE: bool = True  # If true and ClamAV down, enforce heuristic fallback scan

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5001/api/v1/auth/google/callback"
    
    # Password Reset Configuration
    PASSWORD_RESET_EXPIRY_MINUTES: int = 60

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
    )

settings = Settings()
