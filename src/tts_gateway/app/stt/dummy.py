"""Dummy STT backend — returns hardcoded transcription.

Used by tests and as a no-op fallback when no real STT model is loaded.
"""

from __future__ import annotations

from tts_gateway.app.stt import (
    SUPPORTED_STT_LANGS,
    STTBackendBase,
    TranscriptionResult,
    register_stt_backend,
)


@register_stt_backend
class DummySTTBackend(STTBackendBase):
    name = "dummy"
    supported_langs = frozenset(SUPPORTED_STT_LANGS)

    def load(self) -> None:
        self._loaded = True

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        lang: str | None = None,
    ) -> TranscriptionResult:
        if lang is not None:
            self._check_lang(lang)
        return TranscriptionResult(
            text="هذا نص تجريبي",
            language=lang or "ar_darija",
        )
