"""Application settings, loaded from the environment (and a local .env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOBAPPLY_", env_file=".env", extra="ignore"
    )

    # The Anthropic SDK reads ANTHROPIC_API_KEY itself; we surface it here only
    # so the app can fail fast with a clear message when it's missing.
    anthropic_api_key: str = ""

    model: str = "claude-opus-4-8"
    database_url: str = "sqlite:///./job_apply.db"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ANTHROPIC_API_KEY has no JOBAPPLY_ prefix, so read it directly.
        import os

        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
