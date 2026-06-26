"""Helper to import all STT backends so they self-register.

Each STT backend module guards heavy ML imports; importing the module itself
only runs the registration decorator. Heavy imports happen lazily inside load().
"""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

_STT_BACKEND_MODULES = [
    "tts_gateway.app.stt.dummy",
    "tts_gateway.app.stt.moulsot",
]


def import_all_stt_backends() -> list[str]:
    """Import every STT backend module; tolerate ImportError on optional deps.

    Returns the list of successfully imported STT backend module names.
    """
    imported: list[str] = []
    for mod in _STT_BACKEND_MODULES:
        try:
            importlib.import_module(mod)
            imported.append(mod)
        except ImportError as exc:
            logger.info("Skipping STT backend %s (missing optional dep: %s)", mod, exc)
    return imported
