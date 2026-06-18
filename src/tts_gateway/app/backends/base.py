"""Re-export of base classes for convenience."""

from tts_gateway.app.backends import (
    BackendBase,
    SynthesisResult,
    available_backends,
    get_backend,
    register_backend,
)

__all__ = [
    "BackendBase",
    "SynthesisResult",
    "available_backends",
    "get_backend",
    "register_backend",
]
