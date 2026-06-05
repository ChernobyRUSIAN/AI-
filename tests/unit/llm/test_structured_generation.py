import json
import logging
from typing import Any

import pytest

from vuls.llm.gateway import (
    LLMGateway,
    LLMOutputValidationError,
    LLMProviderError,
    LLMProviderUnavailableError,
    LLMTransientError,
)
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


def test_gateway_logs_raw_response_when_json_output_cannot_be_recovered(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raw_response = "not json"
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=raw_response,
                usage=LLMUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    with caplog.at_level(logging.WARNING, logger="vuls.llm.gateway"):
        with pytest.raises(LLMOutputValidationError, match="valid JSON"):
            gateway.generate_project_manifest(project_manifest_request())

    assert raw_response in caplog.text


def test_gateway_repairs_markdown_wrapped_manifest_json() -> None:
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=f"```json\n{json.dumps(manifest_payload())}\n```",
                usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.manifest.project_name == "coffee-crm"


def test_gateway_repairs_manifest_json_with_extra_text_before_and_after() -> None:
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=(
                    "Here is the generated manifest:\n"
                    f"{json.dumps(manifest_payload())}\n"
                    "Let me know if you want changes."
                ),
                usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.manifest.project_name == "coffee-crm"


def test_gateway_repairs_truncated_manifest_json_missing_closing_braces() -> None:
    truncated = json.dumps(manifest_payload(), indent=2)[:-2]
    client = FakeLLMClient(
        [
            LLMClientResponse(
                content=truncated,
                usage=LLMUsage(input_tokens=10, output_tokens=20, total_tokens=30),
            )
        ]
    )
    gateway = LLMGateway(client=client)

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.manifest.project_name == "coffee-crm"


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


def test_gateway_falls_back_to_secondary_model_after_provider_failure() -> None:
    client = FakeLLMClient(
        [
            LLMProviderError("primary rate limit", code="rate_limit", provider="OpenAI"),
            LLMClientResponse(
                content=json.dumps(manifest_payload()),
                usage=LLMUsage(input_tokens=50, output_tokens=50, total_tokens=100),
            ),
        ]
    )
    gateway = LLMGateway(
        client=client,
        model="openai/gpt-primary",
        fallback_models=["anthropic/claude-secondary"],
        max_attempts=1,
    )

    response = gateway.generate_project_manifest(project_manifest_request())

    assert response.model == "anthropic/claude-secondary"
    assert gateway.active_model == "anthropic/claude-secondary"
    assert [call["model"] for call in client.calls] == [
        "openai/gpt-primary",
        "anthropic/claude-secondary",
    ]
    assert gateway.last_failures == (
        {
            "model": "openai/gpt-primary",
            "provider": "OpenAI",
            "attempt": "1",
            "code": "rate_limit",
            "message": "primary rate limit",
        },
    )


def test_gateway_raises_provider_unavailable_after_all_models_fail() -> None:
    client = FakeLLMClient(
        [
            LLMProviderError("unsupported region", code="unsupported_country_region_territory"),
            LLMProviderError("provider outage", code="provider_unavailable"),
            LLMProviderError("network failed", code="network_error"),
        ]
    )
    gateway = LLMGateway(
        client=client,
        model="openai/gpt-primary",
        fallback_models=["google/gemini-fallback", "anthropic/claude-fallback"],
        max_attempts=1,
    )

    with pytest.raises(LLMProviderUnavailableError) as exc_info:
        gateway.generate_project_manifest(project_manifest_request())

    assert [failure["code"] for failure in exc_info.value.failures] == [
        "unsupported_country_region_territory",
        "provider_unavailable",
        "network_error",
    ]
    assert [call["model"] for call in client.calls] == [
        "openai/gpt-primary",
        "google/gemini-fallback",
        "anthropic/claude-fallback",
    ]


def test_gateway_stops_after_configured_retry_attempts() -> None:
    client = FakeLLMClient([LLMTransientError("timeout"), LLMTransientError("timeout")])
    gateway = LLMGateway(client=client, max_attempts=2)

    with pytest.raises(LLMProviderUnavailableError):
        gateway.generate_project_manifest(project_manifest_request())

    assert len(client.calls) == 2
