from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: AppEnv
    app_base_url: str
    app_secret_key: str
    telegram_bot_token: str
    telegram_webhook_secret: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_storage_bucket: str
    openai_api_key: str
    openai_model: str
    github_token: str
    github_owner: str
    github_default_private: bool = True
    project_workdir: Path
    zip_max_bytes: int = Field(default=25_000_000, gt=0)
    log_level: str = "INFO"
    sentry_dsn: str | None = None
    openai_timeout_seconds: int = Field(default=60, gt=0)
    github_api_base_url: str = "https://api.github.com"
    rate_limit_projects_per_user_day: int = Field(default=5, gt=0)
    rate_limit_llm_calls_per_project: int = Field(default=8, gt=0)


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
