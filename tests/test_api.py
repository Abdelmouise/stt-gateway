"""End-to-end tests of the FastAPI app using the dummy backend."""

from __future__ import annotations

import io

import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from tts_gateway.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "dummy"
    assert "fr" in body["supported_langs"]


def test_synthesize_returns_wav(client: TestClient) -> None:
    r = client.post(
        "/v1/synthesize",
        json={"text": "Bonjour, votre solde est de 100 euros.", "lang": "fr"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "audio/wav"
    audio, sr = sf.read(io.BytesIO(r.content))
    assert sr == 24000
    assert len(audio) > 0


def test_synthesize_rejects_empty_text(client: TestClient) -> None:
    r = client.post("/v1/synthesize", json={"text": "   ", "lang": "fr"})
    assert r.status_code == 422


def test_synthesize_rejects_unknown_lang(client: TestClient) -> None:
    r = client.post("/v1/synthesize", json={"text": "Hello", "lang": "zh"})
    assert r.status_code == 422


def test_list_voices_empty(client: TestClient) -> None:
    r = client.get("/v1/voices")
    assert r.status_code == 200
    assert r.json() == []


def test_admin_disabled_by_default(client: TestClient) -> None:
    r = client.post(
        "/v1/voices",
        data={"voice_id": "test"},
        files={"file": ("test.wav", b"RIFF\x00\x00\x00\x00WAVE", "audio/wav")},
    )
    # Admin key not set in test env -> 503
    assert r.status_code == 503
