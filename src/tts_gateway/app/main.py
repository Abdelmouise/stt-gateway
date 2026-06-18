"""FastAPI entry point.

Usage:
    uvicorn tts_gateway.app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tts_gateway.app.backends import get_backend
from tts_gateway.app.backends.loader import import_all_backends
from tts_gateway.app.config import get_settings
from tts_gateway.app.logging_setup import configure_logging
from tts_gateway.app.metrics import install_metrics
from tts_gateway.app.routes import health, synthesize, voices
from tts_gateway.app.voices import VoiceRegistry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(level=settings.log_level)

    imported = import_all_backends()
    logger.info("Imported backends: %s", imported)

    backend_cls = get_backend(settings.backend)
    backend = backend_cls(device=settings.device, model_dir=settings.model_cache_dir)
    logger.info("Loading backend %s on %s ...", backend.name, backend.device)
    backend.load()
    logger.info("Backend %s loaded.", backend.name)

    voices_registry = VoiceRegistry(voices_dir=settings.voices_dir)

    app.state.backend = backend
    app.state.voices = voices_registry
    app.state.settings = settings

    yield

    # Nothing to release explicitly; GPU memory is freed on process exit.


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TTS Gateway",
        version="0.1.0",
        description="Multilingual TTS service (FR/EN/AR) for the banking virtual assistant.",
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(synthesize.router)
    app.include_router(voices.router)

    install_metrics(app)
    return app


app = create_app()
