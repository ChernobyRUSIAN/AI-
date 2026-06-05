from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings
from vuls.github.schemas import GitHubExportRequest, GitHubRepository
from vuls.llm.schemas import (
    GeneratedProjectFile,
    GeneratedProjectManifest,
    LLMClientResponse,
    LLMMessage,
)
from vuls.main import create_app
from vuls.runtime.container import build_runtime_container
from vuls.runtime.validation import RuntimeValidationError


class FakeSupabaseClient:
    def table(self, table_name: str) -> object:
        raise AssertionError(f"Unexpected Supabase query during container build: {table_name}")


class FakeLLMClient:
    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse:
        raise AssertionError("Unexpected LLM call during container build")


class FakeGitHubClient:
    def __init__(self) -> None:
        self.created_repositories: list[dict[str, object]] = []
        self.files: list[str] = []

    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository:
        self.created_repositories.append(
            {
                "owner": owner,
                "repo_name": repo_name,
                "private": private,
                "description": description,
                "default_branch": default_branch,
            }
        )
        return GitHubRepository(
            owner=owner,
            repo_name=repo_name,
            html_url=f"https://github.com/{owner}/{repo_name}",
            default_branch=default_branch,
        )

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
        self.files.append(path)
        return f"sha-{len(self.files)}"


class FakeResult:
    def __init__(self, data: object) -> None:
        self.data = data


class FakeQuery:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def upsert(self, payload: dict[str, object], on_conflict: str | None = None) -> "FakeQuery":
        self.calls.append(("upsert", (payload, on_conflict)))
        return self

    def execute(self) -> FakeResult:
        return FakeResult([{"id": "repository-1"}])


class FakeRepositoryMetadataSupabaseClient:
    def __init__(self) -> None:
        self.tables: list[str] = []
        self.query = FakeQuery()

    def table(self, table_name: str) -> FakeQuery:
        self.tables.append(table_name)
        return self.query


class FakeConfiguredOpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: int,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse:
        raise AssertionError("Unexpected LLM call during container build")


def test_build_runtime_container_wires_existing_runtime_boundaries(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)
    supabase_client = FakeSupabaseClient()
    llm_client = FakeLLMClient()
    github_client = FakeGitHubClient()

    container = build_runtime_container(
        settings=settings,
        supabase_client=supabase_client,
        llm_client=llm_client,
        github_client=github_client,
    )

    assert container.settings is settings
    assert container.supabase_client is supabase_client
    assert container.llm_client is llm_client
    assert container.github_client is github_client
    assert container.template_registry.get("crm").key == "crm"
    assert container.project_workdir == tmp_path / "projects"
    assert container.artifact_dir == tmp_path / "artifacts"
    assert container.generation_orchestrator is not None
    assert container.github_export_service is not None
    assert container.github_repository is not None
    assert container.memory_service is not None
    assert container.project_service is not None
    assert container.telegram_flow_service is not None
    assert container.telegram_dispatcher is not None
    assert container.telegram_sender is not None


def test_build_runtime_container_passes_openai_base_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "vuls.runtime.container.OpenAIResponsesClient",
        FakeConfiguredOpenAIResponsesClient,
    )

    container = build_runtime_container(
        settings=runtime_settings(
            tmp_path,
            openai_base_url="https://openrouter.ai/api/v1",
        ),
        supabase_client=FakeSupabaseClient(),
        github_client=FakeGitHubClient(),
    )

    assert isinstance(container.llm_client, FakeConfiguredOpenAIResponsesClient)
    assert container.llm_client.api_key == "openai-key"
    assert container.llm_client.base_url == "https://openrouter.ai/api/v1"
    assert container.llm_client.timeout_seconds == 60


def test_create_api_app_loads_runtime_settings_secret_and_container(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path, telegram_webhook_secret="from-env-secret")
    container = build_runtime_container(
        settings=settings,
        supabase_client=FakeSupabaseClient(),
        llm_client=FakeLLMClient(),
        github_client=FakeGitHubClient(),
    )

    app = create_api_app(settings=settings, runtime=container)

    assert app.state.settings is settings
    assert app.state.runtime is container
    assert app.state.telegram_webhook_secret == "from-env-secret"
    assert app.state.runtime_validation.ready is True

    client = TestClient(app)
    invalid_response = client.post("/webhooks/telegram/wrong-secret", json={"update_id": 1})
    valid_response = client.post("/webhooks/telegram/from-env-secret", json={"update_id": 1})

    assert invalid_response.status_code == 403
    assert valid_response.status_code == 200
    assert valid_response.json() == {"ok": True}


def test_create_api_app_rejects_invalid_runtime_settings(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)
    invalid_settings = settings.model_copy(update={"openai_api_key": ""})

    try:
        create_api_app(settings=invalid_settings, build_runtime=False)
    except RuntimeValidationError as exc:
        assert "OPENAI_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected invalid startup settings to be rejected")


def test_main_create_app_uses_routed_api_app(tmp_path: Path) -> None:
    settings = runtime_settings(tmp_path)
    container = build_runtime_container(
        settings=settings,
        supabase_client=FakeSupabaseClient(),
        llm_client=FakeLLMClient(),
        github_client=FakeGitHubClient(),
    )

    app = create_app(settings=settings, runtime=container)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["version"] == "v1.0"


def test_runtime_container_wires_github_export_metadata_store(tmp_path: Path) -> None:
    supabase_client = FakeRepositoryMetadataSupabaseClient()
    github_client = FakeGitHubClient()
    container = build_runtime_container(
        settings=runtime_settings(tmp_path),
        supabase_client=supabase_client,
        llm_client=FakeLLMClient(),
        github_client=github_client,
    )

    result = container.github_export_service.export_project(
        GitHubExportRequest(
            project_id="11111111-1111-1111-1111-111111111111",
            owner="acme",
            repo_name="Coffee CRM",
            manifest=GeneratedProjectManifest(
                project_name="coffee-crm",
                readme_summary="CRM for a small coffee shop.",
                tech_stack=["FastAPI", "React"],
                files=[
                    GeneratedProjectFile(
                        path="README.md",
                        content="# Coffee CRM\n",
                        purpose="Project documentation",
                    )
                ],
            ),
            private=True,
        )
    )

    assert result.html_url == "https://github.com/acme/coffee-crm"
    assert supabase_client.tables == ["repositories"]
    assert supabase_client.query.calls == [
        (
            "upsert",
            (
                {
                    "project_id": "11111111-1111-1111-1111-111111111111",
                    "provider": "github",
                    "owner": "acme",
                    "repo_name": "coffee-crm",
                    "html_url": "https://github.com/acme/coffee-crm",
                    "default_branch": "main",
                },
                "project_id",
            ),
        )
    ]


def runtime_settings(
    tmp_path: Path,
    *,
    telegram_webhook_secret: str = "telegram-webhook-secret",
    openai_base_url: str = "https://api.openai.com/v1",
) -> Settings:
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
        openai_base_url=openai_base_url,
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir=tmp_path / "projects",
        github_api_base_url="https://api.github.com",
    )
