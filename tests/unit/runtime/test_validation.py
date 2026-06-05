from pathlib import Path
from types import SimpleNamespace

from vuls.core.config import AppEnv, Settings
from vuls.runtime.validation import (
    REQUIRED_ENVIRONMENT_VARIABLES,
    validate_runtime_startup,
)


def test_validation_reports_blank_required_environment_values() -> None:
    settings = runtime_settings(
        app_secret_key=" ",
        openai_api_key="",
    )

    report = validate_runtime_startup(settings=settings, runtime=None, require_runtime=False)

    assert report.ready is False
    assert report.required_environment == REQUIRED_ENVIRONMENT_VARIABLES
    assert [(issue.code, issue.env_var) for issue in report.issues] == [
        ("missing_required_environment", "APP_SECRET_KEY"),
        ("missing_required_environment", "OPENAI_API_KEY"),
    ]


def test_validation_requires_runtime_components_for_startup() -> None:
    settings = runtime_settings()
    runtime = SimpleNamespace(
        settings=settings,
        user_repository=object(),
        project_repository=object(),
        memory_repository=object(),
        artifact_repository=object(),
        github_repository=object(),
        memory_service=object(),
        template_registry=object(),
        llm_gateway=object(),
        generation_orchestrator=object(),
        github_export_service=object(),
        project_service=object(),
        telegram_flow_service=object(),
        telegram_dispatcher=object(),
    )

    report = validate_runtime_startup(settings=settings, runtime=runtime, require_runtime=True)

    assert report.ready is False
    assert [(issue.code, issue.component) for issue in report.issues] == [
        ("missing_runtime_component", "telegram_sender")
    ]


def test_validation_accepts_complete_runtime_wiring() -> None:
    runtime = SimpleNamespace(
        settings=runtime_settings(),
        user_repository=object(),
        project_repository=object(),
        memory_repository=object(),
        artifact_repository=object(),
        github_repository=object(),
        memory_service=object(),
        template_registry=object(),
        llm_gateway=object(),
        generation_orchestrator=object(),
        github_export_service=object(),
        project_service=object(),
        telegram_flow_service=object(),
        telegram_dispatcher=object(),
        telegram_sender=object(),
    )

    report = validate_runtime_startup(
        settings=runtime.settings,
        runtime=runtime,
        require_runtime=True,
    )

    assert report.ready is True
    assert report.issues == []


def runtime_settings(**overrides: object) -> Settings:
    values = {
        "app_env": AppEnv.LOCAL,
        "app_base_url": "https://vuls.example.com",
        "app_secret_key": "dev-secret-key",
        "telegram_bot_token": "123456:telegram-token",
        "telegram_webhook_secret": "telegram-webhook-secret",
        "supabase_url": "https://example.supabase.co",
        "supabase_service_role_key": "supabase-service-role",
        "supabase_storage_bucket": "vuls-artifacts",
        "openai_api_key": "openai-key",
        "openai_model": "gpt-5.1",
        "github_token": "github-token",
        "github_owner": "vuls",
        "project_workdir": Path("var/projects"),
    }
    values.update(overrides)
    return Settings(**values)
