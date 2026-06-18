"""Audio encoding helpers (WAV / MP3 / Opus).

Keep this minimal: WAV via stdlib + soundfile; MP3/Opus require ffmpeg or
extra libs and are stubbed for now (raise 415 to the caller).
"""

from __future__ import annotations

import io
from typing import Literal

import numpy as np
import soundfile as sf

AudioFormat = Literal["wav", "mp3", "opus"]


def encode_audio(audio: np.ndarray, sample_rate: int, fmt: AudioFormat = "wav") -> bytes:
    """Encode a float32 mono waveform to the requested container."""
    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    # Clip to avoid hard saturation surprises on malformed model outputs.
    audio = np.clip(audio, -1.0, 1.0)

    if fmt == "wav":
        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()

    if fmt in ("mp3", "opus"):
        # Deferred to Phase 2 — wire up via ffmpeg or pyav once formats matter.
        raise NotImplementedError(
            f"Audio format {fmt!r} not yet supported. Use 'wav' for now."
        )

    raise ValueError(f"Unsupported audio format: {fmt!r}")


def media_type_for(fmt: AudioFormat) -> str:
    return {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "opus": "audio/ogg",
    }[fmt]
