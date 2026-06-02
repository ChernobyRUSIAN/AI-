from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from vuls.generation.file_manifest import FileManifestError


class ZipExportError(ValueError):
    """Raised when a generated project cannot be exported as a ZIP artifact."""


@dataclass(frozen=True)
class ZipExportResult:
    zip_path: Path
    size_bytes: int


def export_workspace_zip(
    *,
    workspace_path: Path,
    output_dir: Path,
    project_name: str,
    max_bytes: int,
) -> ZipExportResult:
    if not workspace_path.is_dir():
        raise ZipExportError("Workspace path must be an existing directory.")
    if max_bytes <= 0:
        raise ZipExportError("ZIP max bytes must be greater than zero.")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{_safe_zip_name(project_name)}.zip"

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in workspace_path.rglob("*") if path.is_file()):
            archive_name = _safe_archive_name(workspace_path, file_path)
            archive.write(file_path, archive_name)

    size_bytes = zip_path.stat().st_size
    if size_bytes > max_bytes:
        zip_path.unlink(missing_ok=True)
        raise ZipExportError(f"ZIP artifact exceeds max size: {size_bytes} > {max_bytes}.")

    return ZipExportResult(zip_path=zip_path, size_bytes=size_bytes)


def _safe_archive_name(workspace_path: Path, file_path: Path) -> str:
    try:
        relative_path = file_path.resolve().relative_to(workspace_path.resolve())
    except ValueError as exc:
        raise ZipExportError("ZIP file path escapes workspace.") from exc

    archive_name = relative_path.as_posix()
    if archive_name.startswith("/") or ".." in archive_name.split("/"):
        raise ZipExportError("ZIP archive names must stay inside the workspace.")
    return archive_name


def _safe_zip_name(project_name: str) -> str:
    try:
        safe_name = project_name.replace("\\", "/").strip()
        if "/" in safe_name or not safe_name:
            raise FileManifestError
    except FileManifestError as exc:
        raise ZipExportError("Project name must be safe for ZIP export.") from exc
    return safe_name
