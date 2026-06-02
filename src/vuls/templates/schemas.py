from pydantic import BaseModel, ConfigDict, Field, field_validator


class TemplateFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    required: bool = True

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        normalized = value.replace("\\", "/")
        if normalized.startswith("/") or ".." in normalized.split("/"):
            raise ValueError("Template file paths must be relative and stay inside the project.")
        return normalized


class TemplateFileBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    files: list[TemplateFile] = Field(min_length=1)


class TemplateManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str = Field(min_length=1)
    default_pages: list[str] = Field(min_length=1)
    default_entities: list[str] = Field(min_length=1)
    default_roles: list[str] = Field(min_length=1)
    keywords: list[str] = Field(min_length=1)
    i18n_keys: list[str] = Field(min_length=1)
    readme_sections: list[str] = Field(min_length=1)

    @field_validator(
        "default_pages",
        "default_entities",
        "default_roles",
        "keywords",
        "i18n_keys",
        "readme_sections",
    )
    @classmethod
    def validate_non_empty_values(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned):
            raise ValueError("Template metadata lists cannot contain empty values.")
        return cleaned


class TemplateDefinition(TemplateManifest):
    prompt_markdown: str = Field(min_length=1)
    file_blueprint: TemplateFileBlueprint


class TemplateSelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_key: str | None
    confidence: float = Field(ge=0.0, le=1.0)
    needs_clarification: bool
    clarification_question: str | None
    scores: dict[str, float]


class TemplateValidationIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_key: str | None
    path: str
    message: str
