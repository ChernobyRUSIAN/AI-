from dataclasses import dataclass

import pytest

from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
)
from vuls.core.config import AppEnv, Settings
from vuls.db.client import JsonObject
from vuls.db.models import MemorySource, MemoryType, ProjectStatus
from vuls.db.repositories.memory import MemoryRepositoryTransientError
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult
from vuls.llm.gateway import LLMOutputValidationError, LLMProviderUnavailableError
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    GeneratedProjectFile,
    GeneratedProjectManifest,
    LLMUsage,
    ProjectBrief,
)
from vuls.memory.schemas import MemoryContext
from vuls.memory.service import MemoryService
from vuls.runtime.project_service import RuntimeProjectGenerationError, RuntimeProjectService
from vuls.templates.schemas import TemplateSelection


class FakeUserRepository:
    def __init__(self) -> None:
        self.profile = {"id": "profile-1"}
        self.upserts: list[dict[str, object]] = []

    def upsert_profile(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        display_name: str | None,
        language_code: str,
    ) -> dict[str, object]:
        self.upserts.append(
            {
                "telegram_user_id": telegram_user_id,
                "telegram_username": telegram_username,
                "display_name": display_name,
                "language_code": language_code,
            }
        )
        return dict(self.profile)


class FakeProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, object]] = {}
        self.status_updates: list[tuple[str, ProjectStatus]] = []

    def create_project(
        self,
        *,
        owner_profile_id: str,
        title: str,
        slug: str,
        brief: dict[str, object],
    ) -> dict[str, object]:
        project = {
            "id": "project-1",
            "owner_profile_id": owner_profile_id,
            "title": title,
            "slug": slug,
            "status": ProjectStatus.CLARIFYING.value,
            "selected_template_key": brief["selected_template_key"],
            "brief": brief,
            "updated_at": "2026-06-02T12:00:00Z",
        }
        self.projects["project-1"] = project
        return dict(project)

    def get_project(self, project_id: str) -> dict[str, object]:
        return dict(self.projects[project_id])

    def update_project_status(
        self,
        *,
        project_id: str,
        status: ProjectStatus,
        error: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.status_updates.append((project_id, status))
        self.projects[project_id]["status"] = status.value
        if error is not None:
            self.projects[project_id]["error"] = error
        return dict(self.projects[project_id])


class FakeMemoryService:
    def __init__(self) -> None:
        self.goals: list[tuple[str, str, str]] = []
        self.requirements: list[tuple[str, str, str]] = []
        self.context_calls: list[tuple[str, str]] = []

    def record_project_goal(self, *, profile_id: str, project_id: str, goal: str) -> object:
        self.goals.append((profile_id, project_id, goal))
        return object()

    def record_extracted_requirement(
        self,
        *,
        profile_id: str,
        project_id: str,
        requirement: str,
    ) -> object:
        self.requirements.append((profile_id, project_id, requirement))
        return object()

    def build_context(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit_per_type: int = 5,
    ) -> MemoryContext:
        self.context_calls.append((profile_id, project_id))
        return MemoryContext(profile_id=profile_id, project_id=project_id)


class TransientFailingMemoryRepository:
    def load_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[JsonObject]:
        return []

    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: dict[str, object],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject:
        raise MemoryRepositoryTransientError("Supabase memory_items insert failed")


class FakeLLMGateway:
    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        return BriefNormalizationResponse(
            brief=ProjectBrief(
                title="Car Wash CRM",
                goal=request.user_idea,
                target_users=["owner", "staff"],
                must_have_features=["customers", "appointments"],
                language_code=request.language_code,
            ),
            usage=LLMUsage(),
            model="gpt-test",
        )


class ProviderUnavailableLLMGateway:
    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        raise LLMProviderUnavailableError(
            failures=[
                {
                    "model": "openai/gpt-primary",
                    "provider": "OpenAI",
                    "attempt": "1",
                    "code": "unsupported_country_region_territory",
                    "message": "unsupported region",
                }
            ]
        )


class FakeTemplateRegistry:
    def select_template(self, user_intent: str) -> TemplateSelection:
        return TemplateSelection(
            selected_key="crm",
            confidence=0.95,
            needs_clarification=False,
            clarification_question=None,
            scores={"crm": 4.0},
        )


@dataclass(frozen=True)
class FakeGenerationResult:
    project_id: str
    template_key: str
    manifest: GeneratedProjectManifest
    zip_artifact_id: str


class FakeGenerationOrchestrator:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def generate_project(
        self,
        *,
        project_id: str,
        generation_run_id: str | None,
        template_key: str,
        brief: ProjectBrief,
        memory_context: dict[str, list[str]] | None = None,
    ) -> FakeGenerationResult:
        self.calls.append(
            {
                "project_id": project_id,
                "template_key": template_key,
                "brief": brief,
                "memory_context": memory_context,
            }
        )
        return FakeGenerationResult(
            project_id=project_id,
            template_key=template_key,
            manifest=sample_manifest(),
            zip_artifact_id="zip-artifact-1",
        )


class InvalidJsonGenerationOrchestrator(FakeGenerationOrchestrator):
    def generate_project(
        self,
        *,
        project_id: str,
        generation_run_id: str | None,
        template_key: str,
        brief: ProjectBrief,
        memory_context: dict[str, list[str]] | None = None,
    ) -> FakeGenerationResult:
        raise LLMOutputValidationError("Model output was not valid JSON.")


class FakeGitHubExportService:
    def __init__(self) -> None:
        self.requests: list[GitHubExportRequest] = []

    def export_project(self, request: GitHubExportRequest) -> GitHubExportResult:
        self.requests.append(request)
        return GitHubExportResult(
            project_id=request.project_id,
            owner=request.owner,
            repo_name="car-wash-crm",
            html_url="https://github.com/vuls/car-wash-crm",
            default_branch="main",
            committed_files=["README.md"],
        )


class FakeGitHubRepository:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def get_repository_for_project(self, project_id: str) -> dict[str, object] | None:
        return self.rows.get(project_id)


def test_runtime_project_service_creates_project_from_internal_contract() -> None:
    service, fakes = build_service()

    result = service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a car wash",
            language_code="en",
        )
    )

    assert result.project_id == "project-1"
    assert result.status == "clarifying"
    assert "Car Wash CRM" in result.next_message
    assert fakes.user_repository.upserts == [
        {
            "telegram_user_id": 123,
            "telegram_username": None,
            "display_name": None,
            "language_code": "en",
        }
    ]
    assert fakes.memory_service.goals == [
        ("profile-1", "project-1", "Create a CRM for a car wash")
    ]
    assert [requirement[2] for requirement in fakes.memory_service.requirements] == [
        "customers",
        "appointments",
    ]
    stored_brief = fakes.project_repository.projects["project-1"]["brief"]
    assert isinstance(stored_brief, dict)
    assert stored_brief["product_brief"]["product_name"] == "Car Wash CRM"
    assert stored_brief["feature_prioritization"]["must_have"]
    assert stored_brief["roadmap"]["phases"][0]["name"] == "Phase 1 - MVP"
    assert stored_brief["product_memory"]["source_idea"] == "Create a CRM for a car wash"
    assert stored_brief["design_contract"]["visual_archetype"]["key"]
    assert stored_brief["design_contract"]["open_design_brief"]["prompt"]


