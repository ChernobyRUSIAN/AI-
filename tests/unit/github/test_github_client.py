import json
from io import BytesIO
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from vuls.github.client import GitHubApiError, GitHubHttpClient


class FakeGitHubResponse:
    def __init__(self, payload: dict[str, Any], *, status: int = 201) -> None:
        self._payload = payload
        self.status = status

    def __enter__(self) -> "FakeGitHubResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class RecordingOpener:
    def __init__(self, responses: list[FakeGitHubResponse | HTTPError]) -> None:
        self._responses = responses
        self.calls: list[Request] = []

    def open(self, request: Request, *, timeout: float) -> FakeGitHubResponse:
        self.calls.append(request)
        response = self._responses.pop(0)
        if isinstance(response, HTTPError):
            raise response
        return response


class FakeProxyHandler:
    def __init__(self, proxies: dict[str, str]) -> None:
        self.proxies = proxies


class RecordingBuildOpener:
    def __init__(self, opener: RecordingOpener) -> None:
        self.opener = opener
        self.handlers: list[FakeProxyHandler] = []

    def __call__(self, handler: FakeProxyHandler) -> RecordingOpener:
        self.handlers.append(handler)
        return self.opener


def test_create_repository_falls_back_to_authenticated_user_endpoint_for_personal_owner(
) -> None:
    opener = RecordingOpener(
        [
            HTTPError(
                "https://api.github.com/orgs/ChernobyRUSIAN/repos",
                404,
                "Not Found",
                hdrs=None,
                fp=None,
            ),
            FakeGitHubResponse(
                {
                    "html_url": "https://github.com/ChernobyRUSIAN/car-wash-crm",
                    "owner": {"login": "ChernobyRUSIAN"},
                }
            ),
        ]
    )
    client = GitHubHttpClient(token="github-token", opener=opener)

    repository = client.create_repository(
        owner="ChernobyRUSIAN",
        repo_name="car-wash-crm",
        private=True,
        description="CRM for a car wash.",
        default_branch="main",
    )

    assert [call.full_url for call in opener.calls] == [
        "https://api.github.com/orgs/ChernobyRUSIAN/repos",
        "https://api.github.com/user/repos",
    ]
    assert repository.owner == "ChernobyRUSIAN"
    assert repository.html_url == "https://github.com/ChernobyRUSIAN/car-wash-crm"
    assert _json_payload(opener.calls[1]) == {
        "name": "car-wash-crm",
        "private": True,
        "description": "CRM for a car wash.",
        "auto_init": False,
    }


def test_create_repository_keeps_organization_endpoint_when_org_creation_succeeds(
) -> None:
    opener = RecordingOpener(
        [
            FakeGitHubResponse(
                {
                    "html_url": "https://github.com/acme/car-wash-crm",
                    "owner": {"login": "acme"},
                }
            )
        ]
    )
    client = GitHubHttpClient(token="github-token", opener=opener)

    repository = client.create_repository(
        owner="acme",
        repo_name="car-wash-crm",
        private=True,
        description="CRM for a car wash.",
        default_branch="main",
    )

    assert [call.full_url for call in opener.calls] == [
        "https://api.github.com/orgs/acme/repos"
    ]
    assert repository.owner == "acme"
    assert repository.html_url == "https://github.com/acme/car-wash-crm"


def test_create_repository_rejects_personal_fallback_owner_mismatch() -> None:
    opener = RecordingOpener(
        [
            HTTPError(
                "https://api.github.com/orgs/ChernobyRUSIAN/repos",
                404,
                "Not Found",
                hdrs=None,
                fp=None,
            ),
            FakeGitHubResponse(
                {
                    "html_url": "https://github.com/other-user/car-wash-crm",
                    "owner": {"login": "other-user"},
                }
            ),
        ]
    )
    client = GitHubHttpClient(token="github-token", opener=opener)

    with pytest.raises(GitHubApiError, match="owner mismatch"):
        client.create_repository(
            owner="ChernobyRUSIAN",
            repo_name="car-wash-crm",
            private=True,
            description="CRM for a car wash.",
            default_branch="main",
        )


def test_create_repository_includes_github_error_body_for_validation_failures(
) -> None:
    error_body = {
        "message": "Repository creation failed.",
        "errors": [
            {
                "resource": "Repository",
                "field": "name",
                "code": "custom",
                "message": "name already exists on this account",
            }
        ],
    }
    opener = RecordingOpener(
        [
            HTTPError(
                "https://api.github.com/orgs/acme/repos",
                422,
                "Unprocessable Entity",
                hdrs=None,
                fp=BytesIO(json.dumps(error_body).encode("utf-8")),
            )
        ]
    )
    client = GitHubHttpClient(token="github-token", opener=opener)

    with pytest.raises(GitHubApiError) as exc_info:
        client.create_repository(
            owner="acme",
            repo_name="car-wash-crm",
            private=True,
            description="CRM for a car wash.",
            default_branch="main",
        )

    error_message = str(exc_info.value)
    assert "GitHub API returned HTTP 422" in error_message
    assert "Repository creation failed." in error_message
    assert "name already exists on this account" in error_message


def test_github_http_client_builds_no_proxy_url_opener(monkeypatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    opener = RecordingOpener(
        [
            FakeGitHubResponse(
                {
                    "html_url": "https://github.com/acme/car-wash-crm",
                    "owner": {"login": "acme"},
                }
            )
        ]
    )
    build_opener = RecordingBuildOpener(opener)
    monkeypatch.setattr("vuls.github.client.ProxyHandler", FakeProxyHandler)
    monkeypatch.setattr("vuls.github.client.build_opener", build_opener)

    client = GitHubHttpClient(token="github-token")
    client.create_repository(
        owner="acme",
        repo_name="car-wash-crm",
        private=True,
        description="CRM for a car wash.",
        default_branch="main",
    )

    assert build_opener.handlers[0].proxies == {}
    assert [call.full_url for call in opener.calls] == [
        "https://api.github.com/orgs/acme/repos"
    ]


def _json_payload(request: Request) -> dict[str, object]:
    assert request.data is not None
    payload = json.loads(request.data.decode("utf-8"))
    assert isinstance(payload, dict)
    return payload
