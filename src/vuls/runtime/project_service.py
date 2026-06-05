import re
from collections.abc import Mapping
from typing import Any, Protocol, cast

from vuls.api.routes.projects import (
    CreateProjectRequest,
    GenerateProjectRequest,
    ProductBriefResult,
    ProductMemoryResult,
    ProjectCreateResult,
    ProjectDetailResult,
    ProjectGenerationResult,
    ProjectRoadmapResult,
)
from vuls.core.config import Settings
from vuls.db.client import JsonObject
from vuls.db.models import ProjectStatus
from vuls.design_intelligence import (
    DesignContract,
    DesignInput,
    DesignPlatform,
    build_design_contract,
    design_contract_prompt_items,
    load_design_contract,
)
from vuls.generation.orchestrator import ProjectGenerationResult as OrchestratedGenerationResult
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult
from vuls.llm.gateway import (
    LLMGatewayError,
    LLMOutputValidationError,
    LLMProviderUnavailableError,
)
from vuls.llm.schemas import (
    BriefNormalizationRequest,
    BriefNormalizationResponse,
    GeneratedProjectManifest,
    ProjectBrief,
)
from vuls.memory.schemas import MemoryContext
from vuls.product_intelligence import (
    ProductIntelligence,
    build_product_intelligence,
    load_product_intelligence,
    product_intelligence_prompt_items,
)
from vuls.templates.schemas import TemplateSelection


class UserRepositoryProtocol(Protocol):
    def upsert_profile(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        display_name: str | None,
        language_code: str,
    ) -> JsonObject: ...


class ProjectRepositoryProtocol(Protocol):
    def create_project(
        self,
        *,
        owner_profile_id: str,
        title: str,
        slug: str,
        brief: Mapping[str, Any],
    ) -> JsonObject: ...

    def get_project(self, project_id: str) -> JsonObject: ...

    def update_project_status(
        self,
        *,
        project_id: str,
        status: ProjectStatus,
        error: Mapping[str, Any] | None = None,
    ) -> JsonObject: ...


class MemoryServiceProtocol(Protocol):
    def record_project_goal(self, *, profile_id: str, project_id: str, goal: str) -> object: ...

    def record_extracted_requirement(
        self,
        *,
        profile_id: str,
        project_id: str,
        requirement: str,
    ) -> object: ...

    def build_context(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit_per_type: int = 5,
    ) -> MemoryContext: ...


class BriefNormalizationGatewayProtocol(Protocol):
    def normalize_brief(
        self,
        request: BriefNormalizationRequest,
    ) -> BriefNormalizationResponse: ...


class TemplateRegistryProtocol(Protocol):
    def select_template(self, user_intent: str) -> TemplateSelection: ...


class ProjectGenerationOrchestratorProtocol(Protocol):
    def generate_project(
        self,
        *,
        project_id: str,
        generation_run_id: str | None,
        template_key: str,
        brief: ProjectBrief,
        memory_context: dict[str, list[str]] | None = None,
    ) -> OrchestratedGenerationResult: ...


class GitHubExportServiceProtocol(Protocol):
    def export_project(self, request: GitHubExportRequest) -> GitHubExportResult: ...


class GitHubRepositoryProtocol(Protocol):
    def get_repository_for_project(self, project_id: str) -> JsonObject | None: ...


class RuntimeProjectGenerationError(RuntimeError):
    def __init__(self, *, project_id: str, code: str, message: str) -> None:
        super().__init__(message)
        self.project_id = project_id
        self.code = code
        self.message = message

    def to_error_payload(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
        }

    def to_response_payload(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": "failed",
            "error_code": self.code,
            "message": self.message,
            "error": self.to_error_payload(),
        }


