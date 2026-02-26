"""
Health & info endpoints.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_whisper_service
from app.core.config import get_settings
from app.models.transcription import HealthResponse, WhisperModel
from app.services.whisper_service import WhisperService

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns service health status and whether the Whisper model is loaded.",
)
def health_check(
    whisper_service: WhisperService = Depends(get_whisper_service),
) -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_loaded=whisper_service.is_loaded,
        whisper_model=whisper_service.model_name,
        version=settings.APP_VERSION,
    )


@router.get(
    "/models",
    summary="List available Whisper models",
    description="Returns the list of supported Whisper model variants.",
)
def list_models() -> dict:
    return {
        "models": [m.value for m in WhisperModel],
        "current_model": settings.WHISPER_MODEL,
        "description": {
            "tiny": "Fastest, least accurate (~39M parameters)",
            "base": "Good balance of speed and accuracy (~74M parameters)",
            "small": "Better accuracy, still fast (~244M parameters)",
            "medium": "High accuracy (~769M parameters)",
            "large": "Best accuracy, slowest (~1550M parameters)",
            "large-v2": "Improved large model (recommended for production)",
            "large-v3": "Latest large model with best overall performance",
        },
    }
