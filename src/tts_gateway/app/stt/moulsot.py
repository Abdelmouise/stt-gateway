"""MoulSot v0.3 STT backend — Moroccan Darija ASR with code-switching.

Wraps the qwen_asr package for offline (non-streaming) transcription.
Requires: pip install qwen-asr
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from tts_gateway.app.stt import (
    STTBackendBase,
    TranscriptionResult,
    register_stt_backend,
)

logger = logging.getLogger(__name__)

# Mapping from our internal lang codes to qwen_asr language names.
_LANG_MAP = {
    "ar_darija": "Arabic",
    "ar": "Arabic",
    "fr": "French",
    "en": "English",
}


@register_stt_backend
class MoulSotBackend(STTBackendBase):
    name = "moulsot"
    supported_langs = frozenset({"ar_darija", "ar", "fr", "en"})

    def load(self) -> None:
        if self._loaded:
            return
        from qwen_asr import Qwen3ASRModel  # noqa: E402 — heavy import deferred

        dtype = "float32" if self.device == "cpu" else "bfloat16"
        logger.info(
            "Loading MoulSot (atlasia/moulsot.v0.3) on %s dtype=%s ...",
            self.device,
            dtype,
        )
        self._model = Qwen3ASRModel.from_pretrained(
            "atlasia/moulsot.v0.3",
            dtype=dtype,
            device_map=self.device,
        )
        self._loaded = True
        logger.info("MoulSot loaded.")

    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        lang: str | None = None,
    ) -> TranscriptionResult:
        if not self._loaded:
            raise RuntimeError("MoulSot model not loaded. Call load() first.")

        if lang is not None:
            self._check_lang(lang)

        # qwen_asr expects a file path; write to a temp file.
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name

            qwen_lang = _LANG_MAP.get(lang) if lang else None
            results = self._model.transcribe(audio=tmp_path, language=qwen_lang)

        # Concatenate all segments in order if results is a list
        if isinstance(results, list):
            text_parts = [r.text for r in results if hasattr(r, 'text') and r.text]
            text = " ".join(text_parts)
            detected_lang = getattr(results[0], "language", None) if results else None
        else:
            text = results.text
            detected_lang = getattr(results, "language", None)

        return TranscriptionResult(text=text, language=detected_lang or lang)
