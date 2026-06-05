import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from vuls.bot.dispatcher import TelegramDispatcher
from vuls.bot.messages import (
    ProjectGenerationReply,
    ProjectIntakeResult,
    ProjectStatusView,
    ProjectSummary,
    TelegramUserIdentity,
)
from vuls.db.client import JsonObject
from vuls.db.models import ArtifactType, MemorySource, MemoryType
from vuls.db.repositories.artifacts import ArtifactRepositoryTransientError
from vuls.generation.orchestrator import ProjectGenerationOrchestrator
from vuls.github.schemas import GitHubExportRequest, GitHubRepository
from vuls.github.service import GitHubExportError, GitHubExportService
from vuls.llm.gateway import LLMGateway, LLMGatewayError
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    GeneratedProjectManifest,
    LLMClientResponse,
    LLMMessage,
    ProjectBrief,
)
from vuls.memory.schemas import (
    ConversationDirection,
    ConversationMessage,
    ConversationMessageType,
)
from vuls.memory.service import MemoryService
from vuls.templates.registry import TemplateRegistry


@dataclass
class FakeUser:
    id: int
    username: str | None = None
    full_name: str | None = None
    language_code: str | None = None


@dataclass
class FakeChat:
    id: int


@dataclass
class FakeMessage:
    text: str
    from_user: FakeUser
    chat: FakeChat


@dataclass
class FakeCallback:
    data: str
    from_user: FakeUser
    message: FakeMessage


@dataclass
class E2EProjectState:
    project_id: str
    title: str
    status: str
    template_key: str
    brief: ProjectBrief
    export: Literal["zip", "github"] | None = None
    url: str | None = None
    zip_artifact_id: str | None = None
    workspace_path: Path | None = None
    zip_path: Path | None = None


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self.rows: list[JsonObject] = []

    def load_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[JsonObject]:
        matches = [
            row
            for row in self.rows
            if row["profile_id"] == profile_id
            and row["project_id"] == project_id
            and (memory_type is None or row["memory_type"] == memory_type)
        ]
        return matches[-limit:] if limit > 0 else []

    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: dict[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject:
        row: JsonObject = {
            "id": f"memory-{len(self.rows) + 1}",
            "profile_id": profile_id,
            "project_id": project_id,
            "memory_type": memory_type,
            "source": source,
            "content": content,
            "summary": summary,
            "confidence": confidence,
        }
        self.rows.append(row)
        return row


class FakeLLMClient:
    def __init__(self, responses: list[LLMClientResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[object],
    ) -> LLMClientResponse:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "response_schema": response_schema,
            }
        )
        return self.responses.pop(0)


class FakeArtifactRepository:
    def __init__(self) -> None:
        self.records: list[JsonObject] = []

    def create_artifact(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: dict[str, Any] | None = None,
    ) -> JsonObject:
        record: JsonObject = {
            "id": f"artifact-{len(self.records) + 1}",
            "project_id": project_id,
            "artifact_type": artifact_type,
            "generation_run_id": generation_run_id,
            "storage_path": storage_path,
            "content": content or {},
        }
        self.records.append(record)
        return record


class FailingArtifactRepository:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_artifact(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: dict[str, Any] | None = None,
    ) -> JsonObject:
        self.calls.append(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "generation_run_id": generation_run_id,
                "storage_path": storage_path,
                "content": content or {},
            }
        )
        raise ArtifactRepositoryTransientError(
            "Supabase artifacts insert failed after 3 attempts."
        )


