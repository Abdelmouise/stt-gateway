"""Pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests use a fresh, deterministic config in a temp dir."""
    monkeypatch.setenv("TTS_BACKEND", "dummy")
    monkeypatch.setenv("TTS_DEVICE", "cpu")
    monkeypatch.setenv("TTS_VOICES_DIR", str(tmp_path / "voices"))
    monkeypatch.setenv("TTS_MODEL_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("TTS_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("TTS_STT_BACKEND", "dummy")
    monkeypatch.setenv("TTS_STT_DEVICE", "cpu")
    monkeypatch.delenv("TTS_ADMIN_API_KEY", raising=False)
    # Force re-evaluation of the cached settings singleton.
    import tts_gateway.app.config as cfg
    cfg._settings = None
    yield
    cfg._settings = None
