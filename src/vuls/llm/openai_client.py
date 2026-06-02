from importlib import import_module
from typing import Any, cast

from pydantic import BaseModel

from vuls.llm.gateway import LLMTransientError
from vuls.llm.schemas import LLMClientResponse, LLMMessage, LLMUsage


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float | None = None,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
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
                text={
                    "format": {
                        "type": "json_schema",
                        "name": response_schema.__name__,
                        "schema": response_schema.model_json_schema(),
                        "strict": True,
                    }
                },
            )
        except Exception as exc:
            if _looks_transient(exc):
                raise LLMTransientError(str(exc)) from exc
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
        if self._timeout_seconds is None:
            return client_factory(api_key=self._api_key)
        return client_factory(api_key=self._api_key, timeout=self._timeout_seconds)


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
