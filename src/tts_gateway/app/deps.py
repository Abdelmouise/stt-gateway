"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status

from tts_gateway.app.backends import BackendBase
from tts_gateway.app.config import Settings, get_settings
from tts_gateway.app.voices import VoiceRegistry


def get_backend_dep(request: Request) -> BackendBase:
    backend = getattr(request.app.state, "backend", None)
    if backend is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Backend not initialized",
        )
    return backend


def get_voices_dep(request: Request) -> VoiceRegistry:
    voices = getattr(request.app.state, "voices", None)
    if voices is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice registry not initialized",
        )
    return voices


def require_admin(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.admin_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are disabled (TTS_ADMIN_API_KEY not set)",
        )
    expected = f"Bearer {settings.admin_api_key}"
    if authorization != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