class RuntimeProjectService:
    def __init__(
        self,
        *,
        settings: Settings,
        user_repository: UserRepositoryProtocol,
        project_repository: ProjectRepositoryProtocol,
        memory_service: MemoryServiceProtocol,
        llm_gateway: BriefNormalizationGatewayProtocol,
        template_registry: TemplateRegistryProtocol,
        generation_orchestrator: ProjectGenerationOrchestratorProtocol,
        github_export_service: GitHubExportServiceProtocol,
        github_repository: GitHubRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._user_repository = user_repository
        self._project_repository = project_repository
        self._memory_service = memory_service
        self._llm_gateway = llm_gateway
        self._template_registry = template_registry
        self._generation_orchestrator = generation_orchestrator
        self._github_export_service = github_export_service
        self._github_repository = github_repository

    def create_project(self, request: CreateProjectRequest) -> ProjectCreateResult:
        profile = self._user_repository.upsert_profile(
            telegram_user_id=request.telegram_user_id,
            telegram_username=None,
            display_name=None,
            language_code=request.language_code,
        )
        profile_id = _row_id(profile)
        try:
            brief = self._llm_gateway.normalize_brief(
                BriefNormalizationRequest(
                    user_idea=request.idea,
                    language_code=request.language_code,
                )
            ).brief
        except LLMGatewayError as exc:
            raise _generation_error_from_llm_exception("pending", exc) from exc
        selection = self._template_registry.select_template(request.idea)
        project = self._project_repository.create_project(
            owner_profile_id=profile_id,
            title=brief.title,
            slug=_slugify(brief.title),
            brief=_project_brief_payload(
                raw_idea=request.idea,
                brief=brief,
                selection=selection,
            ),
        )
        project_id = _row_id(project)

        self._memory_service.record_project_goal(
            profile_id=profile_id,
            project_id=project_id,
            goal=brief.goal,
        )
        for requirement in brief.must_have_features:
            self._memory_service.record_extracted_requirement(
                profile_id=profile_id,
                project_id=project_id,
                requirement=requirement,
            )

        return ProjectCreateResult(
            project_id=project_id,
            status="clarifying",
            next_message=_next_message(brief, selection),
        )

    def generate_project(
        self,
        project_id: str,
        request: GenerateProjectRequest,
    ) -> ProjectGenerationResult:
        project = self._project_repository.get_project(project_id)
        profile_id = str(project["owner_profile_id"])
        brief = _brief_from_project(project)
        template_key = _template_key(project)

        self._project_repository.update_project_status(
            project_id=project_id,
            status=ProjectStatus.GENERATING,
        )
        try:
            memory_context = self._memory_service.build_context(
                profile_id=profile_id,
                project_id=project_id,
            ).to_prompt_context()
            memory_context = _with_product_memory(project=project, memory_context=memory_context)
            generation = self._generation_orchestrator.generate_project(
                project_id=project_id,
                generation_run_id=None,
                template_key=template_key,
                brief=brief,
                memory_context=memory_context,
            )

            github_url: str | None = None
            if request.export == "github":
                self._project_repository.update_project_status(
                    project_id=project_id,
                    status=ProjectStatus.EXPORTING,
                )
                manifest = cast(GeneratedProjectManifest, generation.manifest)
                github_result = self._github_export_service.export_project(
                    GitHubExportRequest(
                        project_id=project_id,
                        owner=self._settings.github_owner,
                        repo_name=brief.title,
                        manifest=manifest,
                        private=self._settings.github_default_private,
                        description=manifest.readme_summary,
                    )
                )
                github_url = github_result.html_url
        except LLMGatewayError as exc:
            generation_error = _generation_error_from_llm_exception(project_id, exc)
            self._project_repository.update_project_status(
                project_id=project_id,
                status=ProjectStatus.FAILED,
                error=generation_error.to_error_payload(),
            )
            raise generation_error from exc

        self._project_repository.update_project_status(
            project_id=project_id,
            status=ProjectStatus.COMPLETED,
        )
        return ProjectGenerationResult(
            project_id=project_id,
            status="completed",
            template=generation.template_key,
            github_url=github_url,
            zip_artifact_id=generation.zip_artifact_id if request.export == "zip" else None,
        )

    def get_project(self, project_id: str) -> ProjectDetailResult:
        project = self._project_repository.get_project(project_id)
        repository = self._github_repository.get_repository_for_project(project_id)

        return ProjectDetailResult(
            project_id=_row_id(project),
            title=str(project.get("title", "Untitled project")),
            status=str(project.get("status", ProjectStatus.DRAFT.value)),
            selected_template_key=_template_key(project),
            repository_url=_repository_url(repository),
            updated_at=str(project.get("updated_at", "")),
        )

    def get_product_brief(self, project_id: str) -> ProductBriefResult:
        project = self._project_repository.get_project(project_id)
        intelligence = _product_intelligence_from_project(project)
        return ProductBriefResult(
            project_id=_row_id(project),
            brief=intelligence.product_brief,
        )

    def get_project_roadmap(self, project_id: str) -> ProjectRoadmapResult:
        project = self._project_repository.get_project(project_id)
        intelligence = _product_intelligence_from_project(project)
        return ProjectRoadmapResult(
            project_id=_row_id(project),
            roadmap=intelligence.roadmap,
        )

    def get_project_memory(self, project_id: str) -> ProductMemoryResult:
        project = self._project_repository.get_project(project_id)
        intelligence = _product_intelligence_from_project(project)
        return ProductMemoryResult(
            project_id=_row_id(project),
            memory=intelligence.product_memory,
        )


def _project_brief_payload(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    selection: TemplateSelection,
) -> dict[str, Any]:
    intelligence = build_product_intelligence(
        raw_idea=raw_idea,
        brief=brief,
        selected_template_key=selection.selected_key,
    )
    design_contract = build_design_contract(
        DesignInput(
            product_brief=intelligence.product_brief,
            domain=intelligence.product_memory.domain,
            user_prompt=raw_idea,
            platform="telegram_mini_app",
        )
    )
    return {
        "raw_idea": raw_idea,
        "normalized_brief": brief.model_dump(mode="json"),
        "selected_template_key": selection.selected_key,
        "template_confidence": selection.confidence,
        "design_contract": design_contract.model_dump(mode="json"),
        **intelligence.to_project_brief_payload(),
    }


def _with_product_memory(
    *,
    project: Mapping[str, Any],
    memory_context: dict[str, list[str]],
) -> dict[str, list[str]]:
    augmented = {key: list(value) for key, value in memory_context.items()}
    project_items = augmented.setdefault("project", [])
    project_items.extend(
        product_intelligence_prompt_items(_product_intelligence_from_project(project))
    )
    project_items.extend(
        design_contract_prompt_items(_design_contract_from_project(project))
    )
    return augmented


def _design_contract_from_project(project: Mapping[str, Any]) -> DesignContract:
    payload = _brief_mapping(project)
    intelligence = _product_intelligence_from_project(project)
    return load_design_contract(
        payload=payload,
        product_brief=intelligence.product_brief,
        domain=intelligence.product_memory.domain,
        user_prompt=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        platform=_design_platform_from_payload(payload),
    )


def _product_intelligence_from_project(project: Mapping[str, Any]) -> ProductIntelligence:
    payload = _brief_mapping(project)
    return load_product_intelligence(
        payload=payload,
        raw_idea=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        brief=_brief_from_project(project),
        selected_template_key=_template_key(project),
    )


def _design_platform_from_payload(payload: Mapping[str, Any]) -> DesignPlatform:
    platform = payload.get("platform")
    if platform in ("telegram_mini_app", "web", "mobile"):
        return cast(DesignPlatform, platform)
    return "telegram_mini_app"


def _generation_error_from_llm_exception(
    project_id: str,
    exc: LLMGatewayError,
) -> RuntimeProjectGenerationError:
    if isinstance(exc, LLMOutputValidationError):
        return RuntimeProjectGenerationError(
            project_id=project_id,
            code="llm_output_validation_failed",
            message="Vuls could not parse the generated project manifest. Please retry.",
        )
    if isinstance(exc, LLMProviderUnavailableError):
        return RuntimeProjectGenerationError(
            project_id=project_id,
            code="llm_provider_unavailable",
            message="No available LLM providers.",
        )
    return RuntimeProjectGenerationError(
        project_id=project_id,
        code="llm_generation_failed",
        message="Vuls could not generate this project safely. Please retry.",
    )


def _next_message(brief: ProjectBrief, selection: TemplateSelection) -> str:
    parts = [f"{brief.title}: {brief.goal}"]
    if selection.selected_key is not None:
        parts.append(f"Recommended template: {selection.selected_key}")
    if selection.needs_clarification and selection.clarification_question is not None:
        parts.append(selection.clarification_question)
    return "\n".join(parts)


def _brief_from_project(project: Mapping[str, Any]) -> ProjectBrief:
    brief = _brief_mapping(project).get("normalized_brief")
    if isinstance(brief, Mapping):
        return ProjectBrief.model_validate(dict(brief))
    return ProjectBrief(
        title=str(project.get("title", "Untitled project")),
        goal=str(project.get("title", "Build a product")),
        target_users=["owner"],
        must_have_features=["dashboard"],
        language_code="en",
    )


def _brief_mapping(project: Mapping[str, Any]) -> Mapping[str, Any]:
    brief = project.get("brief", {})
    return brief if isinstance(brief, Mapping) else {}


def _template_key(project: Mapping[str, Any]) -> str:
    project_template_key = _optional_string(project.get("selected_template_key"))
    if project_template_key is not None:
        return project_template_key

    brief_template_key = _optional_string(_brief_mapping(project).get("selected_template_key"))
    if brief_template_key is not None:
        return brief_template_key

    return "saas"


def _repository_url(repository: Mapping[str, Any] | None) -> str | None:
    if repository is None:
        return None
    return _optional_string(repository.get("html_url"))


def _row_id(row: Mapping[str, Any]) -> str:
    return str(row["id"])


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or "vuls-project"


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
