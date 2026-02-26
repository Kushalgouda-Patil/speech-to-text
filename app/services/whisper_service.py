"""
WhisperService — wraps faster-whisper for efficient audio transcription.

Uses faster-whisper (CTranslate2 backend) which is 4× faster than the
original OpenAI Whisper with the same accuracy and a much smaller memory
footprint.
"""
import asyncio
import io
import os
import tempfile
import time
from pathlib import Path
from typing import BinaryIO

from faster_whisper import WhisperModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.transcription import TranscriptionResponse, TranscriptionSegment

logger = get_logger(__name__)

# Supported audio MIME types → file extension
SUPPORTED_AUDIO_TYPES: dict[str, str] = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".mp4",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "video/mp4": ".mp4",
}


class WhisperService:
    """Singleton-style service that loads and caches the Whisper model."""

    _model: WhisperModel | None = None
    _model_name: str | None = None

    def __init__(self) -> None:
        self._settings = get_settings()

    # ── Model lifecycle ───────────────────────────────────────────────

    def load_model(self) -> None:
        """Load the Whisper model into memory (called once at startup)."""
        model_name = self._settings.WHISPER_MODEL
        device = self._settings.WHISPER_DEVICE
        compute_type = self._settings.WHISPER_COMPUTE_TYPE

        logger.info(
            "Loading Whisper model '%s' on device='%s' compute_type='%s' …",
            model_name,
            device,
            compute_type,
        )
        t0 = time.perf_counter()
        WhisperService._model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
        )
        WhisperService._model_name = model_name
        elapsed = time.perf_counter() - t0
        logger.info("Whisper model loaded in %.2f s", elapsed)

    @property
    def is_loaded(self) -> bool:
        return WhisperService._model is not None

    @property
    def model_name(self) -> str:
        return WhisperService._model_name or self._settings.WHISPER_MODEL

    # ── Transcription ─────────────────────────────────────────────────

    async def transcribe_file(
        self,
        file_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResponse:
        """
        Async wrapper — runs blocking transcription in a thread-pool executor
        so the FastAPI event loop is never blocked.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._transcribe_sync,
            file_bytes,
            filename,
            language,
        )

    def _transcribe_sync(
        self,
        file_bytes: bytes,
        filename: str,
        language: str | None,
    ) -> TranscriptionResponse:
        if WhisperService._model is None:
            raise RuntimeError("Whisper model is not loaded yet.")

        settings = self._settings

        # Determine file extension from original filename
        suffix = Path(filename).suffix or ".wav"

        # Write bytes to a named temp file (whisper needs a filesystem path)
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            t0 = time.perf_counter()
            forced_lang = language or settings.WHISPER_LANGUAGE

            segments_iter, info = WhisperService._model.transcribe(
                tmp_path,
                language=forced_lang,
                beam_size=5,
                vad_filter=True,          # skip silent regions
                vad_parameters=dict(min_silence_duration_ms=500),
                word_timestamps=False,
            )

            segments: list[TranscriptionSegment] = []
            full_text_parts: list[str] = []

            for seg in segments_iter:
                segments.append(
                    TranscriptionSegment(
                        id=seg.id,
                        start=round(seg.start, 3),
                        end=round(seg.end, 3),
                        text=seg.text.strip(),
                        avg_logprob=round(seg.avg_logprob, 4),
                        no_speech_prob=round(seg.no_speech_prob, 4),
                    )
                )
                full_text_parts.append(seg.text.strip())

            elapsed = time.perf_counter() - t0
            full_text = " ".join(full_text_parts)

            logger.info(
                "Transcription done | lang=%s duration=%.1fs segments=%d elapsed=%.2fs",
                info.language,
                info.duration,
                len(segments),
                elapsed,
            )

            return TranscriptionResponse(
                text=full_text,
                language=info.language,
                duration=round(info.duration, 3),
                model=self.model_name,
                segments=segments,
            )
        finally:
            os.unlink(tmp_path)
