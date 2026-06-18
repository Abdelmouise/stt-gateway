"""Helper to import all backends so they self-register.

Each backend module guards heavy ML imports; importing the module itself only
runs the registration decorator. Heavy imports happen lazily inside ``load()``.
"""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

# Order matters only for stable listing in /v1/voices. Dummy first so the
# service is always usable even if no ML deps are installed.
_BACKEND_MODULES = [
    "tts_gateway.app.backends.dummy",
    "tts_gateway.app.backends.xtts",
    "tts_gateway.app.backends.chatterbox",
    "tts_gateway.app.backends.higgs",
    "tts_gateway.app.backends.fish_speech",
]


def import_all_backends() -> list[str]:
    """Import every backend module; tolerate ImportError on optional deps.

    Returns the list of successfully imported backend module names so the
    caller can log what is actually available in the running environment.
    """
    imported: list[str] = []
    for mod in _BACKEND_MODULES:
        try:
            importlib.import_module(mod)
            imported.append(mod)
        except ImportError as exc:  # missing optional dep — fine
            logger.info("Skipping backend %s (missing optional dep: %s)", mod, exc)
    return imported
