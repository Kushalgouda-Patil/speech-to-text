# 🎙️ Voice Assistant — Speech-to-Text Microservice

FastAPI microservice that transcribes audio files to text using
[faster-whisper](https://github.com/SYSTRAN/faster-whisper) (a 4× faster
CTranslate2-based implementation of OpenAI Whisper).

Part of the **AI Voice Assistant** microservices suite.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Whisper models** | `tiny`, `base`, `small`, `medium`, `large`, `large-v2`, `large-v3` |
| **Audio formats** | WAV, MP3, M4A, OGG, FLAC, WebM, MP4 |
| **Upload modes** | Multipart file upload **or** base64-encoded JSON body |
| **Language** | Auto-detect or force via `language` parameter |
| **Timestamps** | Per-segment start/end times + confidence scores |
| **VAD filtering** | Automatically skips silent regions |
| **Non-blocking** | Transcription runs in a thread-pool, event loop stays free |
| **Observability** | Structured logging, `/health` endpoint |
| **Docker ready** | `Dockerfile` + `docker-compose.yml` included |

---

## 🗂️ Project Structure

```
voice-assistant-fastapi/
├── app/
│   ├── main.py                 # FastAPI app factory & lifespan
│   ├── api/
│   │   ├── deps.py             # FastAPI DI helpers
│   │   ├── health.py           # GET /health, GET /models
│   │   └── transcribe.py       # POST /api/v1/transcribe/
│   │                           # POST /api/v1/transcribe/base64
│   ├── core/
│   │   ├── config.py           # Settings (Pydantic Settings)
│   │   └── logging.py          # Logging setup
│   ├── models/
│   │   └── transcription.py    # Pydantic request/response schemas
│   └── services/
│       └── whisper_service.py  # Whisper model wrapper
├── tests/
│   └── test_transcription.py
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## 🚀 Quick Start (Local)

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
# macOS – also install ffmpeg (required for audio decoding):
brew install ffmpeg
```

> **Apple Silicon (M1/M2/M3)** — set `WHISPER_DEVICE=mps` in `.env` for GPU acceleration.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env as needed (model, device, etc.)
```

### 4. Run the server

```bash
# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Development (auto-reload)
make dev
```

The service boots, downloads the selected Whisper model on first run, and is ready at **http://localhost:8000**.

- Swagger UI → http://localhost:8000/docs  
- ReDoc → http://localhost:8000/redoc  
- Health → http://localhost:8000/health

---

## 🐳 Docker

```bash
# Build & start
make docker-up

# Tear down
make docker-down
```

Model weights are persisted in a named Docker volume (`whisper_cache`) so they
are not re-downloaded on restart.

---

## 📡 API Reference

### `POST /api/v1/transcribe/` — Upload audio file

**Request** — `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `audio` | `File` | ✅ | Audio file (WAV/MP3/M4A/OGG/FLAC/WebM/MP4) |
| `language` | `string` | ❌ | BCP-47 code (`en`, `fr`, `hi` …). Omit for auto-detect. |

**cURL example**

```bash
curl -X POST http://localhost:8000/api/v1/transcribe/ \
     -F "audio=@recording.wav" \
     -F "language=en"
```

**Response** `200 OK`

```json
{
  "text": "Hello, how can I help you today?",
  "language": "en",
  "duration": 3.52,
  "model": "base",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 3.52,
      "text": "Hello, how can I help you today?",
      "avg_logprob": -0.312,
      "no_speech_prob": 0.004
    }
  ]
}
```

---

### `POST /api/v1/transcribe/base64` — Base64 JSON payload

Useful for callers that cannot send multipart (IoT devices, WebSocket bridges, etc.).

```bash
curl -X POST http://localhost:8000/api/v1/transcribe/base64 \
     -H "Content-Type: application/json" \
     -d '{
       "audio_base64": "<base64-encoded bytes>",
       "filename": "recording.wav",
       "language": "en"
     }'
```

---

### `GET /health`

```json
{ "status": "ok", "model_loaded": true, "whisper_model": "base", "version": "1.0.0" }
```

### `GET /models`

Returns the list of all supported Whisper model variants and descriptions.

---

## ⚙️ Configuration

All settings are controlled via environment variables (or `.env` file).

| Variable | Default | Description |
|---|---|---|
| `WHISPER_MODEL` | `base` | Model variant to load |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda`, or `mps` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` |
| `WHISPER_LANGUAGE` | _(auto)_ | Force a language globally |
| `MAX_UPLOAD_SIZE_MB` | `25` | Max audio file size |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `ALLOWED_ORIGINS` | `["*"]` | CORS allowed origins |

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
make test
```

---

## 🔮 Integration with other microservices

This service is designed to be called by other services in the AI Voice
Assistant pipeline, e.g.:

```
Microphone / Client
      │  audio bytes
      ▼
┌──────────────────────┐
│  STT Microservice    │  ← you are here
│  (this repo)         │
└──────────┬───────────┘
           │  transcribed text (JSON)
           ▼
┌──────────────────────┐
│  LLM / NLU Service   │
└──────────┬───────────┘
           │  response text
           ▼
┌──────────────────────┐
│  TTS Microservice    │
└──────────────────────┘
```