class FakeGitHubClient:
    def __init__(self, *, fail_put_file: bool = False) -> None:
        self.fail_put_file = fail_put_file
        self.repositories: list[GitHubRepository] = []
        self.files: dict[str, str] = {}

    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository:
        repository = GitHubRepository(
            owner=owner,
            repo_name=repo_name,
            html_url=f"https://github.com/{owner}/{repo_name}",
            default_branch=default_branch,
        )
        self.repositories.append(repository)
        return repository

    def put_file(
        self,
        *,
        owner: str,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> str:
        if self.fail_put_file:
            from vuls.github.client import GitHubApiError

            raise GitHubApiError("provider detail must not reach the user")
        self.files[path] = content
        return f"sha-{len(self.files)}"


class FakeRepositoryMetadataStore:
    def __init__(self) -> None:
        self.records: list[JsonObject] = []

    def save_repository_metadata(
        self,
        *,
        project_id: str,
        owner: str,
        repo_name: str,
        html_url: str,
        default_branch: str,
    ) -> None:
        self.records.append(
            {
                "project_id": project_id,
                "owner": owner,
                "repo_name": repo_name,
                "html_url": html_url,
                "default_branch": default_branch,
            }
        )


class VulsMvpE2EService:
    def __init__(
        self,
        *,
        tmp_path: Path,
        llm_client: FakeLLMClient,
        github_client: FakeGitHubClient | None = None,
        artifact_repository: FakeArtifactRepository | FailingArtifactRepository | None = None,
    ) -> None:
        self.memory_repository = InMemoryMemoryRepository()
        self.memory = MemoryService(self.memory_repository)
        self.template_registry = TemplateRegistry()
        self.llm_client = llm_client
        self.llm_gateway = LLMGateway(client=llm_client, model="gpt-test", max_attempts=1)
        self.artifacts = artifact_repository or FakeArtifactRepository()
        self.generation = ProjectGenerationOrchestrator(
            gateway=self.llm_gateway,
            template_registry=self.template_registry,
            artifact_repository=self.artifacts,
            project_workdir=tmp_path / "workspaces",
            artifact_dir=tmp_path / "artifacts",
            zip_max_bytes=50_000,
        )
        self.github_metadata = FakeRepositoryMetadataStore()
        self.github_client = github_client or FakeGitHubClient()
        self.github = GitHubExportService(
            client=self.github_client,
            metadata_store=self.github_metadata,
        )
        self.projects: dict[str, E2EProjectState] = {}
        self.registered_users: list[TelegramUserIdentity] = []

    def register_user(self, identity: TelegramUserIdentity) -> None:
        self.registered_users.append(identity)

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult:
        project_id = f"project-{len(self.projects) + 1}"
        profile_id = _profile_id(identity)
        selection = self.template_registry.select_template(idea)
        template_key = selection.selected_key or "saas"

        self.memory.record_project_goal(
            profile_id=profile_id,
            project_id=project_id,
            goal=idea,
        )
        self.memory.record_extracted_requirement(
            profile_id=profile_id,
            project_id=project_id,
            requirement=f"Use the {template_key} product template.",
        )
        context = self.memory.build_context(profile_id=profile_id, project_id=project_id)
        brief_response = self.llm_gateway.normalize_brief(
            BriefNormalizationRequest(
                user_idea=idea,
                language_code=identity.language_code,
                memory_context=context.to_prompt_context(),
            )
        )
        self.memory.record_conversation_summary(
            profile_id=profile_id,
            project_id=project_id,
            messages=[
                ConversationMessage(
                    direction=ConversationDirection.INBOUND,
                    message_type=ConversationMessageType.COMMAND,
                    text=f"/new {idea}",
                ),
                ConversationMessage(
                    direction=ConversationDirection.OUTBOUND,
                    message_type=ConversationMessageType.TEXT,
                    text=f"Selected {template_key} template.",
                ),
            ],
        )
        self.projects[project_id] = E2EProjectState(
            project_id=project_id,
            title=brief_response.brief.title,
            status="clarifying",
            template_key=template_key,
            brief=brief_response.brief,
        )

        return ProjectIntakeResult(
            project_id=project_id,
            status="clarifying",
            message="Vuls prepared your project brief.",
            recommended_template=template_key,
        )

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply:
        project = self.projects[project_id]
        profile_id = _profile_id(identity)
        context = self.memory.build_context(profile_id=profile_id, project_id=project_id)
        try:
            result = self.generation.generate_project(
                project_id=project_id,
                generation_run_id=f"run-{project_id}",
                template_key=project.template_key,
                brief=project.brief,
                memory_context=context.to_prompt_context(),
            )
            project.workspace_path = result.workspace_path
            project.zip_path = result.zip_path
            project.zip_artifact_id = result.zip_artifact_id
            project.export = export

            github_url = None
            if export == "github":
                github_result = self.github.export_project(
                    GitHubExportRequest(
                        project_id=project_id,
                        owner="acme",
                        repo_name=result.build.manifest.project_name,
                        manifest=result.build.manifest,
                        private=True,
                    )
                )
                github_url = github_result.html_url
                project.url = github_url

            project.status = "completed"
            return ProjectGenerationReply(
                project_id=project_id,
                status="completed",
                template=project.template_key,
                github_url=github_url,
                zip_artifact_id=result.zip_artifact_id if export == "zip" else None,
            )
        except (LLMGatewayError, GitHubExportError):
            project.status = "failed"
            return ProjectGenerationReply(
                project_id=project_id,
                status="failed",
                template=project.template_key,
            )

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]:
        return [
            ProjectSummary(
                project_id=project.project_id,
                title=project.title,
                status=project.status,
            )
            for project in self.projects.values()
        ]

    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None:
        if not self.projects:
            return None
        project = next(reversed(self.projects.values()))
        return ProjectStatusView(
            project_id=project.project_id,
            title=project.title,
            status=project.status,
            template=project.template_key,
            export=project.export,
            url=project.url,
        )


