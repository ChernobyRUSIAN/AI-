import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from vuls.github.client import GitHubApiError
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult, GitHubRepository
from vuls.llm.schemas import GeneratedProjectManifest

GITHUB_REPOSITORY_NAME_MAX_LENGTH = 100
GITHUB_REPOSITORY_DESCRIPTION_MAX_LENGTH = 350
LOGGER = logging.getLogger(__name__)
RepositoryNameSuffixFactory = Callable[[], str]


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
        name_suffix_factory: RepositoryNameSuffixFactory | None = None,
    ) -> None:
        self._client = client
        self._metadata_store = metadata_store
        self._max_name_attempts = max(max_name_attempts, 1)
        self._name_suffix_factory = name_suffix_factory or default_repository_name_suffix

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
        attempted_names: list[str] = []
        retry_suffix: str | None = None
        description = sanitize_repository_description(
            request.description or request.manifest.readme_summary
        )
        for attempt in range(1, self._max_name_attempts + 1):
            if attempt == 1:
                repo_name = base_repo_name
            else:
                if retry_suffix is None:
                    retry_suffix = self._name_suffix_factory()
                repo_name = build_repository_retry_name(
                    base_repo_name=base_repo_name,
                    retry_suffix=retry_suffix,
                    attempt=attempt,
                )
            attempted_names.append(repo_name)
            try:
                return self._client.create_repository(
                    owner=request.owner,
                    repo_name=repo_name,
                    private=request.private,
                    description=description,
                    default_branch=request.default_branch,
                )
            except GitHubNameConflict as exc:
                last_conflict = exc
                log_repository_name_conflict(
                    base_repo_name=base_repo_name,
                    attempted_name=repo_name,
                    attempt=attempt,
                    max_name_attempts=self._max_name_attempts,
                )
            except GitHubApiError as exc:
                if is_github_repository_name_conflict(exc):
                    last_conflict = GitHubNameConflict(str(exc))
                    log_repository_name_conflict(
                        base_repo_name=base_repo_name,
                        attempted_name=repo_name,
                        attempt=attempt,
                        max_name_attempts=self._max_name_attempts,
                    )
                    continue
                raise GitHubExportError(
                    "GitHub API request failed while creating repository."
                ) from exc

        if last_conflict is not None:
            error_message = repository_name_unavailable_message(
                base_repo_name=base_repo_name,
                attempted_names=attempted_names,
                max_name_attempts=self._max_name_attempts,
            )
            LOGGER.error(error_message)
            raise GitHubExportError(error_message) from last_conflict

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


def build_repository_retry_name(
    *,
    base_repo_name: str,
    retry_suffix: str,
    attempt: int,
) -> str:
    suffix = retry_suffix if attempt == 2 else f"{retry_suffix}-{attempt}"
    suffix = normalize_repository_retry_suffix(suffix, attempt=attempt)
    suffix_with_separator = f"-{suffix}"
    max_base_length = GITHUB_REPOSITORY_NAME_MAX_LENGTH - len(suffix_with_separator)
    if max_base_length < 1:
        raise GitHubExportError("Invalid GitHub repository retry suffix.")

    trimmed_base = base_repo_name[:max_base_length].rstrip("-.")
    if not trimmed_base:
        raise GitHubExportError("Invalid GitHub repository name.")
    return f"{trimmed_base}{suffix_with_separator}"


def normalize_repository_retry_suffix(suffix: str, *, attempt: int) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", suffix.strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-.")
    if normalized:
        return normalized
    return str(attempt)


def default_repository_name_suffix() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


def log_repository_name_conflict(
    *,
    base_repo_name: str,
    attempted_name: str,
    attempt: int,
    max_name_attempts: int,
) -> None:
    LOGGER.warning(
        "GitHub repository name conflict: "
        "base_repo_name=%s attempted_name=%s attempt=%s max_name_attempts=%s",
        base_repo_name,
        attempted_name,
        attempt,
        max_name_attempts,
    )


def repository_name_unavailable_message(
    *,
    base_repo_name: str,
    attempted_names: list[str],
    max_name_attempts: int,
) -> str:
    return (
        "GitHub repository name is unavailable. "
        f"base_repo_name={base_repo_name}; "
        f"attempted_names={attempted_names}; "
        f"max_name_attempts={max_name_attempts}."
    )


def sanitize_repository_description(description: str) -> str:
    description_without_newlines = re.sub(r"\r\n|\r|\n", " ", description)
    description_without_controls = "".join(
        char for char in description_without_newlines if not _is_control_character(char)
    )
    return description_without_controls.strip()[
        :GITHUB_REPOSITORY_DESCRIPTION_MAX_LENGTH
    ].rstrip()


def is_github_repository_name_conflict(error: GitHubApiError) -> bool:
    return (
        error.status_code == 422
        and "name already exists on this account" in str(error).casefold()
    )


def _is_control_character(char: str) -> bool:
    return ord(char) < 32 or ord(char) == 127
