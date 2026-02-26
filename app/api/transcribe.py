"""
Transcription router — core speech-to-text endpoints.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_whisper_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.transcription import TranscriptionResponse, WhisperModel
from app.services.whisper_service import SUPPORTED_AUDIO_TYPES, WhisperService

router = APIRouter(prefix="/transcribe", tags=["Transcription"])
logger = get_logger(__name__)
settings = get_settings()

_MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes


def _validate_audio_file(file: UploadFile) -> None:
    """Raise HTTPException for unsupported content type."""
    ct = (file.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in SUPPORTED_AUDIO_TYPES:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_TYPES))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type '{ct}'. Supported: {supported}",
        )


# ── POST /transcribe ─────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=TranscriptionResponse,
    summary="Transcribe an audio file",
    description=(
        "Upload an audio file (WAV, MP3, M4A, OGG, FLAC, WebM, MP4) and receive "
        "the transcribed text along with per-segment timestamps and metadata."
    ),
    response_description="Transcription result with full text and timestamped segments.",
)
async def transcribe_audio(
    audio: Annotated[
        UploadFile,
        File(description="Audio file to transcribe (max 25 MB by default)"),
    ],
    language: Annotated[
        str | None,
        Form(
            description=(
                "BCP-47 language code to force (e.g. 'en', 'fr', 'hi'). "
                "Leave empty for automatic language detection."
            )
        ),
    ] = None,
    whisper_service: WhisperService = Depends(get_whisper_service),
) -> TranscriptionResponse:
    _validate_audio_file(audio)

    # Read and size-check
    file_bytes = await audio.read()
    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed size is {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info(
        "Received audio | filename=%s size=%d bytes language=%s",
        audio.filename,
        len(file_bytes),
        language or "auto",
    )

    result = await whisper_service.transcribe_file(
        file_bytes=file_bytes,
        filename=audio.filename or "audio.wav",
        language=language,
    )
    return result


# ── POST /transcribe/base64 ──────────────────────────────────────────────────

import base64  # noqa: E402 – kept near usage


@router.post(
    "/base64",
    response_model=TranscriptionResponse,
    summary="Transcribe a base64-encoded audio payload",
    description=(
        "Send audio as a base64-encoded JSON body. Useful when the caller cannot "
        "send multipart/form-data (e.g. certain IoT devices or WebSocket bridges)."
    ),
)
async def transcribe_base64(
    payload: dict,
    whisper_service: WhisperService = Depends(get_whisper_service),
) -> TranscriptionResponse:
    """
    Expected body:
    ```json
    {
      "audio_base64": "<base64-encoded bytes>",
      "filename": "recording.wav",
      "language": "en"
    }
    ```
    """
    audio_b64: str | None = payload.get("audio_base64")
    if not audio_b64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'audio_base64' field is required.",
        )
    try:
        file_bytes = base64.b64decode(audio_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 encoding in 'audio_base64'.",
        )

    if len(file_bytes) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Decoded audio too large. Maximum: {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    filename: str = payload.get("filename", "audio.wav")
    language: str | None = payload.get("language")

    logger.info(
        "Received base64 audio | filename=%s size=%d bytes language=%s",
        filename,
        len(file_bytes),
        language or "auto",
    )

    return await whisper_service.transcribe_file(
        file_bytes=file_bytes,
        filename=filename,
        language=language,
    )
