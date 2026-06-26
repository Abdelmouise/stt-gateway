"""Piper TTS backend — fast local neural TTS via ONNX-exported VITS models.

Each language is served by a dedicated .onnx model file (one voice per lang).
No voice cloning; ``voice_ref`` is silently ignored.

Install:
    pip install -e '.[piper]'

Download voices (run once):
    python -m piper.download_voices fr_FR-siwis-medium ar_JO-kareem-medium en_US-lessac-medium

Expected layout under ``model_dir`` (default: ~/.cache/tts_gateway/piper/):
    <model_dir>/fr_FR-siwis-medium.onnx
    <model_dir>/fr_FR-siwis-medium.onnx.json
    <model_dir>/ar_JO-kareem-medium.onnx
    <model_dir>/ar_JO-kareem-medium.onnx.json
    <model_dir>/en_US-lessac-medium.onnx
    <model_dir>/en_US-lessac-medium.onnx.json
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from tts_gateway.app.backends import BackendBase, SynthesisResult, register_backend

# Mapping from internal lang code to the Piper voice model name.
# ar_darija is not available in Piper and will be skipped automatically by
# the bench harness (it is not in supported_langs).
_LANG_MODEL: dict[str, str] = {
    "fr": "fr_FR-siwis-medium",
    "ar_msa": "ar_JO-kareem-medium",
    "en": "en_US-lessac-medium",
}

_DEFAULT_MODEL_DIR = Path.home() / ".cache" / "tts_gateway" / "piper"


@register_backend
class PiperBackend(BackendBase):
    name = "piper"
    supported_langs = frozenset(_LANG_MODEL.keys())
    supports_voice_cloning = False

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        super().__init__(device=device, model_dir=model_dir)
        self._voices: dict[str, object] = {}  # lang -> PiperVoice instance
        self._sample_rate: int = 22050  # updated from first chunk at runtime

    def load(self) -> None:
        if self._loaded:
            return

        try:
            from piper import PiperVoice  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "piper-tts is not installed. Install with: pip install -e '.[piper]'"
            ) from exc

        root = self.model_dir if self.model_dir is not None else _DEFAULT_MODEL_DIR

        for lang, model_name in _LANG_MODEL.items():
            onnx_path = root / f"{model_name}.onnx"
            if not onnx_path.exists():
                raise FileNotFoundError(
                    f"Piper model not found: {onnx_path}\n"
                    f"Download with: python -m piper.download_voices {model_name}"
                )
            use_cuda = self.device == "cuda"
            self._voices[lang] = PiperVoice.load(str(onnx_path), use_cuda=use_cuda)

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

        voice = self._voices[lang]
        chunks = list(voice.synthesize(text))

        if not chunks:
            return SynthesisResult(
                audio=np.zeros(0, dtype=np.float32),
                sample_rate=self._sample_rate,
            )

        sample_rate: int = chunks[0].sample_rate
        self._sample_rate = sample_rate

        raw_bytes = b"".join(chunk.audio_int16_bytes for chunk in chunks)
        audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        audio_float32 = audio_int16.astype(np.float32) / 32768.0

        return SynthesisResult(audio=audio_float32, sample_rate=sample_rate)
