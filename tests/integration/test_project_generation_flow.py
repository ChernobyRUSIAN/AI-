import zipfile
from typing import Any

from vuls.db.models import ArtifactType
from vuls.generation.orchestrator import ProjectGenerationOrchestrator
from vuls.llm.schemas import (
    GeneratedEnvironmentVariable,
    GeneratedProjectFile,
    GeneratedProjectManifest,
    LLMUsage,
    ProjectBrief,
    ProjectManifestRequest,
    ProjectManifestResponse,
)
from vuls.templates.registry import TemplateRegistry


class FakeGateway:
    def __init__(self) -> None:
        self.requests: list[ProjectManifestRequest] = []

    def generate_project_manifest(
        self,
        request: ProjectManifestRequest,
    ) -> ProjectManifestResponse:
        self.requests.append(request)
        return ProjectManifestResponse(
            model="mock-model",
            usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            manifest=GeneratedProjectManifest(
                project_name="coffee-crm",
                readme_summary="CRM for a small coffee shop.",
                tech_stack=["FastAPI", "React"],
                files=[
                    GeneratedProjectFile(
                        path="README.md",
                        content="# Coffee CRM\n",
                        purpose="Project documentation",
                    ),
                    GeneratedProjectFile(
                        path="src/main.py",
                        content="print('hello')\n",
                        purpose="Application entry point",
                    ),
                ],
                env_vars=[
                    GeneratedEnvironmentVariable(
                        name="DATABASE_URL",
                        description="Database connection string",
                        required=True,
                    )
                ],
            ),
        )


class FakeArtifactRepository:
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
    ) -> dict[str, Any]:
        artifact_id = f"artifact-{len(self.calls) + 1}"
        self.calls.append(
            {
                "project_id": project_id,
                "artifact_type": artifact_type,
                "generation_run_id": generation_run_id,
                "storage_path": storage_path,
                "content": content,
            }
        )
        return {"id": artifact_id}


def test_project_generation_flow_uses_gateway_builds_zip_and_records_artifacts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    gateway = FakeGateway()
    artifact_repository = FakeArtifactRepository()
    orchestrator = ProjectGenerationOrchestrator(
        gateway=gateway,
        template_registry=TemplateRegistry(),
        artifact_repository=artifact_repository,
        project_workdir=tmp_path / "workspaces",
        artifact_dir=tmp_path / "artifacts",
        zip_max_bytes=50_000,
    )

    result = orchestrator.generate_project(
        project_id="project-1",
        generation_run_id="run-1",
        template_key="crm",
        brief=ProjectBrief(
            title="Coffee CRM",
            goal="Create a CRM for a small coffee shop",
            target_users=["owner", "staff"],
            must_have_features=["customers", "orders", "tasks"],
            language_code="en",
        ),
        memory_context={"project": ["Selected CRM template."]},
    )

    assert gateway.requests[0].template.key == "crm"
    assert gateway.requests[0].memory_context == {"project": ["Selected CRM template."]}
    assert result.project_id == "project-1"
    assert result.template_key == "crm"
    assert result.manifest_artifact_id == "artifact-1"
    assert result.zip_artifact_id == "artifact-2"
    assert result.workspace_path.joinpath("src/main.py").read_text(encoding="utf-8") == (
        "print('hello')\n"
    )
    with zipfile.ZipFile(result.zip_path) as archive:
        assert sorted(archive.namelist()) == ["README.md", "src/main.py"]

    assert artifact_repository.calls[0]["artifact_type"] == ArtifactType.MANIFEST
    assert artifact_repository.calls[0]["content"] == result.manifest.model_dump(mode="json")
    assert artifact_repository.calls[1]["artifact_type"] == ArtifactType.ZIP
    assert artifact_repository.calls[1]["storage_path"] == str(result.zip_path)