def test_vuls_v1_e2e_zip_flow_validates_complete_mvp_path(tmp_path: Path) -> None:
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(project_brief_payload())),
            LLMClientResponse(content=json.dumps(project_manifest_payload())),
        ]
    )
    service = VulsMvpE2EService(tmp_path=tmp_path, llm_client=llm_client)
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    start_reply = dispatcher.dispatch_message(FakeMessage("/start", user, chat))
    intake_reply = dispatcher.dispatch_message(
        FakeMessage("/new Create a CRM for a coffee shop with customers and orders", user, chat)
    )
    zip_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:zip:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )
    projects_reply = dispatcher.dispatch_message(FakeMessage("/projects", user, chat))
    status_reply = dispatcher.dispatch_message(FakeMessage("/status", user, chat))

    assert service.registered_users[0].telegram_user_id == 123
    assert "New project" in start_reply.text
    assert "Recommended template: crm" in intake_reply.text
    assert zip_reply.text == "\n".join(
        [
            "Project project-1 completed.",
            "Template: crm",
            "ZIP artifact: artifact-2",
        ]
    )
    assert "Coffee CRM" in projects_reply.text
    assert "Export: zip" in status_reply.text

    project = service.projects["project-1"]
    assert project.zip_path is not None
    with zipfile.ZipFile(project.zip_path) as archive:
        archive_names = set(archive.namelist())
        customers_page = archive.read("src/app/customers/page.tsx").decode("utf-8")
        dashboard_page = archive.read("src/app/dashboard/page.tsx").decode("utf-8")
        orders_page = archive.read("src/app/orders/page.tsx").decode("utf-8")
        tasks_page = archive.read("src/app/tasks/page.tsx").decode("utf-8")
        schema_sql = archive.read("schema.sql").decode("utf-8")

    assert {
        "README.md",
        "package.json",
        "tailwind.config.ts",
        "schema.sql",
        "env.example",
        "src/app/dashboard/page.tsx",
        "src/app/customers/actions.ts",
        "src/app/customers/page.tsx",
        "src/app/orders/actions.ts",
        "src/app/orders/page.tsx",
        "src/app/tasks/actions.ts",
        "src/app/tasks/page.tsx",
        "src/lib/database.types.ts",
        "src/lib/supabase.ts",
    }.issubset(archive_names)
    assert "Add customer" in customers_page
    assert "listCustomers" in customers_page
    assert "createCustomer" in customers_page
    assert "Total Customers" in dashboard_page
    assert "Open Orders" in dashboard_page
    assert "listOrders" in orders_page
    assert "order.status" in orders_page
    assert "listTasks" in tasks_page
    assert "task.status" in tasks_page
    assert "public.customers" in schema_sql
    assert "public.orders" in schema_sql
    assert "public.tasks" in schema_sql

    assert [row["memory_type"] for row in service.memory_repository.rows] == [
        MemoryType.PROJECT,
        MemoryType.PROJECT,
        MemoryType.CONVERSATION,
    ]
    assert service.llm_client.calls[0]["response_schema"] is ProjectBrief
    assert service.llm_client.calls[1]["response_schema"] is GeneratedProjectManifest
    manifest_request_message = service.llm_client.calls[1]["messages"][-1]
    assert isinstance(manifest_request_message, LLMMessage)
    assert "Build a CRM for a coffee shop." in manifest_request_message.content
    assert service.artifacts.records[1]["artifact_type"] == ArtifactType.ZIP


