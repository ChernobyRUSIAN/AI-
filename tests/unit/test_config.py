import pytest
from pydantic import ValidationError

from vuls.core.config import AppEnv, Settings, load_settings


def test_settings_loads_required_runtime_values() -> None:
    settings = Settings(
        app_env=AppEnv.LOCAL,
        app_base_url="https://vuls.example.com",
        app_secret_key="dev-secret-key",
        telegram_bot_token="123456:telegram-token",
        telegram_webhook_secret="telegram-webhook-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="supabase-service-role",
        supabase_storage_bucket="vuls-artifacts",
        openai_api_key="openai-key",
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir="./var/projects",
    )

    assert settings.app_env is AppEnv.LOCAL
    assert settings.github_default_private is True
    assert settings.zip_max_bytes == 25_000_000
    assert settings.log_level == "INFO"


def test_settings_rejects_invalid_environment() -> None:
    with pytest.raises(ValidationError):
        Settings(
            app_env="preview",
            app_base_url="https://vuls.example.com",
            app_secret_key="dev-secret-key",
            telegram_bot_token="123456:telegram-token",
            telegram_webhook_secret="telegram-webhook-secret",
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="supabase-service-role",
            supabase_storage_bucket="vuls-artifacts",
            openai_api_key="openai-key",
            openai_model="gpt-5.1",
            github_token="github-token",
            github_owner="vuls",
            project_workdir="./var/projects",
        )


def test_load_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("APP_BASE_URL", "https://vuls.example.com")
    monkeypatch.setenv("APP_SECRET_KEY", "dev-secret-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:telegram-token")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "telegram-webhook-secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "supabase-service-role")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "vuls-artifacts")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.1")
    monkeypatch.setenv("GITHUB_TOKEN", "github-token")
    monkeypatch.setenv("GITHUB_OWNER", "vuls")
    monkeypatch.setenv("PROJECT_WORKDIR", "./var/projects")

    settings = load_settings()

    assert settings.app_env is AppEnv.LOCAL
    assert settings.github_owner == "vuls"
