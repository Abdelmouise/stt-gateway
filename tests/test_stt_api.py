"""E2E tests for the STT /v1/transcribe endpoint."""

from __future__ import annotations

import io
import struct

import pytest
from fastapi.testclient import TestClient

from tts_gateway.app.main import create_app


def _make_wav_bytes(duration_s: float = 0.1, sample_rate: int = 16000) -> bytes:
    """Generate a minimal valid WAV file (silence) in memory."""
    import numpy as np

    n_samples = int(duration_s * sample_rate)
    samples = np.zeros(n_samples, dtype=np.int16)
    pcm_data = samples.tobytes()

    # WAV header (44 bytes)
    buf = io.BytesIO()
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + len(pcm_data)))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))  # chunk size
    buf.write(struct.pack("<H", 1))  # PCM format
    buf.write(struct.pack("<H", 1))  # mono
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", sample_rate * 2))  # byte rate
    buf.write(struct.pack("<H", 2))  # block align
    buf.write(struct.pack("<H", 16))  # bits per sample
    buf.write(b"data")
    buf.write(struct.pack("<I", len(pcm_data)))
    buf.write(pcm_data)
    return buf.getvalue()


@pytest.fixture()
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestTranscribeEndpoint:
    def test_transcribe_ok(self, client: TestClient) -> None:
        wav = _make_wav_bytes()
        resp = client.post(
            "/v1/transcribe",
            files={"file": ("test.wav", wav, "audio/wav")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "text" in body
        assert body["text"]  # non-empty
        assert "language" in body

    def test_transcribe_with_lang_hint(self, client: TestClient) -> None:
        wav = _make_wav_bytes()
        resp = client.post(
            "/v1/transcribe?lang=fr",
            files={"file": ("test.wav", wav, "audio/wav")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["language"] == "fr"

    def test_transcribe_unsupported_format(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/transcribe",
            files={"file": ("test.mp3", b"fake mp3 content", "audio/mpeg")},
        )
        assert resp.status_code == 415

    def test_transcribe_empty_file(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/transcribe",
            files={"file": ("test.wav", b"", "audio/wav")},
        )
        assert resp.status_code == 400

    def test_transcribe_no_file(self, client: TestClient) -> None:
        resp = client.post("/v1/transcribe")
        assert resp.status_code == 422
