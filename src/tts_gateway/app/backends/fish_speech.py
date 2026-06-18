"""Fish-Speech S2-Pro backend.

License: CC-BY-NC-SA-4.0 — non-commercial. Kept as a quality plan-B for the
POC, not a production candidate without a commercial license.

Install: pip install -e ".[fish]"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tts_gateway.app.backends import BackendBase, SynthesisResult, register_backend

_LANG_MAP = {
    "fr": "fr",
    "en": "en",
    "ar": "ar",
    "ar_msa": "ar",
}


@register_backend
class FishSpeechBackend(BackendBase):
    name = "fish_speech"
    supported_langs = frozenset(_LANG_MAP.keys())
    supports_voice_cloning = True

    MODEL_ID = "fishaudio/s2-pro"

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        super().__init__(device=device, model_dir=model_dir)
        self._engine: Any = None

    def load(self) -> None:
        if self._loaded:
            return
        try:
            import fish_speech_lib  # noqa: F401, PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "fish-speech-lib is not installed. Install with: pip install -e '.[fish]'"
            ) from exc
        # Engine wiring is finalized during POC — Fish ships several CLI/API
        # surfaces depending on the release. Keep the load step minimal here.
        self._loaded = True

    def synthesize(
        self,
        text: str,
        lang: str,
        voice_ref: Path | None = None,
        speaker_id: str | None = None,
    ) -> SynthesisResult:
        self._check_lang(lang)
        if not self._loaded:
            self.load()

        raise NotImplementedError(
            "FishSpeechBackend.synthesize: wire-up against the official "
            "S2-Pro inference recipe during POC step 4."
        )
