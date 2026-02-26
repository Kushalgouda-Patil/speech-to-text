"""
Pydantic response/request models for the transcription endpoints.
"""
from enum import Enum

from pydantic import BaseModel, Field


class WhisperModel(str, Enum):
    tiny = "tiny"
    base = "base"
    small = "small"
    medium = "medium"
    large = "large"
    large_v2 = "large-v2"
    large_v3 = "large-v3"


class TranscriptionSegment(BaseModel):
    id: int = Field(..., description="Segment index (0-based)")
    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    avg_logprob: float = Field(..., description="Average log-probability (confidence proxy)")
    no_speech_prob: float = Field(..., description="Probability that this segment is silence/noise")


class TranscriptionResponse(BaseModel):
    text: str = Field(..., description="Full transcribed text (all segments joined)")
    language: str = Field(..., description="Detected (or forced) language code, e.g. 'en'")
    duration: float = Field(..., description="Audio duration in seconds")
    model: str = Field(..., description="Whisper model variant used")
    segments: list[TranscriptionSegment] = Field(
        default_factory=list,
        description="Per-segment transcription data (timestamps, confidence, etc.)",
    )


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    whisper_model: str
    version: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
