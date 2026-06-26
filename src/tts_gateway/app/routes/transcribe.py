"""POST /v1/transcribe — main STT endpoint."""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from tts_gateway.app.audio import convert_m4a_to_wav
from tts_gateway.app.config import Settings, get_settings
from tts_gateway.app.deps import get_stt_backend_dep
from tts_gateway.app.stt import STTBackendBase

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["transcribe"])

_ACCEPTED_CONTENT_TYPES = frozenset({
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/mp4",       # M4A (MPEG-4 Audio)
    "audio/m4a",       # M4A variant
    "audio/x-m4a",     # M4A variant (another MIME type)
    "application/octet-stream",  # allow generic binary
})


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    responses={
        200: {"description": "Transcription result"},
        400: {"description": "Bad request (unsupported lang)"},
        413: {"description": "File too large"},
        415: {"description": "Unsupported audio format"},
        503: {"description": "STT backend not ready"},
    },
)
async def transcribe(
    file: UploadFile,
    stt_backend: Annotated[STTBackendBase, Depends(get_stt_backend_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
    lang: Literal["fr", "en", "ar", "ar_darija"] | None = None,
) -> TranscriptionResponse:
    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in _ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio format: {content_type!r}. Send audio/wav or audio/mp4.",
        )

    # Read and validate size
    audio_bytes = await file.read()
    
    # Convert M4A to WAV if needed
    if content_type in ("audio/mp4", "audio/m4a", "audio/x-m4a"):
        try:
            logger.info("Converting M4A to WAV...")
            audio_bytes = convert_m4a_to_wav(audio_bytes)
            logger.info("M4A conversion successful")
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc
    if len(audio_bytes) > settings.max_audio_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {len(audio_bytes)} exceeds max {settings.max_audio_upload_bytes} bytes.",
        )

    if len(audio_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file.",
        )

    # Validate lang against backend
    if lang is not None and lang not in stt_backend.supported_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"STT backend {stt_backend.name!r} does not support lang={lang!r}",
        )

    try:
        result = stt_backend.transcribe(audio_bytes, lang=lang)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception:
        logger.exception("Transcription failed (backend=%s)", stt_backend.name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed unexpectedly.",
        )

    return TranscriptionResponse(text=result.text, language=result.language)
