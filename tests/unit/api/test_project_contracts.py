import inspect
from pathlib import Path

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.api.dependencies import get_project_service
from vuls.api.routes import internal, projects, telegram
from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
)
from vuls.core.config import AppEnv, Settings


class FakeProjectService:
    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult:
        assert request.telegram_user_id == 123456789
        return ProjectCreateResult(
            project_id="11111111-1111-1111-1111-111111111111",
            status="clarifying",
            next_message="Who will use this CRM?",
        )

    def generate_project(
        self, project_id: str, request: GenerateProjectRequest
    ) -> ProjectGenerationResult:
        assert project_id == "11111111-1111-1111-1111-111111111111"
        assert request.export == "github"
        return ProjectGenerationResult(
            project_id=project_id,
            status="completed",
            template="crm",
            github_url="https://github.com/example/vuls-coffee-crm",
            zip_artifact_id=None,
        )

    def get_project(self, project_id: str) -> ProjectDetailResult:
        return ProjectDetailResult(
            project_id=project_id,
            title="Coffee CRM",
            status="completed",
            selected_template_key="crm",
            repository_url="https://github.com/example/vuls-coffee-crm",
            updated_at="2026-06-01T18:00:00Z",
        )


def test_create_project_contract_validates_request_and_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.post(
        "/internal/projects",
        json={
            "telegram_user_id": 123456789,
            "telegram_chat_id": 123456789,
            "idea": "Create a CRM for a small coffee shop",
            "language_code": "en",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "status": "clarifying",
        "next_message": "Who will use this CRM?",
    }


def test_create_project_contract_rejects_invalid_request_shape() -> None:
    client = TestClient(_create_test_app())

    response = client.post(
        "/internal/projects",
        json={
            "telegram_user_id": "not-an-int",
            "telegram_chat_id": 123456789,
            "idea": "",
            "language_code": "en",
        },
    )

    assert response.status_code == 422


def test_generate_project_contract_validates_request_and_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.post(
        "/internal/projects/11111111-1111-1111-1111-111111111111/generate",
        json={
            "answers": {
                "target_users": "owner and staff",
                "must_have_features": ["customers", "orders", "tasks"],
            },
            "export": "github",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "status": "completed",
        "template": "crm",
        "github_url": "https://github.com/example/vuls-coffee-crm",
        "zip_artifact_id": None,
    }


def test_project_status_contract_validates_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.get("/internal/projects/11111111-1111-1111-1111-111111111111")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "title": "Coffee CRM",
        "status": "completed",
        "selected_template_key": "crm",
        "repository_url": "https://github.com/example/vuls-coffee-crm",
        "updated_at": "2026-06-01T18:00:00Z",
    }


def test_routes_do_not_directly_import_external_clients() -> None:
    route_sources = "\n".join(
        inspect.getsource(module) for module in (internal, projects, telegram)
    ).lower()

    forbidden_imports = (
        "import openai",
        "from openai",
        "import supabase",
        "from supabase",
        "import github",
        "from github",
    )
    assert all(import_text not in route_sources for import_text in forbidden_imports)


def _create_test_app():
    return create_api_app(settings=_settings(), build_runtime=False)


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
        project_workdir=Path("var/projects"),
    )
