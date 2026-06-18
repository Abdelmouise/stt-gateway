"""GET / POST /v1/voices — brand-voice management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from tts_gateway.app.deps import get_voices_dep, require_admin
from tts_gateway.app.voices import VoiceRegistry

router = APIRouter(prefix="/v1/voices", tags=["voices"])


class VoiceInfo(BaseModel):
    voice_id: str
    description: str | None = None


@router.get("", response_model=list[VoiceInfo])
def list_voices(
    voices: Annotated[VoiceRegistry, Depends(get_voices_dep)],
) -> list[VoiceInfo]:
    return [VoiceInfo(voice_id=v.voice_id, description=v.description) for v in voices.list()]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VoiceInfo,
    dependencies=[Depends(require_admin)],
)
async def upload_voice(
    voices: Annotated[VoiceRegistry, Depends(get_voices_dep)],
    voice_id: Annotated[str, Form(min_length=1, max_length=64)],
    file: Annotated[UploadFile, File(description="WAV reference, 6-10s, 24kHz mono recommended")],
) -> VoiceInfo:
    if file.content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Expected audio/wav, got {file.content_type!r}",
        )
    data = await file.read()
    # 50 MB cap to keep upload sane.
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="WAV reference too large (>50MB)",
        )
    try:
        voice = voices.add(voice_id, data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return VoiceInfo(voice_id=voice.voice_id)
