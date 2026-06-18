"""Chatterbox Multilingual backend (Resemble AI).

License: MIT — primary commercial target.
Multilingual support is being expanded; AR support must be empirically
validated as part of the POC.

Install: pip install -e ".[chatterbox]"
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from tts_gateway.app.backends import BackendBase, SynthesisResult, register_backend

if TYPE_CHECKING:  # pragma: no cover
    from chatterbox.tts import ChatterboxTTS  # type: ignore[import-not-found]

# Conservative initial map. Update once we confirm the AR coverage of the
# specific Chatterbox checkpoint we use during the POC.
_LANG_MAP = {
    "fr": "fr",
    "en": "en",
    "ar": "ar",
    "ar_msa": "ar",
}


@register_backend
class ChatterboxBackend(BackendBase):
    name = "chatterbox"
    supported_langs = frozenset(_LANG_MAP.keys())
    supports_voice_cloning = True

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        super().__init__(device=device, model_dir=model_dir)
        self._tts: ChatterboxTTS | None = None

    def load(self) -> None:
        if self._loaded:
            return
        try:
            from chatterbox.tts import ChatterboxTTS  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "chatterbox-tts is not installed. Install with: pip install -e '.[chatterbox]'"
            ) from exc

        self._tts = ChatterboxTTS.from_pretrained(device=self.device)
        self._loaded = True

    def synthesize(
        self,
        text: str,
        lang: str,
        voice_ref: Path | None = None,
        speaker_id: str | None = None,
    ) -> SynthesisResult:
        self._check_lang(lang)
        if not self._loaded or self._tts is None:
            self.load()
        assert self._tts is not None

        kwargs: dict = {}
        if voice_ref is not None:
            kwargs["audio_prompt_path"] = str(voice_ref)
        # The Chatterbox API surface evolves; this call site is the integration
        # point to adapt during the POC if the signature differs.
        wav = self._tts.generate(text=text, language_id=_LANG_MAP[lang], **kwargs)
        audio = np.asarray(wav, dtype=np.float32).squeeze()
        sr = int(getattr(self._tts, "sr", 24000))
        return SynthesisResult(audio=audio, sample_rate=sr)
