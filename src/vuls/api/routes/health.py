from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class DependencyStatus(BaseModel):
    supabase: str = "ok"
    openai: str = "not_checked"
    github: str = "not_checked"


class LLMHealth(BaseModel):
    provider: str
    base_url: str
    active_model: str
    configured_models: list[str]
    last_failure_code: str | None = None
    last_failure_message: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    dependencies: DependencyStatus
    llm: LLMHealth


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    runtime = getattr(request.app.state, "runtime", None)
    llm_gateway = getattr(runtime, "llm_gateway", None)
    configured_models = list(
        getattr(llm_gateway, "configured_models", (settings.openai_model,))
    )
    active_model = str(getattr(llm_gateway, "active_model", configured_models[0]))
    failures = list(getattr(llm_gateway, "last_failures", ()))
    last_failure = failures[-1] if failures else {}
    return HealthResponse(
        status="ok",
        version="v1.0",
        dependencies=DependencyStatus(
            supabase="ok" if runtime is not None else "not_checked",
            openai="configured" if configured_models else "not_checked",
            github="configured" if runtime is not None else "not_checked",
        ),
        llm=LLMHealth(
            provider=_provider_from_base_url(settings.openai_base_url),
            base_url=settings.openai_base_url,
            active_model=active_model,
            configured_models=configured_models,
            last_failure_code=last_failure.get("code"),
            last_failure_message=last_failure.get("message"),
        ),
    )


def _provider_from_base_url(base_url: str) -> str:
    normalized = base_url.casefold()
    if "openrouter" in normalized:
        return "openrouter"
    if "openai" in normalized:
        return "openai"
    return "openai-compatible"
