from vuls.github.schemas import GitHubExportRequest, GitHubRepository
from vuls.github.service import GitHubExportService
from vuls.llm.schemas import GeneratedProjectFile, GeneratedProjectManifest


class FakeGitHubClient:
    def __init__(self) -> None:
        self.files: dict[str, str] = {}

    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository:
        return GitHubRepository(
            owner=owner,
            repo_name=repo_name,
            html_url=f"https://github.com/{owner}/{repo_name}",
            default_branch=default_branch,
        )

    def put_file(
        self,
        *,
        owner: str,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> str:
        self.files[path] = content
        return f"sha-{len(self.files)}"


class FakeRepositoryMetadataStore:
    def __init__(self) -> None:
        self.records: list[dict[str, str]] = []

    def save_repository_metadata(
        self,
        *,
        project_id: str,
        owner: str,
        repo_name: str,
        html_url: str,
        default_branch: str,
    ) -> None:
        self.records.append(
            {
                "project_id": project_id,
                "owner": owner,
                "repo_name": repo_name,
                "html_url": html_url,
                "default_branch": default_branch,
            }
        )


def test_github_export_flow_returns_repository_url_and_records_metadata() -> None:
    client = FakeGitHubClient()
    store = FakeRepositoryMetadataStore()
    service = GitHubExportService(client=client, metadata_store=store)
    manifest = GeneratedProjectManifest(
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

    result = service.export_project(
        GitHubExportRequest(
            project_id="project-1",
            owner="acme",
            repo_name=manifest.project_name,
            manifest=manifest,
            private=True,
        )
    )

    assert result.html_url == "https://github.com/acme/coffee-crm"
    assert result.committed_files == ["README.md", "src/main.py"]
    assert client.files == {
        "README.md": "# Coffee CRM\n",
        "src/main.py": "print('hello')\n",
    }
    assert store.records == [
        {
            "project_id": "project-1",
            "owner": "acme",
            "repo_name": "coffee-crm",
            "html_url": "https://github.com/acme/coffee-crm",
            "default_branch": "main",
        }
    ]
