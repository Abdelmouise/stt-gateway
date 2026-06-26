"""Unit tests for the DummySTTBackend."""

from __future__ import annotations

import io
import struct

import numpy as np

from tts_gateway.app.stt.dummy import DummySTTBackend


def _make_wav_bytes() -> bytes:
    """Generate minimal WAV bytes."""
    samples = np.zeros(1600, dtype=np.int16)
    pcm_data = samples.tobytes()
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm_data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<H", 1))
    buf.write(struct.pack("<I", 16000))
    buf.write(struct.pack("<I", 32000))
    buf.write(struct.pack("<H", 2))
    buf.write(struct.pack("<H", 16))
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm_data)))
    buf.write(pcm_data)
    return buf.getvalue()


class TestDummySTTBackend:
    def test_load(self) -> None:
        backend = DummySTTBackend()
        backend.load()
        assert backend._loaded is True

    def test_transcribe_returns_result(self) -> None:
        backend = DummySTTBackend()
        backend.load()
        result = backend.transcribe(_make_wav_bytes())
        assert result.text
        assert result.language == "ar_darija"

    def test_transcribe_with_lang_hint(self) -> None:
        backend = DummySTTBackend()
        backend.load()
        result = backend.transcribe(_make_wav_bytes(), lang="fr")
        assert result.language == "fr"

    def test_transcribe_unsupported_lang_raises(self) -> None:
        backend = DummySTTBackend()
        backend.load()
        import pytest
        with pytest.raises(ValueError, match="does not support"):
            backend.transcribe(_make_wav_bytes(), lang="zh")
