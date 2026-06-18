"""POST /v1/synthesize — main TTS endpoint."""

from __future__ import annotations

import logging
import unicodedata
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from tts_gateway.app.audio import AudioFormat, encode_audio, media_type_for
from tts_gateway.app.backends import BackendBase
from tts_gateway.app.config import Settings, get_settings
from tts_gateway.app.deps import get_backend_dep, get_voices_dep
from tts_gateway.app.voices import VoiceRegistry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["synthesize"])


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    lang: Literal["fr", "en", "ar", "ar_msa", "ar_darija"]
    voice_id: str | None = Field(
        default=None,
        max_length=64,
        description="Brand voice id; falls back to default_voice_id from settings.",
    )
    format: AudioFormat = "wav"
    sample_rate: int | None = Field(default=None, ge=8000, le=48000)

    @field_validator("text")
    @classmethod
    def _normalize_text(cls, v: str) -> str:
        # NFC normalization avoids ambiguous multi-codepoint Arabic forms.
        v = unicodedata.normalize("NFC", v)
        # Strip control characters (keep newlines / tabs).
        v = "".join(ch for ch in v if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
        v = v.strip()
        if not v:
            raise ValueError("text is empty after normalization")
        return v


@router.post(
    "/synthesize",
    response_class=Response,
    responses={
        200: {"content": {"audio/wav": {}}, "description": "Synthesized audio"},
        400: {"description": "Bad request (text/lang/voice)"},
        413: {"description": "Text too long"},
        503: {"description": "Backend not ready"},
    },
)
def synthesize(
    req: SynthesizeRequest,
    backend: Annotated[BackendBase, Depends(get_backend_dep)],
    voices: Annotated[VoiceRegistry, Depends(get_voices_dep)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    if len(req.text) > settings.max_text_length:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"text length {len(req.text)} exceeds max_text_length={settings.max_text_length}",
        )

    if req.lang not in backend.supported_langs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Backend {backend.name!r} does not support lang={req.lang!r}",
        )

    voice_id = req.voice_id or settings.default_voice_id
    voice = voices.get(voice_id)
    if voice is None and backend.supports_voice_cloning and backend.name != "dummy":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown voice_id={voice_id!r}",
        )

    voice_ref = voice.path if voice is not None else None

    try:
        result = backend.synthesize(
            text=req.text,
            lang=req.lang,
            voice_ref=voice_ref,
            speaker_id=voice_id,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception:
        logger.exception("Synthesis failed (backend=%s, lang=%s)", backend.name, req.lang)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Synthesis failed",
        ) from None

    try:
        audio_bytes = encode_audio(result.audio, result.sample_rate, fmt=req.format)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc

    return Response(content=audio_bytes, media_type=media_type_for(req.format))
