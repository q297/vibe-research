import secrets
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Root .env for local runs from backend/, compose passes variables directly
    # Empty values like DAILY_TOKEN_LIMIT= mean "use the default"
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), extra="ignore", env_ignore_empty=True
    )

    app_version: str = "0.1.0"
    # Serve fixtures instead of real role 2-4 modules
    mock_mode: bool = True
    # No network and no LLM calls, only snapshot and cache (K1)
    offline_mode: bool = False

    # Empty means a random per-process secret, tokens die on restart
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_ttl_minutes: int = 12 * 60
    cors_origins: list[str] = ["http://localhost:5173"]

    # Per-user limits that protect the shared LLM budget on a public stand (E7)
    rate_limit_runs_per_hour: int = 30
    rate_limit_chat_per_hour: int = 60
    rate_limit_ingest_per_hour: int = 10

    daily_token_limit: int | None = None
    stub_step_delay_s: float = 0.4

    database_url: str | None = None

    # Client CSV folder; empty means stub profiles
    profiles_data_dir: str | None = None
    profiles_revenue_multiplier: float | None = None
    profiles_pinned: list[str] = []

    @field_validator("jwt_secret")
    @classmethod
    def _secret_or_random(cls, value: str) -> str:
        return value or secrets.token_urlsafe(32)


@lru_cache
def get_settings() -> Settings:
    return Settings()
