"""Application configuration via environment variables / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values overridable via env vars (TTS_* prefix)."""

    model_config = SettingsConfigDict(
        env_prefix="TTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Backend selection ---
    backend: str = Field(default="dummy", description="Active backend name.")
    device: str = Field(default="cpu", description="cpu | cuda | mps")
    model_cache_dir: Path = Field(
        default=Path.home() / ".cache" / "tts-gateway",
        description="Local cache for downloaded weights (mounted as PVC in prod).",
    )

    # --- Voice management ---
    voices_dir: Path = Field(
        default=Path("voices"),
        description="Directory containing brand voice WAV references.",
    )
    default_voice_id: str = Field(default="brand_default")

    # --- STT backend selection ---
    stt_backend: str = Field(default="dummy", description="Active STT backend name.")
    stt_device: str = Field(default="cpu", description="cpu | cuda | mps (for STT)")

    # --- Service limits ---
    max_text_length: int = Field(default=2000, ge=1, le=10000)
    default_sample_rate: int = Field(default=24000)
    request_timeout_s: float = Field(default=30.0)
    max_audio_upload_bytes: int = Field(default=50 * 1024 * 1024, description="Max upload size for STT (50 MB).")

    # --- Auth (admin endpoints) ---
    admin_api_key: str | None = Field(
        default=None,
        description="Bearer token required for admin endpoints; if None, admin endpoints are disabled.",
    )

    # --- Service ---
    log_level: str = Field(default="INFO")
    cors_origins: list[str] = Field(default_factory=list)


_settings: Settings | None = None


def get_settings() -> Settings:
    """Cached settings accessor (FastAPI Depends-friendly)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