def test_runtime_project_service_create_project_survives_transient_memory_write_failure(
) -> None:
    fakes = ServiceFakes(
        user_repository=FakeUserRepository(),
        project_repository=FakeProjectRepository(),
        memory_service=FakeMemoryService(),
        generation_orchestrator=FakeGenerationOrchestrator(),
        github_export_service=FakeGitHubExportService(),
        github_repository=FakeGitHubRepository(),
    )
    service = RuntimeProjectService(
        settings=settings(),
        user_repository=fakes.user_repository,
        project_repository=fakes.project_repository,
        memory_service=MemoryService(TransientFailingMemoryRepository()),
        llm_gateway=FakeLLMGateway(),
        template_registry=FakeTemplateRegistry(),
        generation_orchestrator=fakes.generation_orchestrator,
        github_export_service=fakes.github_export_service,
        github_repository=fakes.github_repository,
    )

    result = service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a car wash",
            language_code="en",
        )
    )

    assert result.project_id == "project-1"
    assert result.status == "clarifying"
    assert "Car Wash CRM" in result.next_message
    assert fakes.project_repository.projects["project-1"]["title"] == "Car Wash CRM"


def test_runtime_project_service_returns_structured_error_when_brief_llm_unavailable(
) -> None:
    service, fakes = build_service(llm_gateway=ProviderUnavailableLLMGateway())

    with pytest.raises(RuntimeProjectGenerationError) as exc_info:
        service.create_project(
            CreateProjectRequest(
                telegram_user_id=123,
                telegram_chat_id=456,
                idea="Create a CRM for a dental clinic",
                language_code="en",
            )
        )

    assert exc_info.value.project_id == "pending"
    assert exc_info.value.code == "llm_provider_unavailable"
    assert exc_info.value.to_response_payload() == {
        "project_id": "pending",
        "status": "failed",
        "error_code": "llm_provider_unavailable",
        "message": "No available LLM providers.",
        "error": {
            "code": "llm_provider_unavailable",
            "message": "No available LLM providers.",
        },
    }
    assert fakes.project_repository.projects == {}


