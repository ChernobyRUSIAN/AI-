from typing import Any

import pytest

from vuls.llm.gateway import LLMProviderError
from vuls.llm.openai_client import OpenAIResponsesClient
from vuls.llm.schemas import (
    GeneratedProjectManifest,
    LLMMessage,
    LLMRole,
    ProjectBrief,
)


class FakeResponses:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> dict[str, object]:
        self.calls.append(kwargs)
        return {
            "output_text": "{}",
            "usage": {
                "input_tokens": 1,
                "output_tokens": 1,
                "total_tokens": 2,
            },
        }


class FakeOpenAIClient:
    def __init__(self, responses: Any | None = None) -> None:
        self.responses = responses or FakeResponses()


class FakeOpenAIFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> FakeOpenAIClient:
        self.calls.append(kwargs)
        return FakeOpenAIClient()


class FakeOpenAIModule:
    def __init__(self, factory: FakeOpenAIFactory) -> None:
        self.OpenAI = factory


class FakeOpenAIException(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FailingResponses:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def create(self, **kwargs: Any) -> dict[str, object]:
        raise self.exc


@pytest.mark.parametrize(
    ("configured_base_url", "expected_base_url"),
    [
        (None, "https://api.openai.com/v1"),
        ("https://openrouter.ai/api/v1", "https://openrouter.ai/api/v1"),
    ],
)
def test_responses_client_builds_sdk_client_with_base_url(
    monkeypatch: pytest.MonkeyPatch,
    configured_base_url: str | None,
    expected_base_url: str,
) -> None:
    factory = FakeOpenAIFactory()
    monkeypatch.setattr(
        "vuls.llm.openai_client.import_module",
        lambda module_name: FakeOpenAIModule(factory),
    )
    kwargs: dict[str, object] = {"api_key": "test-key"}
    if configured_base_url is not None:
        kwargs["base_url"] = configured_base_url
    client = OpenAIResponsesClient(**kwargs)

    client.complete_json(
        model="gpt-test",
        messages=[LLMMessage(role=LLMRole.USER, content="Create a CRM for a car wash")],
        response_schema=ProjectBrief,
    )

    assert factory.calls[0]["api_key"] == "test-key"
    assert factory.calls[0]["base_url"] == expected_base_url
    assert "http_client" in factory.calls[0]
    assert factory.calls[0]["http_client"]._trust_env is False


def test_responses_client_builds_sdk_client_with_timeout_and_ignores_env_proxies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = FakeOpenAIFactory()
    monkeypatch.setattr(
        "vuls.llm.openai_client.import_module",
        lambda module_name: FakeOpenAIModule(factory),
    )
    client = OpenAIResponsesClient(api_key="test-key", timeout_seconds=12)

    client.complete_json(
        model="gpt-test",
        messages=[LLMMessage(role=LLMRole.USER, content="Create a CRM for dentistry")],
        response_schema=ProjectBrief,
    )

    http_client = factory.calls[0]["http_client"]
    assert http_client._trust_env is False
    assert http_client.timeout.connect == 12


@pytest.mark.parametrize(
    ("exc", "expected_code"),
    [
        (
            FakeOpenAIException(
                "Provider returned unsupported_country_region_territory",
                status_code=403,
            ),
            "unsupported_country_region_territory",
        ),
        (
            FakeOpenAIException("Provider is temporarily rate-limited", status_code=429),
            "rate_limit",
        ),
        (TimeoutError("request timed out"), "timeout"),
    ],
)
def test_responses_client_classifies_provider_failures(
    exc: Exception,
    expected_code: str,
) -> None:
    fake_client = FakeOpenAIClient(responses=FailingResponses(exc))
    client = OpenAIResponsesClient(api_key="test-key", client=fake_client)

    with pytest.raises(LLMProviderError) as exc_info:
        client.complete_json(
            model="gpt-test",
            messages=[LLMMessage(role=LLMRole.USER, content="Create a CRM")],
            response_schema=ProjectBrief,
        )

    assert exc_info.value.code == expected_code


def test_responses_client_sends_openai_strict_schema_for_project_brief() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesClient(api_key="test-key", client=fake_client)

    client.complete_json(
        model="gpt-test",
        messages=[LLMMessage(role=LLMRole.USER, content="Create a CRM for a car wash")],
        response_schema=ProjectBrief,
    )

    schema = fake_client.responses.calls[0]["text"]["format"]["schema"]
    assert_openai_strict_schema(schema)
    assert fake_client.responses.calls[0]["max_output_tokens"] == 4000


def test_responses_client_sends_openai_strict_schema_for_project_manifest() -> None:
    fake_client = FakeOpenAIClient()
    client = OpenAIResponsesClient(api_key="test-key", client=fake_client)

    client.complete_json(
        model="gpt-test",
        messages=[LLMMessage(role=LLMRole.USER, content="Generate project files")],
        response_schema=GeneratedProjectManifest,
    )

    schema = fake_client.responses.calls[0]["text"]["format"]["schema"]
    assert_openai_strict_schema(schema)
    assert fake_client.responses.calls[0]["max_output_tokens"] == 4000


def assert_openai_strict_schema(schema: object) -> None:
    _assert_openai_strict_node(schema, path="$")


def _assert_openai_strict_node(node: object, *, path: str) -> None:
    if isinstance(node, list):
        for index, item in enumerate(node):
            _assert_openai_strict_node(item, path=f"{path}[{index}]")
        return

    if not isinstance(node, dict):
        return

    unsupported_keywords = {
        "default",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
        "format",
    }
    unexpected_keywords = unsupported_keywords.intersection(node)
    assert unexpected_keywords == set(), f"{path} contains unsupported keys {unexpected_keywords}"

    properties = node.get("properties")
    if isinstance(properties, dict):
        assert node.get("additionalProperties") is False, (
            f"{path} must set additionalProperties=false"
        )
        assert set(node.get("required", [])) == set(properties), (
            f"{path} must require every property"
        )

    for key, value in node.items():
        _assert_openai_strict_node(value, path=f"{path}.{key}")
