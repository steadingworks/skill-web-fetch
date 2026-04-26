"""Application configuration via environment variables (WEBFETCH_ prefix)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "WEBFETCH_"}

    jwt_public_key_path: str  # path to PEM-encoded RSA public key
    jwt_issuer: str = "skill-auth"
    searxng_base_url: str = ""  # empty = search endpoint disabled
    log_level: str = "INFO"

    @property
    def public_key_pem(self) -> str:
        """Read public key from disk on each call (supports rotation without restart)."""
        return Path(self.jwt_public_key_path).read_text().strip()


settings = Settings()
