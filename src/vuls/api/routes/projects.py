from typing import Literal, Protocol

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    telegram_user_id: int
    telegram_chat_id: int
    idea: str = Field(min_length=1)
    language_code: str = Field(min_length=2, max_length=10)


class ProjectCreateResult(BaseModel):
    project_id: str
    status: Literal["clarifying"]
    next_message: str


class GenerateProjectRequest(BaseModel):
    answers: dict[str, object]
    export: Literal["github", "zip"]


class ProjectGenerationResult(BaseModel):
    project_id: str
    status: Literal["completed"]
    template: str
    github_url: str | None
    zip_artifact_id: str | None


class ProjectDetailResult(BaseModel):
    project_id: str
    title: str
    status: str
    selected_template_key: str | None
    repository_url: str | None
    updated_at: str


class ProjectService(Protocol):
    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult: ...

    def generate_project(
        self, project_id: str, request: GenerateProjectRequest
    ) -> ProjectGenerationResult: ...

    def get_project(self, project_id: str) -> ProjectDetailResult: ...
