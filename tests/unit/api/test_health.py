from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings


def test_health_returns_ok_status() -> None:
    client = TestClient(create_api_app(settings=_settings(), build_runtime=False))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["llm"] == {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "active_model": "gpt-5.1",
        "configured_models": ["gpt-5.1"],
        "last_failure_code": None,
        "last_failure_message": None,
    }


def test_health_reports_openrouter_provider_and_runtime_model_diagnostics() -> None:
    class FakeGateway:
        active_model = "google/gemini-fallback"
        configured_models = ("openai/gpt-primary", "google/gemini-fallback")
        last_failures = (
            {
                "code": "rate_limit",
                "message": "primary model rate limited",
            },
        )

    runtime = SimpleNamespace(
        user_repository=object(),
        project_repository=object(),
        memory_repository=object(),
        artifact_repository=object(),
        github_repository=object(),
        memory_service=object(),
        template_registry=object(),
        llm_gateway=FakeGateway(),
        generation_orchestrator=object(),
        github_export_service=object(),
        project_service=object(),
        telegram_flow_service=object(),
        telegram_dispatcher=object(),
        telegram_sender=object(),
    )

    app = create_api_app(
        settings=_settings(
            openai_base_url="https://openrouter.ai/api/v1",
            openai_model="openai/gpt-primary",
        ),
        runtime=runtime,
        build_runtime=False,
    )
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["dependencies"] == {
        "supabase": "ok",
        "openai": "configured",
        "github": "configured",
    }
    assert response.json()["llm"] == {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "active_model": "google/gemini-fallback",
        "configured_models": ["openai/gpt-primary", "google/gemini-fallback"],
        "last_failure_code": "rate_limit",
        "last_failure_message": "primary model rate limited",
    }


def _settings(
    *,
    openai_base_url: str = "https://api.openai.com/v1",
    openai_model: str = "gpt-5.1",
) -> Settings:
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
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        github_token="github-token",
        github_owner="vuls",
        project_workdir=Path("var/projects"),
    )
