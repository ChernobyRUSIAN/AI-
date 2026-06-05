import re
from importlib import import_module
from typing import Any, cast

import httpx
from pydantic import BaseModel

from vuls.llm.gateway import LLMProviderError
from vuls.llm.schemas import LLMClientResponse, LLMMessage, LLMUsage

_UNSUPPORTED_OPENAI_SCHEMA_KEYWORDS = frozenset(
    {
        "default",
        "format",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "multipleOf",
        "pattern",
    }
)
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MAX_OUTPUT_TOKENS = 4000


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        timeout_seconds: float | None = None,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = _normalize_base_url(base_url)
        self._max_output_tokens = max_output_tokens
        self._timeout_seconds = timeout_seconds
        self._client = client

    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse:
        client = self._client or self._build_client()
        try:
            response = client.responses.create(
                model=model,
                input=[message.model_dump(mode="json") for message in messages],
                max_output_tokens=self._max_output_tokens,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": response_schema.__name__,
                        "schema": _openai_strict_json_schema(response_schema),
                        "strict": True,
                    }
                },
            )
        except Exception as exc:
            provider_error = _provider_error_from_exception(exc)
            if provider_error is not None:
                raise provider_error from exc
            raise

        return LLMClientResponse(
            content=_extract_output_text(response),
            usage=_extract_usage(response),
        )

    def _build_client(self) -> Any:
        try:
            openai_module = import_module("openai")
        except ImportError as exc:
            raise RuntimeError("Install the OpenAI Python SDK before running Vuls.") from exc

        client_factory = cast(Any, openai_module).OpenAI
        http_client = _build_http_client(timeout_seconds=self._timeout_seconds)
        return client_factory(
            api_key=self._api_key,
            base_url=self._base_url,
            http_client=http_client,
        )


def _build_http_client(*, timeout_seconds: float | None) -> httpx.Client:
    if timeout_seconds is None:
        return httpx.Client(trust_env=False)
    return httpx.Client(timeout=timeout_seconds, trust_env=False)


def _normalize_base_url(base_url: str | None) -> str:
    if base_url is None or not base_url.strip():
        return DEFAULT_OPENAI_BASE_URL
    return base_url


def _openai_strict_json_schema(response_schema: type[BaseModel]) -> dict[str, Any]:
    schema = response_schema.model_json_schema()
    return cast(dict[str, Any], _sanitize_openai_schema_node(schema))


def _sanitize_openai_schema_node(node: Any) -> Any:
    if isinstance(node, list):
        return [_sanitize_openai_schema_node(item) for item in node]
    if not isinstance(node, dict):
        return node

    sanitized = {
        key: _sanitize_openai_schema_node(value)
        for key, value in node.items()
        if key not in _UNSUPPORTED_OPENAI_SCHEMA_KEYWORDS
    }
    properties = sanitized.get("properties")
    if isinstance(properties, dict):
        sanitized["additionalProperties"] = False
        sanitized["required"] = list(properties)
    return sanitized


def _extract_output_text(response: Any) -> str:
    output_text = _read_attr_or_key(response, "output_text")
    if isinstance(output_text, str):
        return output_text

    choices = _read_attr_or_key(response, "choices")
    if isinstance(choices, list) and choices:
        message = _read_attr_or_key(choices[0], "message")
        content = _read_attr_or_key(message, "content")
        if isinstance(content, str):
            return content

    raise RuntimeError("OpenAI response did not include output text.")


def _extract_usage(response: Any) -> LLMUsage:
    usage = _read_attr_or_key(response, "usage")
    return LLMUsage(
        input_tokens=_read_int(usage, "input_tokens", "prompt_tokens"),
        output_tokens=_read_int(usage, "output_tokens", "completion_tokens"),
        total_tokens=_read_int(usage, "total_tokens"),
    )


def _read_int(source: Any, *names: str) -> int:
    for name in names:
        value = _read_attr_or_key(source, name)
        if isinstance(value, int):
            return value
    return 0


def _read_attr_or_key(source: Any, name: str) -> Any:
    if isinstance(source, dict):
        return source.get(name)
    return getattr(source, name, None)


def _looks_transient(exc: Exception) -> bool:
    class_name = exc.__class__.__name__.lower()
    return any(
        marker in class_name
        for marker in ("rate", "timeout", "apierror", "connection", "serviceunavailable")
    )


def _provider_error_from_exception(exc: Exception) -> LLMProviderError | None:
    message = str(exc)
    normalized_message = message.casefold()
    class_name = exc.__class__.__name__.casefold()
    status_code = getattr(exc, "status_code", None)

    if "unsupported_country_region_territory" in normalized_message:
        return LLMProviderError(
            message,
            code="unsupported_country_region_territory",
            provider=_provider_name_from_message(message),
        )
    if (
        status_code == 429
        or "rate limit" in normalized_message
        or "rate-limited" in normalized_message
    ):
        return LLMProviderError(
            message,
            code="rate_limit",
            provider=_provider_name_from_message(message),
        )
    if status_code in {502, 503, 504} or "temporarily" in normalized_message:
        return LLMProviderError(
            message,
            code="provider_unavailable",
            provider=_provider_name_from_message(message),
        )
    if "timeout" in class_name or "timeout" in normalized_message:
        return LLMProviderError(message, code="timeout")
    if (
        "connection" in class_name
        or "connect" in normalized_message
        or "network" in normalized_message
    ):
        return LLMProviderError(message, code="network_error")
    if _looks_transient(exc):
        return LLMProviderError(message, code="provider_unavailable")
    return None


def _provider_name_from_message(message: str) -> str | None:
    match = re.search(r"'provider_name': '([^']+)'", message)
    if match:
        return match.group(1)
    match = re.search(r'"provider_name"\s*:\s*"([^"]+)"', message)
    if match:
        return match.group(1)
    return None
