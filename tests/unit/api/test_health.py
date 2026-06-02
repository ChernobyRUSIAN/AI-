from pathlib import Path

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings


def test_health_returns_ok_status() -> None:
    client = TestClient(create_api_app(settings=_settings(), build_runtime=False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def _settings() -> Settings:
    return Settings(
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
        project_workdir=Path("var/projects"),
    )
