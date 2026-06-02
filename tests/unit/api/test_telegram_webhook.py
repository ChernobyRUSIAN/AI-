from pathlib import Path

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings


def test_telegram_webhook_rejects_invalid_secret() -> None:
    client = TestClient(
        create_api_app(
            settings=_settings(telegram_webhook_secret="expected-secret"),
            build_runtime=False,
        )
    )

    response = client.post("/webhooks/telegram/wrong-secret", json={"update_id": 1})

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "invalid_webhook_secret",
            "message": "Invalid Telegram webhook secret",
        }
    }


def _settings(*, telegram_webhook_secret: str = "telegram-webhook-secret") -> Settings:
    return Settings(
        app_env=AppEnv.LOCAL,
        app_base_url="https://vuls.example.com",
        app_secret_key="dev-secret-key",
        telegram_bot_token="123456:telegram-token",
        telegram_webhook_secret=telegram_webhook_secret,
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="supabase-service-role",
        supabase_storage_bucket="vuls-artifacts",
        openai_api_key="openai-key",
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir=Path("var/projects"),
    )
