import inspect
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.api.dependencies import get_project_service
from vuls.api.routes import internal, projects, telegram
from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProductBriefResult,
    ProductMemoryResult,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
    ProjectRoadmapResult,
)
from vuls.core.config import AppEnv, Settings
from vuls.llm.schemas import ProjectBrief
from vuls.product_intelligence import build_product_intelligence
from vuls.runtime.project_service import RuntimeProjectGenerationError


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

    def get_product_brief(self, project_id: str) -> ProductBriefResult:
        intelligence = _sample_product_intelligence()
        return ProductBriefResult(
            project_id=project_id,
            brief=intelligence.product_brief,
        )

    def get_project_roadmap(self, project_id: str) -> ProjectRoadmapResult:
        intelligence = _sample_product_intelligence()
        return ProjectRoadmapResult(
            project_id=project_id,
            roadmap=intelligence.roadmap,
        )

    def get_project_memory(self, project_id: str) -> ProductMemoryResult:
        intelligence = _sample_product_intelligence()
        return ProductMemoryResult(
            project_id=project_id,
            memory=intelligence.product_memory,
        )


class FailingProjectService(FakeProjectService):
    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult:
        raise RuntimeProjectGenerationError(
            project_id="pending",
            code="llm_provider_unavailable",
            message="No available LLM providers.",
        )

    def generate_project(
        self, project_id: str, request: GenerateProjectRequest
    ) -> ProjectGenerationResult:
        raise RuntimeProjectGenerationError(
            project_id=project_id,
            code="llm_output_validation_failed",
            message="Vuls could not parse the generated project manifest. Please retry.",
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


def test_create_project_uses_runtime_project_service_by_default() -> None:
    app = _create_test_app()
    app.state.runtime = SimpleNamespace(project_service=FakeProjectService())
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


def test_generate_project_returns_structured_error_when_generation_fails() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FailingProjectService()
    client = TestClient(app)

    response = client.post(
        "/internal/projects/11111111-1111-1111-1111-111111111111/generate",
        json={"answers": {}, "export": "zip"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "project_id": "11111111-1111-1111-1111-111111111111",
        "status": "failed",
        "error_code": "llm_output_validation_failed",
        "message": "Vuls could not parse the generated project manifest. Please retry.",
        "error": {
            "code": "llm_output_validation_failed",
            "message": "Vuls could not parse the generated project manifest. Please retry.",
        },
    }


def test_create_project_returns_structured_error_when_llm_provider_is_unavailable() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FailingProjectService()
    client = TestClient(app)

    response = client.post(
        "/internal/projects",
        json={
            "telegram_user_id": 123456789,
            "telegram_chat_id": 123456789,
            "idea": "Create a CRM for a dental clinic",
            "language_code": "en",
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "project_id": "pending",
        "status": "failed",
        "error_code": "llm_provider_unavailable",
        "message": "No available LLM providers.",
        "error": {
            "code": "llm_provider_unavailable",
            "message": "No available LLM providers.",
        },
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


def test_product_brief_contract_validates_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.get("/internal/projects/11111111-1111-1111-1111-111111111111/brief")

    assert response.status_code == 200
    assert response.json()["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()["brief"]["product_name"] == "Coffee CRM"
    assert response.json()["brief"]["core_features"]
    assert response.json()["brief"]["success_metrics"]


def test_project_roadmap_contract_validates_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.get("/internal/projects/11111111-1111-1111-1111-111111111111/roadmap")

    assert response.status_code == 200
    assert response.json()["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert [phase["name"] for phase in response.json()["roadmap"]["phases"]] == [
        "Phase 1 - MVP",
        "Phase 2 - Growth",
        "Phase 3 - Scale",
    ]


def test_project_memory_contract_validates_response_shape() -> None:
    app = _create_test_app()
    app.dependency_overrides[get_project_service] = lambda: FakeProjectService()
    client = TestClient(app)

    response = client.get("/internal/projects/11111111-1111-1111-1111-111111111111/memory")

    assert response.status_code == 200
    assert response.json()["project_id"] == "11111111-1111-1111-1111-111111111111"
    assert response.json()["memory"]["source_idea"] == "Create a CRM for a coffee shop"
    assert response.json()["memory"]["selected_template"] == "crm"
    assert response.json()["memory"]["feature_prioritization"]["must_have"]


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


def _sample_product_intelligence():
    return build_product_intelligence(
        raw_idea="Create a CRM for a coffee shop",
        brief=ProjectBrief(
            title="Coffee CRM",
            goal="Create a CRM for a coffee shop",
            target_users=["owner", "staff"],
            must_have_features=["customers", "orders", "tasks"],
            language_code="en",
        ),
        selected_template_key="crm",
    )
