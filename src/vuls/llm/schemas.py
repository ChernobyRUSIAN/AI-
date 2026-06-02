from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vuls.templates.schemas import TemplateDefinition


class LLMRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: LLMRole
    content: str = Field(min_length=1)


class LLMUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMClientResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str
    usage: LLMUsage = Field(default_factory=LLMUsage)


class SafetyCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    allowed: bool
    code: str
    reason: str


class ProjectBrief(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    target_users: list[str] = Field(min_length=1)
    must_have_features: list[str] = Field(min_length=1)
    language_code: str = Field(default="en", min_length=2, max_length=10)


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(frozen=True)

    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    required: bool = True


class TemplateSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_template_key: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)


class GeneratedProjectFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    content: str
    purpose: str = Field(min_length=1)

    @field_validator("path")
    @classmethod
    def validate_safe_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("Generated file paths must be relative and stay inside the project.")
        return normalized


class GeneratedEnvironmentVariable(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = True


class GeneratedProjectManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_name: str = Field(min_length=1)
    readme_summary: str = Field(min_length=1)
    tech_stack: list[str] = Field(min_length=1)
    files: list[GeneratedProjectFile] = Field(min_length=1)
    env_vars: list[GeneratedEnvironmentVariable] = Field(default_factory=list)


class BriefNormalizationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    user_idea: str = Field(min_length=1)
    language_code: str = Field(default="en", min_length=2, max_length=10)
    memory_context: dict[str, list[str]] = Field(default_factory=dict)


class ProjectManifestRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    template: TemplateDefinition
    brief: ProjectBrief
    memory_context: dict[str, list[str]] = Field(default_factory=dict)


class BriefNormalizationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    brief: ProjectBrief
    usage: LLMUsage
    model: str


class ProjectManifestResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest: GeneratedProjectManifest
    usage: LLMUsage
    model: str


OutputSchemaName = Literal["ProjectBrief", "GeneratedProjectManifest", "TemplateSelection"]
