"""Tests for the dummy backend (used as the always-available fallback)."""

from __future__ import annotations

import numpy as np

from tts_gateway.app.backends.dummy import DummyBackend


def test_dummy_loads_and_synthesizes() -> None:
    backend = DummyBackend(device="cpu")
    backend.load()
    assert backend._loaded
    res = backend.synthesize("Hello world", lang="fr")
    assert isinstance(res.audio, np.ndarray)
    assert res.audio.dtype == np.float32
    assert res.sample_rate == 24000
    assert len(res.audio) > 0


def test_dummy_rejects_unknown_lang() -> None:
    backend = DummyBackend(device="cpu")
    backend.load()
    import pytest
    with pytest.raises(ValueError):
        backend.synthesize("Hello", lang="zh")
