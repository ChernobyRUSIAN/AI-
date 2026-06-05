from dataclasses import dataclass
from pathlib import Path

from vuls.core.config import Settings

REQUIRED_ENVIRONMENT_VARIABLES = (
    "APP_ENV",
    "APP_BASE_URL",
    "APP_SECRET_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_STORAGE_BUCKET",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "GITHUB_TOKEN",
    "GITHUB_OWNER",
    "PROJECT_WORKDIR",
)

REQUIRED_RUNTIME_COMPONENTS = (
    "user_repository",
    "project_repository",
    "memory_repository",
    "artifact_repository",
    "github_repository",
    "memory_service",
    "template_registry",
    "llm_gateway",
    "generation_orchestrator",
    "github_export_service",
    "project_service",
    "telegram_flow_service",
    "telegram_dispatcher",
    "telegram_sender",
)

_ENV_FIELD_NAMES = {
    "APP_ENV": "app_env",
    "APP_BASE_URL": "app_base_url",
    "APP_SECRET_KEY": "app_secret_key",
    "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
    "TELEGRAM_WEBHOOK_SECRET": "telegram_webhook_secret",
    "SUPABASE_URL": "supabase_url",
    "SUPABASE_SERVICE_ROLE_KEY": "supabase_service_role_key",
    "SUPABASE_STORAGE_BUCKET": "supabase_storage_bucket",
    "OPENAI_API_KEY": "openai_api_key",
    "OPENAI_MODEL": "openai_model",
    "GITHUB_TOKEN": "github_token",
    "GITHUB_OWNER": "github_owner",
    "PROJECT_WORKDIR": "project_workdir",
}


@dataclass(frozen=True)
class RuntimeValidationIssue:
    code: str
    message: str
    env_var: str | None = None
    component: str | None = None


@dataclass(frozen=True)
class RuntimeValidationReport:
    issues: list[RuntimeValidationIssue]
    required_environment: tuple[str, ...] = REQUIRED_ENVIRONMENT_VARIABLES
    required_components: tuple[str, ...] = REQUIRED_RUNTIME_COMPONENTS

    @property
    def ready(self) -> bool:
        return not self.issues


class RuntimeValidationError(RuntimeError):
    def __init__(self, report: RuntimeValidationReport) -> None:
        self.report = report
        super().__init__(_format_report(report))


def validate_runtime_startup(
    *,
    settings: Settings,
    runtime: object | None,
    require_runtime: bool,
) -> RuntimeValidationReport:
    issues = [
        *validate_required_environment(settings),
        *validate_runtime_wiring(runtime, require_runtime=require_runtime),
    ]
    return RuntimeValidationReport(issues=issues)


def validate_required_environment(settings: Settings) -> list[RuntimeValidationIssue]:
    issues: list[RuntimeValidationIssue] = []
    for env_var in REQUIRED_ENVIRONMENT_VARIABLES:
        field_name = _ENV_FIELD_NAMES[env_var]
        value = getattr(settings, field_name)
        if _is_missing(value):
            issues.append(
                RuntimeValidationIssue(
                    code="missing_required_environment",
                    env_var=env_var,
                    message=f"{env_var} must be configured before Vuls starts.",
                )
            )
    return issues


def validate_runtime_wiring(
    runtime: object | None,
    *,
    require_runtime: bool,
) -> list[RuntimeValidationIssue]:
    if runtime is None:
        if not require_runtime:
            return []
        return [
            RuntimeValidationIssue(
                code="missing_runtime_container",
                component="runtime",
                message="Runtime container must be configured before Vuls starts.",
            )
        ]

    issues: list[RuntimeValidationIssue] = []
    for component in REQUIRED_RUNTIME_COMPONENTS:
        if getattr(runtime, component, None) is None:
            issues.append(
                RuntimeValidationIssue(
                    code="missing_runtime_component",
                    component=component,
                    message=f"Runtime component is not wired: {component}.",
                )
            )
    return issues


def ensure_runtime_ready(report: RuntimeValidationReport) -> None:
    if not report.ready:
        raise RuntimeValidationError(report)


def _is_missing(value: object) -> bool:
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Path):
        return not str(value).strip()
    return value is None


def _format_report(report: RuntimeValidationReport) -> str:
    if report.ready:
        return "Runtime validation passed."

    details = []
    for issue in report.issues:
        subject = issue.env_var or issue.component or issue.code
        details.append(f"{subject}: {issue.message}")
    return "Runtime validation failed: " + "; ".join(details)
