import zipfile

import pytest

from vuls.generation.zip_exporter import ZipExportError, export_workspace_zip


def test_export_workspace_zip_includes_generated_project_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace" / "coffee-crm"
    (workspace / "src").mkdir(parents=True)
    (workspace / "README.md").write_bytes(b"# Coffee CRM\n")
    (workspace / "src" / "main.py").write_bytes(b"print('hello')\n")
    output_dir = tmp_path / "artifacts"

    result = export_workspace_zip(
        workspace_path=workspace,
        output_dir=output_dir,
        project_name="coffee-crm",
        max_bytes=10_000,
    )

    assert result.zip_path == output_dir / "coffee-crm.zip"
    assert result.size_bytes > 0
    with zipfile.ZipFile(result.zip_path) as archive:
        assert sorted(archive.namelist()) == ["README.md", "src/main.py"]
        assert archive.read("README.md").decode("utf-8") == "# Coffee CRM\n"


def test_export_workspace_zip_rejects_zip_over_max_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "workspace" / "large-project"
    workspace.mkdir(parents=True)
    (workspace / "README.md").write_bytes(("# Large\n" + "x" * 5000).encode("utf-8"))

    with pytest.raises(ZipExportError, match="exceeds"):
        export_workspace_zip(
            workspace_path=workspace,
            output_dir=tmp_path / "artifacts",
            project_name="large-project",
            max_bytes=100,
        )
