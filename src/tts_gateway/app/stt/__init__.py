"""STT backend abstraction and registry.

Each concrete STT backend wraps one speech-to-text model behind a common
interface so the FastAPI service can use them interchangeably.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

# Languages supported across the STT subsystem.
SUPPORTED_STT_LANGS = {"fr", "en", "ar", "ar_darija"}


@dataclass(frozen=True)
class TranscriptionResult:
    """Result from a STT backend."""

    text: str
    language: str | None  # detected language code, if available


class STTBackendBase(ABC):
    """Common interface for all STT backends."""

    name: ClassVar[str] = "base"
    supported_langs: ClassVar[frozenset[str]] = frozenset()

    def __init__(self, device: str = "cpu", model_dir: Path | None = None) -> None:
        self.device = device
        self.model_dir = model_dir
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory. Idempotent."""

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        *,
        lang: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio bytes (WAV format, 16-bit PCM) to text.

        ``lang`` is an optional language hint. If None, the backend should
        attempt automatic language detection.
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

_STT_REGISTRY: dict[str, type[STTBackendBase]] = {}


def register_stt_backend(cls: type[STTBackendBase]) -> type[STTBackendBase]:
    """Decorator to register a STT backend class by its ``name`` attribute."""
    if cls.name in _STT_REGISTRY:
        raise ValueError(f"STT backend {cls.name!r} already registered")
    _STT_REGISTRY[cls.name] = cls
    return cls


def get_stt_backend(name: str) -> type[STTBackendBase]:
    if name not in _STT_REGISTRY:
        raise KeyError(
            f"Unknown STT backend {name!r}. Registered: {sorted(_STT_REGISTRY)}. "
            "Make sure the STT backend module is imported."
        )
    return _STT_REGISTRY[name]


def available_stt_backends() -> list[str]:
    return sorted(_STT_REGISTRY)