def test_runtime_project_service_generates_github_export_from_internal_contract() -> None:
    service, fakes = build_service()
    service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a car wash",
            language_code="en",
        )
    )

    result = service.generate_project(
        "project-1",
        GenerateProjectRequest(answers={}, export="github"),
    )

    assert result.project_id == "project-1"
    assert result.status == "completed"
    assert result.template == "crm"
    assert result.github_url == "https://github.com/vuls/car-wash-crm"
    assert result.zip_artifact_id is None
    assert fakes.generation_orchestrator.calls[0]["template_key"] == "crm"
    memory_context = fakes.generation_orchestrator.calls[0]["memory_context"]
    assert isinstance(memory_context, dict)
    assert any(
        "Product brief:" in item
        for item in memory_context["project"]
    )
    assert any(
        "Feature priorities:" in item
        for item in memory_context["project"]
    )
    assert any(
        "Design Intelligence:" in item
        for item in memory_context["project"]
    )
    assert any(
        "Open Design prompt:" in item
        for item in memory_context["project"]
    )
    assert fakes.github_export_service.requests[0].owner == "vuls"
    assert fakes.project_repository.status_updates == [
        ("project-1", ProjectStatus.GENERATING),
        ("project-1", ProjectStatus.EXPORTING),
        ("project-1", ProjectStatus.COMPLETED),
    ]


def test_runtime_project_service_returns_structured_error_for_invalid_manifest_json() -> None:
    service, fakes = build_service(
        generation_orchestrator=InvalidJsonGenerationOrchestrator()
    )
    service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a fitness club",
            language_code="en",
        )
    )

    with pytest.raises(RuntimeProjectGenerationError) as exc_info:
        service.generate_project(
            "project-1",
            GenerateProjectRequest(answers={}, export="zip"),
        )

    assert exc_info.value.project_id == "project-1"
    assert exc_info.value.code == "llm_output_validation_failed"
    assert fakes.project_repository.status_updates == [
        ("project-1", ProjectStatus.GENERATING),
        ("project-1", ProjectStatus.FAILED),
    ]
    assert fakes.project_repository.projects["project-1"]["error"] == {
        "code": "llm_output_validation_failed",
        "message": "Vuls could not parse the generated project manifest. Please retry.",
    }


def test_runtime_project_service_reads_project_detail_with_repository_url() -> None:
    service, fakes = build_service()
    service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a car wash",
            language_code="en",
        )
    )
    fakes.github_repository.rows["project-1"] = {
        "html_url": "https://github.com/vuls/car-wash-crm"
    }

    result = service.get_project("project-1")

    assert result.project_id == "project-1"
    assert result.title == "Car Wash CRM"
    assert result.status == "clarifying"
    assert result.selected_template_key == "crm"
    assert result.repository_url == "https://github.com/vuls/car-wash-crm"
    assert result.updated_at == "2026-06-02T12:00:00Z"


def test_runtime_project_service_reads_product_brief_roadmap_and_memory() -> None:
    service, _fakes = build_service()
    service.create_project(
        CreateProjectRequest(
            telegram_user_id=123,
            telegram_chat_id=456,
            idea="Create a CRM for a dentistry clinic",
            language_code="en",
        )
    )

    brief_result = service.get_product_brief("project-1")
    roadmap_result = service.get_project_roadmap("project-1")
    memory_result = service.get_project_memory("project-1")

    assert brief_result.project_id == "project-1"
    assert brief_result.brief.product_name == "Car Wash CRM"
    assert roadmap_result.roadmap.phases[0].name == "Phase 1 - MVP"
    assert memory_result.memory.selected_template == "crm"
    assert memory_result.memory.product_brief.product_name == "Car Wash CRM"


@dataclass(frozen=True)
class ServiceFakes:
    user_repository: FakeUserRepository
    project_repository: FakeProjectRepository
    memory_service: FakeMemoryService
    generation_orchestrator: FakeGenerationOrchestrator
    github_export_service: FakeGitHubExportService
    github_repository: FakeGitHubRepository


def build_service(
    generation_orchestrator: FakeGenerationOrchestrator | None = None,
    llm_gateway: FakeLLMGateway | ProviderUnavailableLLMGateway | None = None,
) -> tuple[RuntimeProjectService, ServiceFakes]:
    fakes = ServiceFakes(
        user_repository=FakeUserRepository(),
        project_repository=FakeProjectRepository(),
        memory_service=FakeMemoryService(),
        generation_orchestrator=generation_orchestrator or FakeGenerationOrchestrator(),
        github_export_service=FakeGitHubExportService(),
        github_repository=FakeGitHubRepository(),
    )
    service = RuntimeProjectService(
        settings=settings(),
        user_repository=fakes.user_repository,
        project_repository=fakes.project_repository,
        memory_service=fakes.memory_service,
        llm_gateway=llm_gateway or FakeLLMGateway(),
        template_registry=FakeTemplateRegistry(),
        generation_orchestrator=fakes.generation_orchestrator,
        github_export_service=fakes.github_export_service,
        github_repository=fakes.github_repository,
    )
    return service, fakes


def settings() -> Settings:
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
        project_workdir="./var/projects",
    )


def sample_manifest() -> GeneratedProjectManifest:
    return GeneratedProjectManifest(
        project_name="car-wash-crm",
        readme_summary="CRM for a car wash.",
        tech_stack=["FastAPI", "React"],
        files=[
            GeneratedProjectFile(
                path="README.md",
                content="# Car Wash CRM\n",
                purpose="Project documentation",
            )
        ],
    )
