import base64
import json
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from vuls.github.schemas import GitHubRepository


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API returns an unexpected or failed response."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class GitHubUrlOpener(Protocol):
    def open(self, request: Request, *, timeout: float) -> Any: ...


class GitHubHttpClient:
    def __init__(
        self,
        *,
        token: str,
        api_base_url: str = "https://api.github.com",
        timeout_seconds: float = 30.0,
        opener: GitHubUrlOpener | None = None,
    ) -> None:
        self._token = token
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._opener = opener or build_opener(ProxyHandler({}))

    def create_repository(
        self,
        *,
        owner: str,
        repo_name: str,
        private: bool,
        description: str,
        default_branch: str,
    ) -> GitHubRepository:
        payload = {
            "name": repo_name,
            "private": private,
            "description": description,
            "auto_init": False,
        }
        try:
            data = self._request_json(
                "POST",
                f"/orgs/{owner}/repos",
                payload,
                expected_statuses={201},
            )
        except GitHubApiError as exc:
            if exc.status_code != 404:
                raise
            data = self._request_json(
                "POST",
                "/user/repos",
                payload,
                expected_statuses={201},
            )
        html_url = data.get("html_url")
        if not isinstance(html_url, str):
            raise GitHubApiError("GitHub repository response did not include html_url.")
        response_owner = _repository_owner_login(data)
        if response_owner is not None and response_owner.casefold() != owner.casefold():
            raise GitHubApiError(
                "GitHub repository owner mismatch after repository creation."
            )
        return GitHubRepository(
            owner=owner,
            repo_name=repo_name,
            html_url=html_url,
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
        payload = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        data = self._request_json(
            "PUT",
            f"/repos/{owner}/{repo_name}/contents/{path}",
            payload,
            expected_statuses={200, 201},
        )
        commit = data.get("commit")
        if not isinstance(commit, dict):
            raise GitHubApiError("GitHub file response did not include commit metadata.")
        sha = commit.get("sha")
        if not isinstance(sha, str):
            raise GitHubApiError("GitHub file response did not include commit sha.")
        return sha

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
        *,
        expected_statuses: set[int],
    ) -> dict[str, Any]:
        request = Request(
            f"{self._api_base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method=method,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
                status = response.status
        except HTTPError as exc:
            body = _http_error_body(exc)
            raise GitHubApiError(
                _github_error_message(exc.code, body),
                status_code=exc.code,
            ) from exc
        except URLError as exc:
            raise GitHubApiError("GitHub API network request failed.") from exc

        if status not in expected_statuses:
            raise GitHubApiError(f"GitHub API returned HTTP {status}.", status_code=status)

        decoded = json.loads(body) if body else {}
        if not isinstance(decoded, dict):
            raise GitHubApiError("GitHub API response must be a JSON object.")
        return decoded


def _http_error_body(exc: HTTPError) -> str:
    try:
        raw_body = exc.read()
    except Exception:
        return ""
    if not raw_body:
        return ""
    return raw_body.decode("utf-8", errors="replace").strip()


def _github_error_message(status_code: int, body: str) -> str:
    message = f"GitHub API returned HTTP {status_code}."
    if body:
        return f"{message} Response body: {body}"
    return message


def _repository_owner_login(data: dict[str, Any]) -> str | None:
    owner = data.get("owner")
    if isinstance(owner, dict):
        login = owner.get("login")
        if isinstance(login, str) and login:
            return login
    return None
