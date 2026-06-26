"""Audio encoding helpers (WAV / MP3 / Opus).

Keep this minimal: WAV via stdlib + soundfile; MP3/Opus require ffmpeg or
extra libs and are stubbed for now (raise 415 to the caller).
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
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


def convert_m4a_to_wav(m4a_bytes: bytes) -> bytes:
    """Convert M4A audio bytes to WAV format using ffmpeg.
    
    Args:
        m4a_bytes: Audio data in M4A format (raw bytes)
        
    Returns:
        Audio data in WAV format (raw bytes)
        
    Raises:
        RuntimeError: If ffmpeg is not installed or conversion fails
    """
    tmp_m4a_path = None
    tmp_wav_path = None
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".m4a", delete=False) as tmp_m4a:
            tmp_m4a.write(m4a_bytes)
            tmp_m4a_path = tmp_m4a.name

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            tmp_wav_path = tmp_wav.name

        # Convert M4A to WAV using ffmpeg
        subprocess.run(
            [
                "ffmpeg",
                "-i", tmp_m4a_path,
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y",
                tmp_wav_path,
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )

        with open(tmp_wav_path, "rb") as f:
            wav_bytes = f.read()

        return wav_bytes
    except FileNotFoundError as e:
        raise RuntimeError(
            "ffmpeg not found. Install ffmpeg to support M4A audio conversion. "
            "On macOS: brew install ffmpeg; On Ubuntu: apt-get install ffmpeg"
        ) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"ffmpeg conversion failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
        ) from e
    finally:
        # Clean up temp files
        if tmp_m4a_path and os.path.exists(tmp_m4a_path):
            try:
                os.unlink(tmp_m4a_path)
            except OSError:
                pass
        if tmp_wav_path and os.path.exists(tmp_wav_path):
            try:
                os.unlink(tmp_wav_path)
            except OSError:
                pass
