import json
from typing import Protocol

from pydantic import BaseModel, ValidationError

from vuls.llm.prompts import build_brief_normalization_prompt, build_project_manifest_prompt
from vuls.llm.safety import evaluate_generation_safety
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    GeneratedProjectManifest,
    LLMClientResponse,
    LLMMessage,
    LLMUsage,
    ProjectBrief,
    ProjectManifestRequest,
    ProjectManifestResponse,
)

DEFAULT_LLM_MODEL = "gpt-5"


class LLMGatewayError(RuntimeError):
    """Base exception for expected LLM gateway failures."""


class LLMTransientError(LLMGatewayError):
    """Raised for retryable provider failures."""


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
        max_attempts: int = 3,
    ) -> None:
        self._client = client
        self._model = model
        self._max_attempts = max(max_attempts, 1)

    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse:
        self._ensure_safe(request.user_idea)
        response = self._complete_with_retries(
            messages=build_brief_normalization_prompt(request),
            response_schema=ProjectBrief,
        )
        return BriefNormalizationResponse(
            brief=_parse_json_model(response.content, ProjectBrief),
            usage=response.usage,
            model=self._model,
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
        response = self._complete_with_retries(
            messages=build_project_manifest_prompt(request),
            response_schema=GeneratedProjectManifest,
        )
        return ProjectManifestResponse(
            manifest=_parse_json_model(response.content, GeneratedProjectManifest),
            usage=response.usage,
            model=self._model,
        )

    def _complete_with_retries(
        self,
        *,
        messages: list[LLMMessage],
        response_schema: type[BaseModel],
    ) -> LLMClientResponse:
        last_error: LLMTransientError | None = None

        for _attempt in range(self._max_attempts):
            try:
                return self._client.complete_json(
                    model=self._model,
                    messages=messages,
                    response_schema=response_schema,
                )
            except LLMTransientError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error

        return LLMClientResponse(content="{}", usage=LLMUsage())

    def _ensure_safe(self, text: str) -> None:
        safety = evaluate_generation_safety(text)
        if not safety.allowed:
            raise LLMSafetyError(f"{safety.code}: {safety.reason}")


def _parse_json_model[T: BaseModel](content: str, model: type[T]) -> T:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMOutputValidationError("Model output was not valid JSON.") from exc

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise LLMOutputValidationError("Model output did not match the expected schema.") from exc
