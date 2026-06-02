import pytest

from vuls.generation.file_manifest import FileManifestError, validate_file_manifest
from vuls.llm.schemas import GeneratedProjectFile, GeneratedProjectManifest


def valid_manifest() -> GeneratedProjectManifest:
    return GeneratedProjectManifest(
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
    )


def test_validate_file_manifest_accepts_safe_manifest() -> None:
    manifest = validate_file_manifest(valid_manifest())

    assert manifest.project_name == "coffee-crm"
    assert [file.path for file in manifest.files] == ["README.md", "src/main.py"]


def test_validate_file_manifest_requires_readme() -> None:
    manifest = valid_manifest().model_copy(
        update={
            "files": [
                GeneratedProjectFile(
                    path="src/main.py",
                    content="print('hello')\n",
                    purpose="Application entry point",
                )
            ]
        }
    )

    with pytest.raises(FileManifestError, match="README.md"):
        validate_file_manifest(manifest)


def test_validate_file_manifest_rejects_duplicate_paths() -> None:
    manifest = valid_manifest().model_copy(
        update={
            "files": [
                GeneratedProjectFile(
                    path="README.md",
                    content="# One\n",
                    purpose="Project documentation",
                ),
                GeneratedProjectFile(
                    path="README.md",
                    content="# Two\n",
                    purpose="Duplicate documentation",
                ),
            ]
        }
    )

    with pytest.raises(FileManifestError, match="Duplicate"):
        validate_file_manifest(manifest)


def test_validate_file_manifest_rejects_path_traversal_even_if_model_was_constructed() -> None:
    unsafe_file = GeneratedProjectFile.model_construct(
        path="../secrets.txt",
        content="secret",
        purpose="Unsafe path",
    )
    manifest = GeneratedProjectManifest.model_construct(
        project_name="unsafe-project",
        readme_summary="Unsafe manifest.",
        tech_stack=["Python"],
        files=[
            GeneratedProjectFile(
                path="README.md",
                content="# Unsafe\n",
                purpose="Project documentation",
            ),
            unsafe_file,
        ],
        env_vars=[],
    )

    with pytest.raises(FileManifestError, match="relative"):
        validate_file_manifest(manifest)
