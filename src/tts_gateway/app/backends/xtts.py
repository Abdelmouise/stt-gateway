"""Coqui XTTS-v2 backend.

License: Coqui Public Model License (NON-COMMERCIAL). Used here as a quality
reference for benchmarking only — do not deploy to production until the
juridical review of CPML for banking use is concluded.

Install: pip install -e ".[xtts]"
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from tts_gateway.app.backends import BackendBase, SynthesisResult, register_backend

if TYPE_CHECKING:  # pragma: no cover
    from TTS.api import TTS as CoquiTTS  # type: ignore[import-not-found]

# XTTS-v2 official supported languages. AR = MSA. Darija is NOT supported.
_XTTS_LANG_MAP = {
    "fr": "fr",
    "en": "en",
    "ar": "ar",
    "ar_msa": "ar",
}


@register_backend
class XttsBackend(BackendBase):
    name = "xtts"
    supported_langs = frozenset(_XTTS_LANG_MAP.keys())
    supports_voice_cloning = True

    MODEL_ID = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        super().__init__(device=device, model_dir=model_dir)
        self._tts: CoquiTTS | None = None

    def load(self) -> None:
        if self._loaded:
            return
        try:
            from TTS.api import TTS as CoquiTTS  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Coqui TTS is not installed. Install with: pip install -e '.[xtts]'"
            ) from exc

        self._tts = CoquiTTS(self.MODEL_ID).to(self.device)
        self._loaded = True

    def synthesize(
        self,
        text: str,
        lang: str,
        voice_ref: Path | None = None,
        speaker_id: str | None = None,
    ) -> SynthesisResult:
        self._check_lang(lang)
        if voice_ref is None:
            raise ValueError("XTTS requires a voice_ref WAV (zero-shot cloning).")
        if not self._loaded or self._tts is None:
            self.load()

        assert self._tts is not None
        wav = self._tts.tts(
            text=text,
            speaker_wav=str(voice_ref),
            language=_XTTS_LANG_MAP[lang],
        )
        audio = np.asarray(wav, dtype=np.float32)
        sr = int(self._tts.synthesizer.output_sample_rate)
        return SynthesisResult(audio=audio, sample_rate=sr)
