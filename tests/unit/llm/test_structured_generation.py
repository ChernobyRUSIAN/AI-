import json
from typing import Any

import pytest

from vuls.llm.gateway import LLMGateway, LLMOutputValidationError, LLMTransientError
from vuls.llm.schemas import (
    GeneratedProjectManifest,
    LLMClientResponse,
    LLMMessage,
    LLMUsage,
    ProjectBrief,
    ProjectManifestRequest,
)
from vuls.templates.registry import TemplateRegistry


class FakeLLMClient:
    def __init__(self, responses: list[LLMClientResponse | Exception]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[GeneratedProjectManifest],
    ) -> LLMClientResponse:
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "response_schema": response_schema,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def manifest_payload() -> dict[str, object]:
    return {
        "project_name": "coffee-crm",
        "readme_summary": "CRM for a small coffee shop.",
        "tech_stack": ["FastAPI", "React"],
        "files": [
            {
                "path": "README.md",
                "content": "# Coffee CRM\n",
                "purpose": "Project documentation",
            },
            {
                "path": "src/main.py",
                "content": "print('hello')\n",
                "purpose": "Application entry point",
            },
        ],
        "env_vars": [
            {
                "name": "DATABASE_URL",
                "description": "Database connection string",
                "required": True,
            }
        ],
    }


def project_manifest_request() -> ProjectManifestRequest:
    return ProjectManifestRequest(
        template=TemplateRegistry().get("crm"),
        brief=ProjectBrief(
            title="Coffee CRM",
            goal="Create a CRM for a small coffee shop",
            target_users=["owner", "staff"],
            must_have_features=["customers", "orders", "tasks"],
            language_code="en",
        ),
    )


def test_gateway_validates_structured_manifest_and_returns_usage_metadata() -> None:
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=json.dumps(manifest_payload()),
                usage=LLMUsage(input_tokens=120, output_tokens=80, total_tokens=200),
            )
        ]
    )
    gateway = LLMGateway(client=client, model="gpt-test")

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.model == "gpt-test"
    assert response.usage.total_tokens == 200
    assert response.manifest.project_name == "coffee-crm"
    assert response.manifest.readme_summary == "CRM for a small coffee shop."
    assert response.manifest.files[0].path == "README.md"
    assert response.manifest.files[0].content == "# Coffee CRM\n"
    assert response.manifest.env_vars[0].name == "DATABASE_URL"
    assert client.calls[0]["response_schema"] is GeneratedProjectManifest


def test_gateway_raises_typed_error_for_invalid_json_output() -> None:
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content="not json",
                usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    with pytest.raises(LLMOutputValidationError, match="valid JSON"):
        gateway.generate_project_manifest(project_manifest_request())


def test_gateway_raises_typed_error_for_invalid_manifest_shape() -> None:
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=json.dumps({"project_name": "missing-required-fields"}),
                usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    with pytest.raises(LLMOutputValidationError, match="schema"):
        gateway.generate_project_manifest(project_manifest_request())


def test_gateway_retries_transient_failures_before_returning_manifest() -> None:
    client = FakeLLMClient(
        [
            LLMTransientError("rate limit"),
            LLMClientResponse(
                content=json.dumps(manifest_payload()),
                usage=LLMUsage(input_tokens=50, output_tokens=50, total_tokens=100),
            ),
        ]
    )
    gateway = LLMGateway(client=client, max_attempts=2)

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.manifest.project_name == "coffee-crm"
    assert len(client.calls) == 2


def test_gateway_stops_after_configured_retry_attempts() -> None:
    client = FakeLLMClient([LLMTransientError("timeout"), LLMTransientError("timeout")])
    gateway = LLMGateway(client=client, max_attempts=2)

    with pytest.raises(LLMTransientError, match="timeout"):
        gateway.generate_project_manifest(project_manifest_request())

    assert len(client.calls) == 2
