"""
Dependency injection helpers shared across routers.
"""
from functools import lru_cache

from app.services.whisper_service import WhisperService


@lru_cache(maxsize=1)
def get_whisper_service() -> WhisperService:
    """Return the singleton WhisperService instance."""
    return WhisperService()
