from pathlib import PurePosixPath

from vuls.llm.schemas import GeneratedProjectManifest


class FileManifestError(ValueError):
    """Raised when a generated project manifest is unsafe or incomplete."""


def validate_file_manifest(manifest: GeneratedProjectManifest) -> GeneratedProjectManifest:
    if not _is_safe_name(manifest.project_name):
        raise FileManifestError("Project name must be a safe slug.")

    seen_paths: set[str] = set()
    for generated_file in manifest.files:
        normalized_path = _normalize_manifest_path(generated_file.path)
        if normalized_path in seen_paths:
            raise FileManifestError(f"Duplicate generated file path: {normalized_path}.")
        seen_paths.add(normalized_path)

    if "README.md" not in seen_paths:
        raise FileManifestError("Generated project manifest must include README.md.")

    return manifest


def _normalize_manifest_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    parts = PurePosixPath(normalized).parts
    if (
        not normalized
        or normalized.startswith("/")
        or normalized.startswith("~")
        or normalized[1:3] == ":/"
        or ".." in parts
        or "." in parts
    ):
        raise FileManifestError("Generated file paths must be relative and safe.")
    return str(PurePosixPath(normalized))


def _is_safe_name(name: str) -> bool:
    normalized = name.strip()
    return bool(normalized) and _normalize_manifest_path(normalized) == normalized
