import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from vuls.db.client import JsonObject
from vuls.db.models import ArtifactType
from vuls.db.repositories.artifacts import ArtifactRepositoryTransientError
from vuls.generation.crm_mvp import ensure_crm_next_mvp_manifest
from vuls.generation.project_builder import ProjectBuildResult, build_project_workspace
from vuls.generation.zip_exporter import ZipExportResult, export_workspace_zip
from vuls.llm.schemas import (
    ProjectBrief,
    ProjectManifestRequest,
    ProjectManifestResponse,
)
from vuls.templates.registry import TemplateRegistry

LOGGER = logging.getLogger(__name__)


class ProjectManifestGateway(Protocol):
    def generate_project_manifest(
        self,
        request: ProjectManifestRequest,
    ) -> ProjectManifestResponse: ...


class ArtifactRepositoryProtocol(Protocol):
    def create_artifact(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: Mapping[str, Any] | None = None,
    ) -> JsonObject: ...


@dataclass(frozen=True)
class ProjectGenerationResult:
    project_id: str
    template_key: str
    build: ProjectBuildResult
    zip_export: ZipExportResult
    manifest_artifact_id: str | None
    zip_artifact_id: str | None

    @property
    def manifest(self) -> object:
        return self.build.manifest

    @property
    def workspace_path(self) -> Path:
        return self.build.workspace_path

    @property
    def zip_path(self) -> Path:
        return self.zip_export.zip_path


class ProjectGenerationOrchestrator:
    def __init__(
        self,
        *,
        gateway: ProjectManifestGateway,
        template_registry: TemplateRegistry,
        artifact_repository: ArtifactRepositoryProtocol,
        project_workdir: Path,
        artifact_dir: Path,
        zip_max_bytes: int,
    ) -> None:
        self._gateway = gateway
        self._template_registry = template_registry
        self._artifact_repository = artifact_repository
        self._project_workdir = project_workdir
        self._artifact_dir = artifact_dir
        self._zip_max_bytes = zip_max_bytes

    def generate_project(
        self,
        *,
        project_id: str,
        generation_run_id: str | None,
        template_key: str,
        brief: ProjectBrief,
        memory_context: dict[str, list[str]] | None = None,
    ) -> ProjectGenerationResult:
        template = self._template_registry.get(template_key)
        manifest_response = self._gateway.generate_project_manifest(
            ProjectManifestRequest(
                template=template,
                brief=brief,
                memory_context=memory_context or {},
            )
        )
        manifest = ensure_crm_next_mvp_manifest(
            manifest=manifest_response.manifest,
            template_key=template_key,
            brief=brief,
        )
        build = build_project_workspace(
            manifest=manifest,
            project_workdir=self._project_workdir,
        )
        zip_export = export_workspace_zip(
            workspace_path=build.workspace_path,
            output_dir=self._artifact_dir,
            project_name=manifest.project_name,
            max_bytes=self._zip_max_bytes,
        )

        manifest_artifact_id = self._create_artifact_best_effort(
            project_id=project_id,
            generation_run_id=generation_run_id,
            artifact_type=ArtifactType.MANIFEST,
            content=manifest.model_dump(mode="json"),
        )
        zip_artifact_id = self._create_artifact_best_effort(
            project_id=project_id,
            generation_run_id=generation_run_id,
            artifact_type=ArtifactType.ZIP,
            storage_path=str(zip_export.zip_path),
            content={
                "size_bytes": zip_export.size_bytes,
                "project_name": manifest.project_name,
            },
        )

        return ProjectGenerationResult(
            project_id=project_id,
            template_key=template_key,
            build=build,
            zip_export=zip_export,
            manifest_artifact_id=manifest_artifact_id,
            zip_artifact_id=zip_artifact_id,
        )

    def _create_artifact_best_effort(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: Mapping[str, Any] | None = None,
    ) -> str | None:
        try:
            artifact = self._artifact_repository.create_artifact(
                project_id=project_id,
                generation_run_id=generation_run_id,
                artifact_type=artifact_type,
                storage_path=storage_path,
                content=content,
            )
        except ArtifactRepositoryTransientError:
            LOGGER.warning(
                "Artifact persistence failed after retries; continuing generation. "
                "project_id=%s artifact_type=%s",
                project_id,
                artifact_type.value,
                exc_info=True,
            )
            return None
        return str(artifact["id"])
