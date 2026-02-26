"""
Configuration management using Pydantic Settings.
Values can be overridden via environment variables or a .env file.
"""
import warnings
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# faster-whisper (CTranslate2) only supports these devices
_SUPPORTED_DEVICES = {"cpu", "cuda"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────
    APP_NAME: str = "Voice Assistant – Speech-to-Text Service"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Microservice that transcribes audio files to text using OpenAI Whisper. "
        "Part of the AI Voice Assistant backend."
    )
    DEBUG: bool = False

    # ── Server ────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Whisper ───────────────────────────────────────────────────────
    # Choices: tiny, base, small, medium, large, large-v2, large-v3
    WHISPER_MODEL: Literal[
        "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
    ] = "base"
    WHISPER_DEVICE: str = "cpu"   # "cpu" | "cuda"  (mps is NOT supported by faster-whisper)
    WHISPER_COMPUTE_TYPE: str = "int8"  # "int8" | "float16" | "float32"
    WHISPER_LANGUAGE: str | None = None  # None → auto-detect

    @field_validator("WHISPER_DEVICE", mode="before")
    @classmethod
    def validate_device(cls, v: str) -> str:
        device = str(v).strip().lower()
        if device not in _SUPPORTED_DEVICES:
            warnings.warn(
                f"WHISPER_DEVICE='{v}' is not supported by faster-whisper (CTranslate2). "
                f"Supported devices: {sorted(_SUPPORTED_DEVICES)}. "
                "Falling back to 'cpu'.",
                stacklevel=2,
            )
            return "cpu"
        return device

    # ── Upload limits ─────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 25  # max audio file size in MB

    # ── CORS ──────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── Logging ───────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
