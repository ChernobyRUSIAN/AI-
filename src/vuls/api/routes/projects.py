from typing import Literal, Protocol

from pydantic import BaseModel, Field

from vuls.product_intelligence import (
    ProductBriefDocument,
    ProductMemoryDocument,
    ProjectRoadmap,
)


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


class ProductBriefResult(BaseModel):
    project_id: str
    brief: ProductBriefDocument


class ProjectRoadmapResult(BaseModel):
    project_id: str
    roadmap: ProjectRoadmap


class ProductMemoryResult(BaseModel):
    project_id: str
    memory: ProductMemoryDocument


class ProjectService(Protocol):
    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult: ...

    def generate_project(
        self, project_id: str, request: GenerateProjectRequest
    ) -> ProjectGenerationResult: ...

    def get_project(self, project_id: str) -> ProjectDetailResult: ...

    def get_product_brief(self, project_id: str) -> ProductBriefResult: ...

    def get_project_roadmap(self, project_id: str) -> ProjectRoadmapResult: ...

    def get_project_memory(self, project_id: str) -> ProductMemoryResult: ...
