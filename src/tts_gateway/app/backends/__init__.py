"""Backend abstraction and registry.

Each concrete backend wraps one TTS model behind a common interface so the
benchmark harness and the FastAPI service can use them interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import numpy as np

# ISO codes used internally. AR is MSA by default; Darija is "ar_darija".
SUPPORTED_LANGS = {"fr", "en", "ar", "ar_msa", "ar_darija"}


@dataclass(frozen=True)
class SynthesisResult:
    """Raw audio result from a backend."""

    audio: np.ndarray  # float32, shape (n_samples,) mono
    sample_rate: int


class BackendBase(ABC):
    """Common interface for all TTS backends."""

    name: ClassVar[str] = "base"
    supported_langs: ClassVar[frozenset[str]] = frozenset()
    supports_voice_cloning: ClassVar[bool] = False

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        self.device = device
        self.model_dir = model_dir
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory. Idempotent."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        lang: str,
        voice_ref: Path | None = None,
        speaker_id: str | None = None,
    ) -> SynthesisResult:
        """Generate speech for ``text`` in ``lang``.

        ``voice_ref`` is a path to a reference WAV (for cloning backends).
        ``speaker_id`` is a discrete speaker name (for multi-speaker fixed-voice models).
        Backends that don't support cloning ignore ``voice_ref``.
        """

    def _check_lang(self, lang: str) -> None:
        if lang not in self.supported_langs:
            raise ValueError(
                f"{self.name} does not support lang={lang!r}; "
                f"supported: {sorted(self.supported_langs)}"
            )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, type[BackendBase]] = {}


def register_backend(cls: type[BackendBase]) -> type[BackendBase]:
    """Decorator to register a backend class by its ``name`` attribute."""
    if cls.name in _REGISTRY:
        raise ValueError(f"Backend {cls.name!r} already registered")
    _REGISTRY[cls.name] = cls
    return cls


def get_backend(name: str) -> type[BackendBase]:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown backend {name!r}. Registered: {sorted(_REGISTRY)}. "
            "Make sure the backend module is imported."
        )
    return _REGISTRY[name]


def available_backends() -> list[str]:
    return sorted(_REGISTRY)