def test_vuls_v1_e2e_zip_flow_recovers_malformed_fitness_club_manifest_json(
    tmp_path: Path,
) -> None:
    malformed_manifest = (
        "Here is the manifest:\n"
        f"{json.dumps(project_manifest_payload())[:-1]}\n"
    )
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(fitness_club_brief_payload())),
            LLMClientResponse(content=malformed_manifest),
        ]
    )
    service = VulsMvpE2EService(tmp_path=tmp_path, llm_client=llm_client)
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    dispatcher.dispatch_message(
        FakeMessage(
            "/new Create a CRM for a fitness club with members and subscriptions",
            user,
            chat,
        )
    )
    zip_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:zip:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )

    assert zip_reply.text == "\n".join(
        [
            "Project project-1 completed.",
            "Template: crm",
            "ZIP artifact: artifact-2",
        ]
    )
    project = service.projects["project-1"]
    assert project.zip_path is not None
    with zipfile.ZipFile(project.zip_path) as archive:
        archive_names = set(archive.namelist())
        schema_sql = archive.read("schema.sql").decode("utf-8")

    assert "src/lib/supabase.ts" in archive_names
    assert "src/app/customers/actions.ts" in archive_names
    assert "src/app/orders/actions.ts" in archive_names
    assert "public.customers" in schema_sql


def test_vuls_v1_e2e_failure_path_returns_user_safe_telegram_error(tmp_path: Path) -> None:
    llm_client = FakeLLMClient(
        [
            LLMClientResponse(content=json.dumps(project_brief_payload())),
            LLMClientResponse(content="not valid json"),
        ]
    )
    service = VulsMvpE2EService(tmp_path=tmp_path, llm_client=llm_client)
    dispatcher = TelegramDispatcher(service)
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    dispatcher.dispatch_message(
        FakeMessage("/new Create a CRM for a coffee shop with customers and orders", user, chat)
    )
    failure_reply = dispatcher.dispatch_callback(
        FakeCallback(
            data="export:zip:project-1",
            from_user=user,
            message=FakeMessage("", user, chat),
        )
    )

    assert failure_reply.text == "\n".join(
        [
            "Project project-1 could not be completed safely. "
            "Please try again or refine the request.",
            "Template: crm",
        ]
    )
    assert "not valid json" not in failure_reply.text
    assert "Model output" not in failure_reply.text
    assert service.projects["project-1"].status == "failed"


def project_brief_payload() -> dict[str, object]:
    return {
        "title": "Coffee CRM",
        "goal": "Build a CRM for a coffee shop.",
        "target_users": ["owner", "staff"],
        "must_have_features": ["customers", "orders", "tasks"],
        "language_code": "en",
    }


def fitness_club_brief_payload() -> dict[str, object]:
    return {
        "title": "Fitness Club CRM",
        "goal": "Build a CRM for a fitness club.",
        "target_users": ["owner", "trainers"],
        "must_have_features": ["members", "subscriptions", "tasks"],
        "language_code": "en",
    }


def project_manifest_payload() -> dict[str, object]:
    return {
        "project_name": "coffee-crm",
        "readme_summary": "CRM for a small coffee shop.",
        "tech_stack": ["FastAPI", "React"],
        "files": [
            {
                "path": "README.md",
                "content": "# Coffee CRM\n",
                "purpose": "Project documentation",
            },
            {
                "path": "src/main.py",
                "content": "print('hello')\n",
                "purpose": "Application entry point",
            },
            {
                "path": "src/routes/customers.py",
                "content": "def list_customers():\n    return []\n",
                "purpose": "Customer route stub",
            },
        ],
    }


def _profile_id(identity: TelegramUserIdentity) -> str:
    return f"telegram:{identity.telegram_user_id}"
