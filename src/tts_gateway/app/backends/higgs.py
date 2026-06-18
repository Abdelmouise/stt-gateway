"""Higgs-Audio v3 backend (BosonAI).

License: TBD (verify on the model card before any production use).
Architecture: LLM-style TTS (~4B parameters), strong multilingual potential.

Install: pip install -e ".[higgs]"
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
class HiggsBackend(BackendBase):
    name = "higgs"
    supported_langs = frozenset(_LANG_MAP.keys())
    supports_voice_cloning = True

    MODEL_ID = "bosonai/higgs-audio-v3-tts-4b"

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        super().__init__(device=device, model_dir=model_dir)
        self._model: Any = None
        self._processor: Any = None

    def load(self) -> None:
        if self._loaded:
            return
        try:
            # Higgs ships its own pipeline; transformers fallback is sketched
            # here and must be confirmed against the official inference recipe.
            from transformers import AutoModel, AutoProcessor  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "transformers is not installed. Install with: pip install -e '.[higgs]'"
            ) from exc

        self._processor = AutoProcessor.from_pretrained(self.MODEL_ID, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(self.MODEL_ID, trust_remote_code=True).to(
            self.device
        )
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

        # Placeholder: the exact generation API for Higgs-Audio v3 is to be
        # finalized during the POC against the model card. The contract below
        # is what callers can rely on.
        raise NotImplementedError(
            "HiggsBackend.synthesize: wire-up against the official inference "
            "recipe during POC step 4 (see bench/run_bench.py)."
        )
        # Expected shape once implemented:
        # return SynthesisResult(audio=audio_f32, sample_rate=24000)
