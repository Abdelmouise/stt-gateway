"""Tests for audio encoding helpers."""

from __future__ import annotations

import io

import numpy as np
import pytest
import soundfile as sf

from tts_gateway.app.audio import encode_audio, media_type_for


def test_encode_wav_roundtrip() -> None:
    sr = 16000
    audio = np.sin(np.linspace(0, 2 * np.pi * 440, sr // 2, dtype=np.float32))
    blob = encode_audio(audio, sample_rate=sr, fmt="wav")
    assert blob[:4] == b"RIFF"
    decoded, sr_back = sf.read(io.BytesIO(blob))
    assert sr_back == sr
    assert len(decoded) == len(audio)


def test_encode_clips_overshoot() -> None:
    audio = np.array([2.0, -2.0, 0.5, -0.5], dtype=np.float32)
    blob = encode_audio(audio, sample_rate=16000, fmt="wav")
    decoded, _ = sf.read(io.BytesIO(blob))
    assert decoded.max() <= 1.0
    assert decoded.min() >= -1.0


def test_unsupported_formats_raise() -> None:
    audio = np.zeros(100, dtype=np.float32)
    with pytest.raises(NotImplementedError):
        encode_audio(audio, 16000, fmt="mp3")
    with pytest.raises(NotImplementedError):
        encode_audio(audio, 16000, fmt="opus")


def test_media_types() -> None:
    assert media_type_for("wav") == "audio/wav"
    assert media_type_for("mp3") == "audio/mpeg"
    assert media_type_for("opus") == "audio/ogg"
