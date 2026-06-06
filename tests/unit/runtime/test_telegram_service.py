from dataclasses import dataclass
from pathlib import Path

from vuls.bot.messages import TelegramUserIdentity
from vuls.core.config import AppEnv, Settings
from vuls.db.models import ProjectStatus
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    GeneratedProjectFile,
    GeneratedProjectManifest,
    LLMUsage,
    ProjectBrief,
)
from vuls.memory.schemas import MemoryContext
from vuls.runtime.telegram_service import RuntimeTelegramFlowService
from vuls.templates.schemas import TemplateSelection


class FakeUserRepository:
    def __init__(self) -> None:
        self.profile = {
            "id": "profile-1",
            "telegram_user_id": 123,
            "telegram_username": "artel",
            "display_name": "Artel User",
            "language_code": "en",
        }
        self.upserts: list[dict[str, object]] = []
        self.lookups: list[int] = []

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

    def get_by_telegram_user_id(self, telegram_user_id: int) -> dict[str, object]:
        self.lookups.append(telegram_user_id)
        return dict(self.profile)


class FakeProjectRepository:
    def __init__(self) -> None:
        self.projects: dict[str, dict[str, object]] = {}
        self.created: list[dict[str, object]] = []
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
            "status": ProjectStatus.DRAFT.value,
            "selected_template_key": brief["selected_template_key"],
            "brief": brief,
            "updated_at": "2026-06-02T10:00:00Z",
        }
        self.created.append(project)
        self.projects["project-1"] = project
        return dict(project)

    def get_project(self, project_id: str) -> dict[str, object]:
        return dict(self.projects[project_id])

    def list_projects_for_owner(
        self,
        owner_profile_id: str,
        *,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        return [
            dict(project)
            for project in self.projects.values()
            if project["owner_profile_id"] == owner_profile_id
        ][:limit]

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
        self.project_goals: list[tuple[str, str, str]] = []
        self.requirements: list[tuple[str, str, str]] = []
        self.context_calls: list[tuple[str, str]] = []

    def record_project_goal(self, *, profile_id: str, project_id: str, goal: str) -> object:
        self.project_goals.append((profile_id, project_id, goal))
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


class FakeLLMGateway:
    def __init__(self) -> None:
        self.requests: list[BriefNormalizationRequest] = []

    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        self.requests.append(request)
        return BriefNormalizationResponse(
            brief=ProjectBrief(
                title="Car Wash CRM",
                goal=request.user_idea,
                target_users=["owner", "staff"],
                must_have_features=["customers", "appointments", "payments"],
                language_code=request.language_code,
            ),
            usage=LLMUsage(),
            model="gpt-test",
        )


class FakeTemplateRegistry:
    def __init__(self) -> None:
        self.intents: list[str] = []

    def select_template(self, user_intent: str) -> TemplateSelection:
        self.intents.append(user_intent)
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
                "generation_run_id": generation_run_id,
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


def test_runtime_flow_starts_project_from_telegram_request() -> None:
    service, fakes = build_service()
    identity = telegram_identity()

    result = service.start_new_project(identity, "Create a CRM for a car wash")

    assert fakes.user_repository.upserts == [
        {
            "telegram_user_id": 123,
            "telegram_username": "artel",
            "display_name": "Artel User",
            "language_code": "en",
        }
    ]
    assert fakes.llm_gateway.requests[0].user_idea == "Create a CRM for a car wash"
    assert fakes.template_registry.intents == ["Create a CRM for a car wash"]
    assert fakes.project_repository.created[0]["title"] == "Car Wash CRM"
    assert fakes.project_repository.created[0]["slug"] == "car-wash-crm"
    assert fakes.project_repository.created[0]["brief"]["selected_template_key"] == "crm"
    assert (
        fakes.project_repository.created[0]["brief"]["design_contract"]["visual_archetype"]["key"]
    )
    assert (
        fakes.project_repository.created[0]["brief"]["design_contract"]["open_design_brief"][
            "prompt"
        ]
    )
    assert fakes.memory_service.project_goals == [
        ("profile-1", "project-1", "Create a CRM for a car wash")
    ]
    assert [item[2] for item in fakes.memory_service.requirements] == [
        "customers",
        "appointments",
        "payments",
    ]
    assert result.project_id == "project-1"
    assert result.status == "draft"
    assert result.recommended_template == "crm"
    assert "Car Wash CRM" in result.message


def test_runtime_flow_generates_zip_through_generation_service() -> None:
    service, fakes = build_service()
    service.start_new_project(telegram_identity(), "Create a CRM for a car wash")

    result = service.generate_project(telegram_identity(), "project-1", "zip")

    assert result.status == "completed"
    assert result.template == "crm"
    assert result.zip_artifact_id == "zip-artifact-1"
    assert result.github_url is None
    assert fakes.generation_orchestrator.calls[0]["template_key"] == "crm"
    assert fakes.generation_orchestrator.calls[0]["brief"] == ProjectBrief(
        title="Car Wash CRM",
        goal="Create a CRM for a car wash",
        target_users=["owner", "staff"],
        must_have_features=["customers", "appointments", "payments"],
        language_code="en",
    )
    assert fakes.memory_service.context_calls == [("profile-1", "project-1")]
    memory_context = fakes.generation_orchestrator.calls[0]["memory_context"]
    assert isinstance(memory_context, dict)
    assert any(
        "Design Intelligence:" in item
        for item in memory_context["project"]
    )
    assert fakes.project_repository.status_updates == [
        ("project-1", ProjectStatus.GENERATING),
        ("project-1", ProjectStatus.COMPLETED),
    ]
    assert fakes.github_export_service.requests == []


def test_runtime_flow_exports_github_through_github_service() -> None:
    service, fakes = build_service()
    service.start_new_project(telegram_identity(), "Create a CRM for a car wash")

    result = service.generate_project(telegram_identity(), "project-1", "github")

    assert result.status == "completed"
    assert result.github_url == "https://github.com/vuls/car-wash-crm"
    request = fakes.github_export_service.requests[0]
    assert request.project_id == "project-1"
    assert request.owner == "vuls"
    assert request.repo_name == "Car Wash CRM"
    assert request.private is True
    assert request.manifest.project_name == "car-wash-crm"
    assert fakes.project_repository.status_updates == [
        ("project-1", ProjectStatus.GENERATING),
        ("project-1", ProjectStatus.EXPORTING),
        ("project-1", ProjectStatus.COMPLETED),
    ]


def test_runtime_flow_lists_recent_projects_and_active_project() -> None:
    service, _fakes = build_service()
    service.start_new_project(telegram_identity(), "Create a CRM for a car wash")

    recent = service.list_recent_projects(telegram_identity())
    active = service.get_active_project(telegram_identity())

    assert [(project.project_id, project.title, project.status) for project in recent] == [
        ("project-1", "Car Wash CRM", "draft")
    ]
    assert active is not None
    assert active.project_id == "project-1"
    assert active.title == "Car Wash CRM"
    assert active.template == "crm"


@dataclass(frozen=True)
class ServiceFakes:
    user_repository: FakeUserRepository
    project_repository: FakeProjectRepository
    memory_service: FakeMemoryService
    llm_gateway: FakeLLMGateway
    template_registry: FakeTemplateRegistry
    generation_orchestrator: FakeGenerationOrchestrator
    github_export_service: FakeGitHubExportService


def build_service() -> tuple[RuntimeTelegramFlowService, ServiceFakes]:
    fakes = ServiceFakes(
        user_repository=FakeUserRepository(),
        project_repository=FakeProjectRepository(),
        memory_service=FakeMemoryService(),
        llm_gateway=FakeLLMGateway(),
        template_registry=FakeTemplateRegistry(),
        generation_orchestrator=FakeGenerationOrchestrator(),
        github_export_service=FakeGitHubExportService(),
    )
    service = RuntimeTelegramFlowService(
        settings=settings(),
        user_repository=fakes.user_repository,
        project_repository=fakes.project_repository,
        memory_service=fakes.memory_service,
        llm_gateway=fakes.llm_gateway,
        template_registry=fakes.template_registry,
        generation_orchestrator=fakes.generation_orchestrator,
        github_export_service=fakes.github_export_service,
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
        project_workdir=Path("var/projects"),
    )


def telegram_identity() -> TelegramUserIdentity:
    return TelegramUserIdentity(
        telegram_user_id=123,
        telegram_chat_id=456,
        username="artel",
        display_name="Artel User",
        language_code="en",
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
