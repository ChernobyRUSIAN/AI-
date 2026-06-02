from dataclasses import dataclass
from pathlib import Path

from vuls.generation.file_manifest import FileManifestError, validate_file_manifest
from vuls.llm.schemas import GeneratedProjectManifest


@dataclass(frozen=True)
class ProjectBuildResult:
    manifest: GeneratedProjectManifest
    workspace_path: Path
    written_files: list[Path]


def build_project_workspace(
    *,
    manifest: GeneratedProjectManifest,
    project_workdir: Path,
) -> ProjectBuildResult:
    validated_manifest = validate_file_manifest(manifest)
    project_workdir.mkdir(parents=True, exist_ok=True)
    workspace_path = _safe_child_path(project_workdir, validated_manifest.project_name)
    workspace_path.mkdir(parents=True, exist_ok=True)

    written_files: list[Path] = []
    for generated_file in validated_manifest.files:
        destination = _safe_child_path(workspace_path, generated_file.path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(generated_file.content, encoding="utf-8", newline="")
        written_files.append(destination)

    return ProjectBuildResult(
        manifest=validated_manifest,
        workspace_path=workspace_path,
        written_files=written_files,
    )


def _safe_child_path(root: Path, relative_path: str) -> Path:
    root_resolved = root.resolve()
    destination = (root_resolved / relative_path).resolve()
    if root_resolved != destination and root_resolved not in destination.parents:
        raise FileManifestError("Generated file path escapes the project workspace.")
    return destination
