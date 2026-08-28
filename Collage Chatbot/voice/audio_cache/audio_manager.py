import os
import hashlib
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import VoiceAsset
from backend.app.config import settings

class AudioCacheManager:
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or settings.AUDIO_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def get_cached_asset(self, db: Session, text: str, language: str = "en") -> Optional[VoiceAsset]:
        # Hash normalized text
        norm_text = text.strip().lower()
        content_hash = hashlib.sha256(f"{norm_text}:{language}".encode("utf-8")).hexdigest()
        filename = f"{content_hash}.wav"
        file_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(file_path):
            asset = db.query(VoiceAsset).filter(VoiceAsset.file_path == file_path).first()
            if asset:
                return asset
        return None

    def save_audio_asset(self, db: Session, text: str, audio_bytes: bytes, language: str = "en") -> VoiceAsset:
        norm_text = text.strip().lower()
        content_hash = hashlib.sha256(f"{norm_text}:{language}".encode("utf-8")).hexdigest()
        filename = f"{content_hash}.wav"
        file_path = os.path.join(self.cache_dir, filename)

        with open(file_path, "wb") as f:
            f.write(audio_bytes)

        asset = VoiceAsset(
            text_content=text,
            language=language,
            audio_format="wav",
            file_path=file_path,
            duration_seconds=max(1.0, len(text.split()) * 0.3)
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset
