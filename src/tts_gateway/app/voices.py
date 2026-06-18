"""Brand-voice registry: discovers WAV files in a directory and serves them."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Voice:
    voice_id: str
    path: Path
    description: str | None = None


class VoiceRegistry:
    """Keeps track of available brand voices.

    A voice is any ``*.wav`` file inside ``voices_dir``. The voice_id is the
    filename without extension. Reload on demand (``refresh``) — uploads of new
    voices via /v1/voices add files to disk and call refresh.
    """

    def __init__(self, voices_dir: Path) -> None:
        self.voices_dir = voices_dir
        self._voices: dict[str, Voice] = {}
        self.refresh()

    def refresh(self) -> None:
        self._voices.clear()
        if not self.voices_dir.exists():
            logger.warning("Voices dir does not exist: %s", self.voices_dir)
            return
        for wav in sorted(self.voices_dir.glob("*.wav")):
            vid = wav.stem
            self._voices[vid] = Voice(voice_id=vid, path=wav)
        logger.info("Loaded %d voice(s) from %s", len(self._voices), self.voices_dir)

    def list(self) -> list[Voice]:
        return list(self._voices.values())

    def get(self, voice_id: str) -> Voice | None:
        return self._voices.get(voice_id)

    def add(self, voice_id: str, wav_bytes: bytes) -> Voice:
        """Persist a new brand voice WAV to disk and register it."""
        # Defensive filename — voice_id is admin-controlled but we still strip.
        safe_id = "".join(c for c in voice_id if c.isalnum() or c in ("-", "_"))
        if not safe_id or safe_id != voice_id:
            raise ValueError("voice_id must be alphanumeric / dashes / underscores")

        self.voices_dir.mkdir(parents=True, exist_ok=True)
        path = self.voices_dir / f"{safe_id}.wav"
        path.write_bytes(wav_bytes)
        voice = Voice(voice_id=safe_id, path=path)
        self._voices[safe_id] = voice
        return voice
