import base64
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from vuls.github.schemas import GitHubRepository


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API returns an unexpected or failed response."""


class GitHubHttpClient:
    def __init__(
        self,
        *,
        token: str,
        api_base_url: str = "https://api.github.com",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._token = token
        self._api_base_url = api_base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

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
        data = self._request_json(
            "POST",
            f"/orgs/{owner}/repos",
            payload,
            expected_statuses={201},
        )
        html_url = data.get("html_url")
        if not isinstance(html_url, str):
            raise GitHubApiError("GitHub repository response did not include html_url.")
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
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
                status = response.status
        except HTTPError as exc:
            raise GitHubApiError(f"GitHub API returned HTTP {exc.code}.") from exc
        except URLError as exc:
            raise GitHubApiError("GitHub API network request failed.") from exc

        if status not in expected_statuses:
            raise GitHubApiError(f"GitHub API returned HTTP {status}.")

        decoded = json.loads(body) if body else {}
        if not isinstance(decoded, dict):
            raise GitHubApiError("GitHub API response must be a JSON object.")
        return decoded
