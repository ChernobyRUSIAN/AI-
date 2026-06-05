from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from vuls.api.dependencies import get_project_service
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
from vuls.runtime.project_service import RuntimeProjectGenerationError

router = APIRouter(prefix="/internal/projects", tags=["internal"])
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]


@router.post("", response_model=ProjectCreateResult)
def create_project(
    request: CreateProjectRequest,
    project_service: ProjectServiceDependency,
) -> ProjectCreateResult | JSONResponse:
    try:
        return project_service.create_project(request)
    except RuntimeProjectGenerationError as exc:
        return JSONResponse(status_code=502, content=exc.to_response_payload())


@router.post("/{project_id}/generate", response_model=ProjectGenerationResult)
def generate_project(
    project_id: str,
    request: GenerateProjectRequest,
    project_service: ProjectServiceDependency,
) -> ProjectGenerationResult | JSONResponse:
    try:
        return project_service.generate_project(project_id, request)
    except RuntimeProjectGenerationError as exc:
        return JSONResponse(status_code=502, content=exc.to_response_payload())


@router.get("/{project_id}", response_model=ProjectDetailResult)
def get_project(
    project_id: str,
    project_service: ProjectServiceDependency,
) -> ProjectDetailResult:
    return project_service.get_project(project_id)


@router.get("/{project_id}/brief", response_model=ProductBriefResult)
def get_product_brief(
    project_id: str,
    project_service: ProjectServiceDependency,
) -> ProductBriefResult:
    return project_service.get_product_brief(project_id)


@router.get("/{project_id}/roadmap", response_model=ProjectRoadmapResult)
def get_project_roadmap(
    project_id: str,
    project_service: ProjectServiceDependency,
) -> ProjectRoadmapResult:
    return project_service.get_project_roadmap(project_id)


@router.get("/{project_id}/memory", response_model=ProductMemoryResult)
def get_project_memory(
    project_id: str,
    project_service: ProjectServiceDependency,
) -> ProductMemoryResult:
    return project_service.get_project_memory(project_id)
