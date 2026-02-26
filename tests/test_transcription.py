"""
Integration tests for the STT microservice.
Run with:  pytest tests/ -v
"""
import io
import struct
import wave

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _make_silent_wav(duration_s: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Create a minimal silent WAV file in-memory for testing."""
    n_samples = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)       # mono
        wf.setsampwidth(2)       # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_samples)
    return buf.getvalue()


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "model_loaded" in data
        assert "whisper_model" in data

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "service" in r.json()

    def test_models_list(self, client):
        r = client.get("/models")
        assert r.status_code == 200
        body = r.json()
        assert "models" in body
        assert "tiny" in body["models"]


# ── Transcription ─────────────────────────────────────────────────────────────

class TestTranscription:
    def test_transcribe_silent_wav(self, client):
        wav_bytes = _make_silent_wav()
        r = client.post(
            "/api/v1/transcribe/",
            files={"audio": ("test.wav", wav_bytes, "audio/wav")},
        )
        assert r.status_code == 200
        body = r.json()
        assert "text" in body
        assert "language" in body
        assert "duration" in body
        assert isinstance(body["segments"], list)

    def test_transcribe_empty_file(self, client):
        r = client.post(
            "/api/v1/transcribe/",
            files={"audio": ("empty.wav", b"", "audio/wav")},
        )
        assert r.status_code == 400

    def test_transcribe_unsupported_type(self, client):
        r = client.post(
            "/api/v1/transcribe/",
            files={"audio": ("file.pdf", b"%PDF", "application/pdf")},
        )
        assert r.status_code == 415

    def test_transcribe_base64(self, client):
        import base64
        wav_bytes = _make_silent_wav()
        payload = {
            "audio_base64": base64.b64encode(wav_bytes).decode(),
            "filename": "test.wav",
        }
        r = client.post("/api/v1/transcribe/base64", json=payload)
        assert r.status_code == 200
        body = r.json()
        assert "text" in body

    def test_transcribe_base64_missing_field(self, client):
        r = client.post("/api/v1/transcribe/base64", json={})
        assert r.status_code == 400

    def test_transcribe_base64_invalid_encoding(self, client):
        r = client.post(
            "/api/v1/transcribe/base64",
            json={"audio_base64": "!!!not-valid-base64!!!"},
        )
        assert r.status_code == 400
