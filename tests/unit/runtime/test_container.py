from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import BaseModel

from vuls.api.app import create_api_app
from vuls.core.config import AppEnv, Settings
from vuls.llm.schemas import LLMClientResponse, LLMMessage
from vuls.main import create_app
from vuls.runtime.container import build_runtime_container


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
    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> object:
        raise AssertionError("Unexpected GitHub repository creation during container build")

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
        raise AssertionError("Unexpected GitHub file write during container build")


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
    assert container.memory_service is not None


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

    client = TestClient(app)
    invalid_response = client.post("/webhooks/telegram/wrong-secret", json={"update_id": 1})
    valid_response = client.post("/webhooks/telegram/from-env-secret", json={"update_id": 1})

    assert invalid_response.status_code == 403
    assert valid_response.status_code == 200
    assert valid_response.json() == {"ok": True}


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


def runtime_settings(
    tmp_path: Path,
    *,
    telegram_webhook_secret: str = "telegram-webhook-secret",
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
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir=tmp_path / "projects",
        github_api_base_url="https://api.github.com",
    )
