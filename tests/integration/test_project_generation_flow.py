import zipfile
from typing import Any

from vuls.db.models import ArtifactType
from vuls.db.repositories.artifacts import ArtifactRepositoryTransientError
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
                    GeneratedProjectFile(
                        path="src/app/page.tsx",
                        content=(
                            "import { useRouter } from 'next/router';\n"
                            "import { useEffect } from 'react';\n\n"
                            "export default function Page() {\n"
                            "  const router = useRouter();\n"
                            "  useEffect(() => {\n"
                            "    router.push('/dashboard');\n"
                            "  }, [router]);\n"
                            "  return <main>Redirecting</main>;\n"
                            "}\n"
                        ),
                        purpose="Model-generated incompatible App Router page.",
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


class ManifestFailingArtifactRepository(FakeArtifactRepository):
    def create_artifact(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if artifact_type == ArtifactType.MANIFEST:
            self.calls.append(
                {
                    "project_id": project_id,
                    "artifact_type": artifact_type,
                    "generation_run_id": generation_run_id,
                    "storage_path": storage_path,
                    "content": content,
                }
            )
            raise ArtifactRepositoryTransientError(
                "Supabase artifacts insert failed after 3 attempts."
            )
        return super().create_artifact(
            project_id=project_id,
            artifact_type=artifact_type,
            generation_run_id=generation_run_id,
            storage_path=storage_path,
            content=content,
        )


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
    assert "Add customer" in result.workspace_path.joinpath(
        "src/app/customers/page.tsx"
    ).read_text(encoding="utf-8")
    assert "src/lib/mock-data.ts" not in {
        path.relative_to(result.workspace_path).as_posix()
        for path in result.workspace_path.rglob("*")
        if path.is_file()
    }
    assert "createClient" in result.workspace_path.joinpath(
        "src/lib/supabase.ts"
    ).read_text(encoding="utf-8")
    assert "public.customers" in result.workspace_path.joinpath(
        "schema.sql"
    ).read_text(encoding="utf-8")
    assert "Total Customers" in result.workspace_path.joinpath(
        "src/app/dashboard/page.tsx"
    ).read_text(encoding="utf-8")
    assert "order.status" in result.workspace_path.joinpath(
        "src/app/orders/page.tsx"
    ).read_text(encoding="utf-8")
    app_files = list(result.workspace_path.glob("src/app/**/*.tsx"))
    assert app_files
    assert all("next/router" not in path.read_text(encoding="utf-8") for path in app_files)
    with zipfile.ZipFile(result.zip_path) as archive:
        archive_names = set(archive.namelist())
        app_router_contents = [
            archive.read(name).decode("utf-8")
            for name in archive_names
            if name.startswith("src/app/") and name.endswith(".tsx")
        ]

    assert {
        "README.md",
        "package.json",
        "src/app/dashboard/page.tsx",
        "src/app/customers/actions.ts",
        "src/app/customers/page.tsx",
        "src/app/orders/actions.ts",
        "src/app/orders/page.tsx",
        "src/app/tasks/actions.ts",
        "src/app/tasks/page.tsx",
        "src/lib/database.types.ts",
        "src/lib/supabase.ts",
        "schema.sql",
        "env.example",
    }.issubset(archive_names)
    assert app_router_contents
    assert all("next/router" not in content for content in app_router_contents)

    assert artifact_repository.calls[0]["artifact_type"] == ArtifactType.MANIFEST
    assert artifact_repository.calls[0]["content"] == result.manifest.model_dump(mode="json")
    assert artifact_repository.calls[1]["artifact_type"] == ArtifactType.ZIP
    assert artifact_repository.calls[1]["storage_path"] == str(result.zip_path)


def test_project_generation_flow_survives_manifest_artifact_transient_failure(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    gateway = FakeGateway()
    artifact_repository = ManifestFailingArtifactRepository()
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

    assert result.manifest_artifact_id is None
    assert result.zip_artifact_id == "artifact-2"
    assert result.zip_path.exists()
    assert [call["artifact_type"] for call in artifact_repository.calls] == [
        ArtifactType.MANIFEST,
        ArtifactType.ZIP,
    ]
