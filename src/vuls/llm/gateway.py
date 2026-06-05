import json
import logging
import re
from typing import Protocol, cast

from pydantic import BaseModel, ValidationError

from vuls.llm.prompts import build_brief_normalization_prompt, build_project_manifest_prompt
from vuls.llm.safety import evaluate_generation_safety
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    GeneratedProjectManifest,
    LLMClientResponse,
    LLMMessage,
    ProjectBrief,
    ProjectManifestRequest,
    ProjectManifestResponse,
)

DEFAULT_LLM_MODEL = "gpt-5"
logger = logging.getLogger(__name__)


class LLMGatewayError(RuntimeError):
    """Base exception for expected LLM gateway failures."""


class LLMTransientError(LLMGatewayError):
    """Raised for retryable provider failures."""


class LLMProviderError(LLMTransientError):
    """Raised when a provider/model fails with a classified retryable reason."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_unavailable",
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider = provider
        self.model = model


class LLMProviderUnavailableError(LLMGatewayError):
    """Raised after every configured provider/model option has failed."""

    def __init__(self, *, failures: list[dict[str, str]]) -> None:
        super().__init__("No available LLM providers.")
        self.failures = failures


class LLMOutputValidationError(LLMGatewayError):
    """Raised when a model response is not valid JSON or does not match schema."""


class LLMSafetyError(LLMGatewayError):
    """Raised when a request is blocked before the provider call."""


class LLMClient(Protocol):
    def complete_json(
        self,
        *,
        model: str,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse: ...


class LLMGateway:
    def __init__(
        self,
        *,
        client: LLMClient,
        model: str = DEFAULT_LLM_MODEL,
        fallback_models: list[str] | tuple[str, ...] | None = None,
        max_attempts: int = 3,
    ) -> None:
        self._client = client
        self._models = _model_sequence(model, fallback_models)
        self._model = self._models[0]
        self._active_model = self._models[0]
        self._last_failures: list[dict[str, str]] = []
        self._max_attempts = max(max_attempts, 1)

    @property
    def active_model(self) -> str:
        return self._active_model

    @property
    def configured_models(self) -> tuple[str, ...]:
        return self._models

    @property
    def last_failures(self) -> tuple[dict[str, str], ...]:
        return tuple(dict(failure) for failure in self._last_failures)

    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        self._ensure_safe(request.user_idea)
        response, model = self._complete_with_fallback(
            messages=build_brief_normalization_prompt(request),
            response_schema=ProjectBrief,
        )
        return BriefNormalizationResponse(
            brief=_parse_json_model(response.content, ProjectBrief),
            usage=response.usage,
            model=model,
        )

    def generate_project_manifest(
        self,
        request: ProjectManifestRequest,
    ) -> ProjectManifestResponse:
        self._ensure_safe(
            " ".join(
                [
                    request.brief.title,
                    request.brief.goal,
                    *request.brief.target_users,
                    *request.brief.must_have_features,
                ]
            )
        )
        response, model = self._complete_with_fallback(
            messages=build_project_manifest_prompt(request),
            response_schema=GeneratedProjectManifest,
        )
        return ProjectManifestResponse(
            manifest=_parse_json_model(response.content, GeneratedProjectManifest),
            usage=response.usage,
            model=model,
        )

    def _complete_with_fallback(
        self,
        *,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> tuple[LLMClientResponse, str]:
        failures: list[dict[str, str]] = []

        for model in self._models:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = self._client.complete_json(
                        model=model,
                        messages=messages,
                        response_schema=response_schema,
                    )
                    self._active_model = model
                    self._last_failures = failures
                    return response, model
                except LLMTransientError as exc:
                    failure = _failure_payload(model=model, attempt=attempt, error=exc)
                    failures.append(failure)
                    logger.warning(
                        "LLM provider/model failed; trying fallback if available. "
                        "model=%s attempt=%s code=%s reason=%s",
                        model,
                        attempt,
                        failure["code"],
                        failure["message"],
                    )

        self._last_failures = failures
        raise LLMProviderUnavailableError(failures=failures)

    def _complete_with_retries(
        self,
        *,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse:
        response, _model = self._complete_with_fallback(
            messages=messages,
            response_schema=response_schema,
        )
        return response

    def _ensure_safe(self, text: str) -> None:
        safety = evaluate_generation_safety(text)
        if not safety.allowed:
            raise LLMSafetyError(f"{safety.code}: {safety.reason}")


def _parse_json_model[T: BaseModel](content: str, model: type[T]) -> T:
    payload = _load_json_payload(content, model)

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise LLMOutputValidationError("Model output did not match the expected schema.") from exc


def _model_sequence(
    primary_model: str,
    fallback_models: list[str] | tuple[str, ...] | None,
) -> tuple[str, ...]:
    models: list[str] = []
    for model in (primary_model, *(fallback_models or ())):
        normalized = model.strip()
        if normalized and normalized not in models:
            models.append(normalized)
    return tuple(models) or (DEFAULT_LLM_MODEL,)


def _failure_payload(
    *,
    model: str,
    attempt: int,
    error: LLMTransientError,
) -> dict[str, str]:
    code = getattr(error, "code", "provider_unavailable")
    provider = getattr(error, "provider", None)
    return {
        "model": model,
        "provider": str(provider or _provider_from_model(model)),
        "attempt": str(attempt),
        "code": str(code),
        "message": str(error),
    }


def _provider_from_model(model: str) -> str:
    if "/" in model:
        return model.split("/", 1)[0]
    return "openai"


def _load_json_payload(content: str, model: type[BaseModel]) -> object:
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        logger.warning(
            "LLM returned invalid JSON for %s. Raw response: %s",
            model.__name__,
            content,
            exc_info=True,
        )
        repaired_payload = _repair_json_payload(content)
        if repaired_payload is None:
            raise LLMOutputValidationError("Model output was not valid JSON.") from exc
        return repaired_payload


def _repair_json_payload(content: str) -> object | None:
    for candidate in _json_repair_candidates(content):
        try:
            return cast(object, json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return None


def _json_repair_candidates(content: str) -> list[str]:
    stripped = _strip_markdown_code_fences(content)
    extracted = _extract_largest_json_object(stripped)
    if extracted is None:
        extracted = _extract_from_first_object_start(stripped)

    raw_candidates = [stripped]
    if extracted is not None and extracted != stripped:
        raw_candidates.append(extracted)

    candidates: list[str] = []
    seen: set[str] = set()
    for candidate in raw_candidates:
        normalized = _remove_trailing_commas(candidate.strip())
        repaired = _close_truncated_json(normalized)
        for value in (normalized, repaired):
            if value and value not in seen:
                candidates.append(value)
                seen.add(value)
    return candidates


def _strip_markdown_code_fences(content: str) -> str:
    stripped = content.strip()
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```"):
        closing_index = next(
            (
                index
                for index in range(len(lines) - 1, 0, -1)
                if lines[index].strip().startswith("```")
            ),
            None,
        )
        if closing_index is not None:
            return "\n".join(lines[1:closing_index]).strip()
    return stripped


def _extract_largest_json_object(content: str) -> str | None:
    candidates: list[str] = []
    start_index: int | None = None
    depth = 0
    in_string = False
    escaping = False

    for index, character in enumerate(content):
        if in_string:
            if escaping:
                escaping = False
            elif character == "\\":
                escaping = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            if depth == 0:
                start_index = index
            depth += 1
        elif character == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start_index is not None:
                candidates.append(content[start_index : index + 1])
                start_index = None

    if not candidates:
        return None
    return max(candidates, key=len)


def _extract_from_first_object_start(content: str) -> str | None:
    start_index = content.find("{")
    if start_index < 0:
        return None
    return content[start_index:].strip()


def _remove_trailing_commas(content: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", content)


def _close_truncated_json(content: str) -> str:
    expected_closers: list[str] = []
    in_string = False
    escaping = False

    for character in content:
        if in_string:
            if escaping:
                escaping = False
            elif character == "\\":
                escaping = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "{":
            expected_closers.append("}")
        elif character == "[":
            expected_closers.append("]")
        elif character in ("}", "]") and expected_closers:
            if expected_closers[-1] == character:
                expected_closers.pop()

    repaired = content.rstrip()
    if in_string:
        repaired += '"'
    while expected_closers:
        repaired = re.sub(r",\s*$", "", repaired)
        repaired += expected_closers.pop()
    return _remove_trailing_commas(repaired)
