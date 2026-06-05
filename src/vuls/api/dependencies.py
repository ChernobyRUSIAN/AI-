from typing import cast

from fastapi import Request

from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProductBriefResult,
    ProductMemoryResult,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
    ProjectRoadmapResult,
    ProjectService,
)


class UnconfiguredProjectService:
    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult:
        raise RuntimeError("Project service is not configured")

    def generate_project(
        self, project_id: str, request: GenerateProjectRequest
    ) -> ProjectGenerationResult:
        raise RuntimeError("Project service is not configured")

    def get_project(self, project_id: str) -> ProjectDetailResult:
        raise RuntimeError("Project service is not configured")

    def get_product_brief(self, project_id: str) -> ProductBriefResult:
        raise RuntimeError("Project service is not configured")

    def get_project_roadmap(self, project_id: str) -> ProjectRoadmapResult:
        raise RuntimeError("Project service is not configured")

    def get_project_memory(self, project_id: str) -> ProductMemoryResult:
        raise RuntimeError("Project service is not configured")


def get_project_service(request: Request) -> ProjectService:
    runtime = getattr(request.app.state, "runtime", None)
    project_service = getattr(runtime, "project_service", None)
    if project_service is None:
        return UnconfiguredProjectService()
    return cast(ProjectService, project_service)
