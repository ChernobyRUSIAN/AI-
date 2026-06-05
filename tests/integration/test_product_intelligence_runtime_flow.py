from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings
from vuls.db.client import JsonObject
from vuls.db.models import ProjectStatus
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    LLMUsage,
    ProjectBrief,
)
from vuls.memory.schemas import MemoryContext
from vuls.runtime.project_service import RuntimeProjectService
from vuls.templates.schemas import TemplateSelection


class InMemoryUserRepository:
    def upsert_profile(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        display_name: str | None,
        language_code: str,
    ) -> JsonObject:
        return {
            "id": f"profile-{telegram_user_id}",
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "display_name": display_name,
            "language_code": language_code,
        }


class InMemoryProjectRepository:
    def __init__(self) -> None:
        self.rows: dict[str, JsonObject] = {}

    def create_project(
        self,
        *,
        owner_profile_id: str,
        title: str,
        slug: str,
        brief: dict[str, Any],
    ) -> JsonObject:
        row: JsonObject = {
            "id": "project-1",
            "owner_profile_id": owner_profile_id,
            "title": title,
            "slug": slug,
            "status": ProjectStatus.CLARIFYING.value,
            "selected_template_key": brief["selected_template_key"],
            "brief": brief,
            "updated_at": "2026-06-04T12:00:00Z",
        }
        self.rows["project-1"] = row
        return dict(row)

    def get_project(self, project_id: str) -> JsonObject:
        return dict(self.rows[project_id])

    def update_project_status(
        self,
        *,
        project_id: str,
        status: ProjectStatus,
        error: dict[str, Any] | None = None,
    ) -> JsonObject:
        self.rows[project_id]["status"] = status.value
        if error is not None:
            self.rows[project_id]["error"] = error
        return dict(self.rows[project_id])


class InMemoryMemoryService:
    def __init__(self) -> None:
        self.goals: list[str] = []
        self.requirements: list[str] = []

    def record_project_goal(self, *, profile_id: str, project_id: str, goal: str) -> object:
        self.goals.append(goal)
        return object()

    def record_extracted_requirement(
        self,
        *,
        profile_id: str,
        project_id: str,
        requirement: str,
    ) -> object:
        self.requirements.append(requirement)
        return object()

    def build_context(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit_per_type: int = 5,
    ) -> MemoryContext:
        return MemoryContext(profile_id=profile_id, project_id=project_id)


class DentalBriefGateway:
    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        return BriefNormalizationResponse(
            brief=ProjectBrief(
                title="Dental Clinic CRM",
                goal=request.user_idea,
                target_users=["clinic owner", "receptionist", "dentist"],
                must_have_features=["patients", "appointments", "treatments"],
                language_code=request.language_code,
            ),
            usage=LLMUsage(),
            model="mock-model",
        )


class TemplateRegistryStub:
    def select_template(self, user_intent: str) -> TemplateSelection:
        return TemplateSelection(
            selected_key="crm",
            confidence=0.95,
            needs_clarification=False,
            clarification_question=None,
            scores={"crm": 5.0},
        )


class UnusedGenerationOrchestrator:
    def generate_project(
        self,
        *,
        project_id: str,
        generation_run_id: str | None,
        template_key: str,
        brief: ProjectBrief,
        memory_context: dict[str, list[str]] | None = None,
    ) -> Any:
        raise AssertionError("Generation is not needed for the product intelligence API flow.")


class UnusedGitHubExportService:
    def export_project(self, request: GitHubExportRequest) -> GitHubExportResult:
        raise AssertionError("GitHub export is not needed for the product intelligence API flow.")


class EmptyGitHubRepository:
    def get_repository_for_project(self, project_id: str) -> JsonObject | None:
        return None


def test_product_intelligence_is_persisted_and_exposed_by_runtime_api() -> None:
    project_repository = InMemoryProjectRepository()
    memory_service = InMemoryMemoryService()
    service = RuntimeProjectService(
        settings=_settings(),
        user_repository=InMemoryUserRepository(),
        project_repository=project_repository,
        memory_service=memory_service,
        llm_gateway=DentalBriefGateway(),
        template_registry=TemplateRegistryStub(),
        generation_orchestrator=UnusedGenerationOrchestrator(),
        github_export_service=UnusedGitHubExportService(),
        github_repository=EmptyGitHubRepository(),
    )
    app = create_api_app(settings=_settings(), build_runtime=False)
    app.state.runtime = SimpleNamespace(project_service=service)
    client = TestClient(app)

    create_response = client.post(
        "/internal/projects",
        json={
            "telegram_user_id": 123,
            "telegram_chat_id": 456,
            "idea": "Create a CRM for a dentistry clinic",
            "language_code": "en",
        },
    )

    project_id = create_response.json()["project_id"]
    brief_response = client.get(f"/internal/projects/{project_id}/brief")
    roadmap_response = client.get(f"/internal/projects/{project_id}/roadmap")
    memory_response = client.get(f"/internal/projects/{project_id}/memory")

    assert create_response.status_code == 200
    assert brief_response.status_code == 200
    assert roadmap_response.status_code == 200
    assert memory_response.status_code == 200
    assert brief_response.json()["brief"]["product_name"] == "Dental Clinic CRM"
    assert "patients" in _serialized(brief_response.json())
    assert [phase["name"] for phase in roadmap_response.json()["roadmap"]["phases"]] == [
        "Phase 1 - MVP",
        "Phase 2 - Growth",
        "Phase 3 - Scale",
    ]
    assert memory_response.json()["memory"]["source_idea"] == (
        "Create a CRM for a dentistry clinic"
    )
    assert memory_response.json()["memory"]["domain"] == "dentistry"
    assert project_repository.rows["project-1"]["brief"]["product_memory"]["domain"] == "dentistry"
    assert memory_service.goals == ["Create a CRM for a dentistry clinic"]
    assert memory_service.requirements == ["patients", "appointments", "treatments"]


def _serialized(value: object) -> str:
    return str(value).lower()


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
        github_default_private=True,
        project_workdir=Path("var/projects"),
    )
