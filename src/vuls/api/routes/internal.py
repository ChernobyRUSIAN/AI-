from typing import Annotated

from fastapi import APIRouter, Depends

from vuls.api.dependencies import get_project_service
from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
    ProjectService,
)

router = APIRouter(prefix="/internal/projects", tags=["internal"])
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


@router.post("", response_model=ProjectCreateResult)
def create_project(
    request: CreateProjectRequest,
    project_service: ProjectServiceDependency,
) -> ProjectCreateResult:
    return project_service.create_project(request)


@router.post("/{project_id}/generate", response_model=ProjectGenerationResult)
def generate_project(
    project_id: str,
    request: GenerateProjectRequest,
    project_service: ProjectServiceDependency,
) -> ProjectGenerationResult:
    return project_service.generate_project(project_id, request)


@router.get("/{project_id}", response_model=ProjectDetailResult)
def get_project(
    project_id: str,
    project_service: ProjectServiceDependency,
) -> ProjectDetailResult:
    return project_service.get_project(project_id)
