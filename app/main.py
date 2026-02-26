"""
FastAPI application factory.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, transcribe
from app.api.deps import get_whisper_service
from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    # Pre-load the Whisper model so the first request is not penalised
    svc = get_whisper_service()
    svc.load_model()
    logger.info("Service ready ✓")
    yield
    logger.info("Shutting down.")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred.", "error_code": "INTERNAL_ERROR"},
        )

    # Routers
    app.include_router(health.router)

    # Versioned routes:  /api/v1/transcribe/   /api/v1/transcribe/base64
    app.include_router(transcribe.router, prefix="/api/v1")

    # Convenience (unversioned) routes:  /transcribe/   /transcribe/base64
    app.include_router(transcribe.router, prefix="", include_in_schema=False)

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "transcribe_file":   "POST /transcribe/",
                "transcribe_base64": "POST /transcribe/base64",
                "versioned":         "POST /api/v1/transcribe/",
            },
        }

    return app


app = create_app()
