import re
from typing import Protocol

from vuls.github.client import GitHubApiError
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult, GitHubRepository
from vuls.llm.schemas import GeneratedProjectManifest


class GitHubExportError(RuntimeError):
    """Raised when GitHub export cannot complete safely."""


class GitHubNameConflict(GitHubExportError):
    """Raised when the desired repository name already exists."""


class GitHubApiClientProtocol(Protocol):
    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository: ...

    def put_file(
        self,
        *,
        owner: str,
        repo_name: str,
        path: str,
        content: str,
        message: str,
        branch: str,
    ) -> str: ...


class RepositoryMetadataStoreProtocol(Protocol):
    def save_repository_metadata(
        self,
        *,
        project_id: str,
        owner: str,
        repo_name: str,
        html_url: str,
        default_branch: str,
    ) -> None: ...


class GitHubExportService:
    def __init__(
        self,
        *,
        client: GitHubApiClientProtocol,
        metadata_store: RepositoryMetadataStoreProtocol | None = None,
        max_name_attempts: int = 3,
    ) -> None:
        self._client = client
        self._metadata_store = metadata_store
        self._max_name_attempts = max(max_name_attempts, 1)

    def export_project(self, request: GitHubExportRequest) -> GitHubExportResult:
        base_repo_name = normalize_repository_name(request.repo_name)
        repository = self._create_repository_with_conflict_retry(
            request=request,
            base_repo_name=base_repo_name,
        )
        committed_files = self._commit_manifest_files(
            repository=repository,
            manifest=request.manifest,
        )
        self._save_metadata(request=request, repository=repository)

        return GitHubExportResult(
            project_id=request.project_id,
            owner=repository.owner,
            repo_name=repository.repo_name,
            html_url=repository.html_url,
            default_branch=repository.default_branch,
            committed_files=committed_files,
        )

    def _create_repository_with_conflict_retry(
        self,
        *,
        request: GitHubExportRequest,
        base_repo_name: str,
    ) -> GitHubRepository:
        last_conflict: GitHubNameConflict | None = None
        for attempt in range(1, self._max_name_attempts + 1):
            repo_name = base_repo_name if attempt == 1 else f"{base_repo_name}-{attempt}"
            try:
                return self._client.create_repository(
                    owner=request.owner,
                    repo_name=repo_name,
                    private=request.private,
                    description=request.description or request.manifest.readme_summary,
                    default_branch=request.default_branch,
                )
            except GitHubNameConflict as exc:
                last_conflict = exc
            except GitHubApiError as exc:
                raise GitHubExportError(
                    "GitHub API request failed while creating repository."
                ) from exc

        if last_conflict is not None:
            raise GitHubExportError("GitHub repository name is unavailable.") from last_conflict

        raise GitHubExportError("GitHub repository could not be created.")

    def _commit_manifest_files(
        self,
        *,
        repository: GitHubRepository,
        manifest: GeneratedProjectManifest,
    ) -> list[str]:
        committed_files: list[str] = []
        for generated_file in manifest.files:
            try:
                self._client.put_file(
                    owner=repository.owner,
                    repo_name=repository.repo_name,
                    path=generated_file.path,
                    content=generated_file.content,
                    message=f"Add {generated_file.path}",
                    branch=repository.default_branch,
                )
            except GitHubApiError as exc:
                raise GitHubExportError(
                    "GitHub API request failed while committing files."
                ) from exc
            committed_files.append(generated_file.path)
        return committed_files

    def _save_metadata(
        self,
        *,
        request: GitHubExportRequest,
        repository: GitHubRepository,
    ) -> None:
        if self._metadata_store is None:
            return
        self._metadata_store.save_repository_metadata(
            project_id=request.project_id,
            owner=repository.owner,
            repo_name=repository.repo_name,
            html_url=repository.html_url,
            default_branch=repository.default_branch,
        )


def normalize_repository_name(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name:
        raise GitHubExportError("Invalid GitHub repository name.")

    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-.")

    if not normalized:
        raise GitHubExportError("Invalid GitHub repository name.")
    if len(normalized) > 100:
        raise GitHubExportError("Invalid GitHub repository name.")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", normalized):
        raise GitHubExportError("Invalid GitHub repository name.")
    return normalized
