"""Dummy backend — generates a silent waveform.

Used by tests and as a no-op fallback when no real backend is loaded.
Matches the BackendBase interface so the FastAPI service is fully functional
even before a real model is integrated.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tts_gateway.app.backends import (
    SUPPORTED_LANGS,
    BackendBase,
    SynthesisResult,
    register_backend,
)


@register_backend
class DummyBackend(BackendBase):
    name = "dummy"
    supported_langs = frozenset(SUPPORTED_LANGS)
    supports_voice_cloning = True  # ignores ref but accepts the param

    SAMPLE_RATE = 24000

    def load(self) -> None:
        self._loaded = True

    def synthesize(
        self,
        text: str,
        lang: str,
        voice_ref: Path | None = None,
        speaker_id: str | None = None,
    ) -> SynthesisResult:
        self._check_lang(lang)
        # ~80 ms per word as a rough placeholder duration
        n_words = max(1, len(text.split()))
        duration_s = 0.4 + 0.08 * n_words
        n_samples = int(duration_s * self.SAMPLE_RATE)
        # Very quiet sine so the audio is not strictly silent (helps bench tooling)
        t = np.linspace(0.0, duration_s, n_samples, endpoint=False, dtype=np.float32)
        audio = 0.001 * np.sin(2 * np.pi * 220.0 * t).astype(np.float32)
        return SynthesisResult(audio=audio, sample_rate=self.SAMPLE_RATE)
