import pytest
from pydantic import ValidationError

from vuls.github.client import GitHubApiError
from vuls.github.schemas import GitHubExportRequest, GitHubRepository
from vuls.github.service import GitHubExportError, GitHubExportService, GitHubNameConflict
from vuls.llm.schemas import GeneratedProjectFile, GeneratedProjectManifest


class FakeGitHubClient:
    def __init__(
        self,
        *,
        conflicts: set[str] | None = None,
        fail_on_put: GitHubApiError | None = None,
    ) -> None:
        self.conflicts = conflicts or set()
        self.fail_on_put = fail_on_put
        self.created_repositories: list[dict[str, object]] = []
        self.committed_files: list[dict[str, object]] = []

    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository:
        self.created_repositories.append(
            {
                "owner": owner,
                "repo_name": repo_name,
                "private": private,
                "description": description,
                "default_branch": default_branch,
            }
        )
        if repo_name in self.conflicts:
            raise GitHubNameConflict(f"Repository already exists: {repo_name}")
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
        if self.fail_on_put is not None:
            raise self.fail_on_put
        commit_sha = f"sha-{len(self.committed_files) + 1}"
        self.committed_files.append(
            {
                "owner": owner,
                "repo_name": repo_name,
                "path": path,
                "content": content,
                "message": message,
                "branch": branch,
                "commit_sha": commit_sha,
            }
        )
        return commit_sha


class FakeRepositoryMetadataStore:
    def __init__(self) -> None:
        self.saved: list[dict[str, object]] = []

    def save_repository_metadata(
        self,
        *,
        project_id: str,
        owner: str,
        repo_name: str,
        html_url: str,
        default_branch: str,
    ) -> None:
        self.saved.append(
            {
                "project_id": project_id,
                "owner": owner,
                "repo_name": repo_name,
                "html_url": html_url,
                "default_branch": default_branch,
            }
        )


def sample_manifest() -> GeneratedProjectManifest:
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


def test_export_project_creates_repository_commits_files_and_returns_url() -> None:
    client = FakeGitHubClient()
    store = FakeRepositoryMetadataStore()
    service = GitHubExportService(client=client, metadata_store=store)

    result = service.export_project(
        GitHubExportRequest(
            project_id="project-1",
            owner="acme",
            repo_name="Coffee CRM",
            manifest=sample_manifest(),
            private=True,
        )
    )

    assert result.html_url == "https://github.com/acme/coffee-crm"
    assert result.repo_name == "coffee-crm"
    assert result.commit_count == 2
    assert client.created_repositories == [
        {
            "owner": "acme",
            "repo_name": "coffee-crm",
            "private": True,
            "description": "CRM for a small coffee shop.",
            "default_branch": "main",
        }
    ]
    assert [call["path"] for call in client.committed_files] == ["README.md", "src/main.py"]
    assert store.saved == [
        {
            "project_id": "project-1",
            "owner": "acme",
            "repo_name": "coffee-crm",
            "html_url": "https://github.com/acme/coffee-crm",
            "default_branch": "main",
        }
    ]


def test_export_project_retries_name_conflict_with_deterministic_suffix() -> None:
    client = FakeGitHubClient(conflicts={"coffee-crm"})
    service = GitHubExportService(client=client)

    result = service.export_project(
        GitHubExportRequest(
            project_id="project-1",
            owner="acme",
            repo_name="Coffee CRM",
            manifest=sample_manifest(),
        )
    )

    assert result.repo_name == "coffee-crm-2"
    assert [call["repo_name"] for call in client.created_repositories] == [
        "coffee-crm",
        "coffee-crm-2",
    ]
    assert {call["repo_name"] for call in client.committed_files} == {"coffee-crm-2"}


def test_export_project_sanitizes_api_failures() -> None:
    client = FakeGitHubClient(
        fail_on_put=GitHubApiError("Authorization failed for ghp_secret_token")
    )
    service = GitHubExportService(client=client)

    with pytest.raises(GitHubExportError) as exc_info:
        service.export_project(
            GitHubExportRequest(
                project_id="project-1",
                owner="acme",
                repo_name="coffee-crm",
                manifest=sample_manifest(),
            )
        )

    assert "ghp_secret_token" not in str(exc_info.value)
    assert "GitHub API request failed while committing files." in str(exc_info.value)


def test_export_project_rejects_invalid_repository_name_before_api_call() -> None:
    client = FakeGitHubClient()
    service = GitHubExportService(client=client)

    with pytest.raises(GitHubExportError, match="repository name"):
        service.export_project(
            GitHubExportRequest(
                project_id="project-1",
                owner="acme",
                repo_name="../secret",
                manifest=sample_manifest(),
            )
        )

    assert client.created_repositories == []
    assert client.committed_files == []


def test_export_request_rejects_empty_owner() -> None:
    with pytest.raises(ValidationError):
        GitHubExportRequest(
            project_id="project-1",
            owner="",
            repo_name="coffee-crm",
            manifest=sample_manifest(),
        )
