from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
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


def get_project_service() -> ProjectService:
    return UnconfiguredProjectService()
