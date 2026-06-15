import re
from collections.abc import Mapping
from typing import Any, Literal, Protocol, cast

from vuls.agent_intelligence import (
    AgentCriticResult,
    AgentExecutionContext,
    AgentExecutionResult,
    AgentTask,
    AgentWorkflow,
    critic_review_agent_outputs,
    execute_agent_workflow,
    plan_agent_workflow,
)
from vuls.bot.messages import (
    ProjectGenerationReply,
    ProjectIntakeResult,
    ProjectStatusView,
    ProjectSummary,
    TelegramUserIdentity,
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
from vuls.generation.orchestrator import ProjectGenerationResult
from vuls.github.schemas import GitHubExportRequest, GitHubExportResult
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
from vuls.reference_analysis import (
    ReferenceAnalysis,
    ReferenceInput,
    analyze_references,
    load_reference_analysis,
    reference_analysis_prompt_items,
)
from vuls.reference_image_intelligence import (
    ReferenceImageAnalysis,
    load_reference_image_analysis,
    reference_image_analysis_prompt_items,
)
from vuls.reference_product_intelligence import (
    ReferenceProductAnalysis,
    ReferenceProductInput,
    analyze_reference_product,
    load_reference_product_analysis,
    reference_product_analysis_prompt_items,
)
from vuls.reference_ux_intelligence import (
    ReferenceUXAnalysis,
    ReferenceUXInput,
    analyze_reference_ux,
    load_reference_ux_analysis,
    reference_ux_analysis_prompt_items,
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

    def get_by_telegram_user_id(self, telegram_user_id: int) -> JsonObject: ...


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

    def list_projects_for_owner(
        self,
        owner_profile_id: str,
        *,
        limit: int = 10,
    ) -> list[JsonObject]: ...

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
    ) -> ProjectGenerationResult: ...


class GitHubExportServiceProtocol(Protocol):
    def export_project(self, request: GitHubExportRequest) -> GitHubExportResult: ...


class RuntimeTelegramFlowService:
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
    ) -> None:
        self._settings = settings
        self._user_repository = user_repository
        self._project_repository = project_repository
        self._memory_service = memory_service
        self._llm_gateway = llm_gateway
        self._template_registry = template_registry
        self._generation_orchestrator = generation_orchestrator
        self._github_export_service = github_export_service

    def register_user(self, identity: TelegramUserIdentity) -> None:
        self._upsert_profile(identity)

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult:
        profile = self._upsert_profile(identity)
        profile_id = _row_id(profile)
        normalized = self._llm_gateway.normalize_brief(
            BriefNormalizationRequest(
                user_idea=idea,
                language_code=identity.language_code,
            )
        ).brief
        selection = self._template_registry.select_template(idea)
        selected_template_key = selection.selected_key
        project = self._project_repository.create_project(
            owner_profile_id=profile_id,
            title=normalized.title,
            slug=_slugify(normalized.title),
            brief=_project_brief_payload(
                raw_idea=idea,
                brief=normalized,
                selection=selection,
            ),
        )
        project_id = _row_id(project)

        self._memory_service.record_project_goal(
            profile_id=profile_id,
            project_id=project_id,
            goal=normalized.goal,
        )
        for requirement in normalized.must_have_features:
            self._memory_service.record_extracted_requirement(
                profile_id=profile_id,
                project_id=project_id,
                requirement=requirement,
            )

        return ProjectIntakeResult(
            project_id=project_id,
            status=_project_status(project),
            message=f"{normalized.title}: {normalized.goal}",
            clarification_questions=_clarification_questions(selection),
            recommended_template=selected_template_key,
        )

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply:
        profile = self._get_profile(identity)
        profile_id = _row_id(profile)
        project = self._project_repository.get_project(project_id)
        template_key = _template_key(project)
        brief = _brief_from_project(project)

        try:
            self._project_repository.update_project_status(
                project_id=project_id,
                status=ProjectStatus.GENERATING,
            )
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
            if export == "github":
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

            self._project_repository.update_project_status(
                project_id=project_id,
                status=ProjectStatus.COMPLETED,
            )
            return ProjectGenerationReply(
                project_id=project_id,
                status="completed",
                template=generation.template_key,
                github_url=github_url,
                zip_artifact_id=generation.zip_artifact_id if export == "zip" else None,
            )
        except Exception:
            self._project_repository.update_project_status(
                project_id=project_id,
                status=ProjectStatus.FAILED,
                error={"code": "generation_failed"},
            )
            return ProjectGenerationReply(
                project_id=project_id,
                status="failed",
                template=template_key,
            )

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]:
        profile = self._get_profile(identity)
        return [
            ProjectSummary(
                project_id=_row_id(project),
                title=str(project.get("title", "Untitled project")),
                status=_project_status(project),
            )
            for project in self._project_repository.list_projects_for_owner(
                _row_id(profile),
                limit=10,
            )
        ]

    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None:
        profile = self._get_profile(identity)
        projects = self._project_repository.list_projects_for_owner(_row_id(profile), limit=1)
        if not projects:
            return None

        project = projects[0]
        return ProjectStatusView(
            project_id=_row_id(project),
            title=str(project.get("title", "Untitled project")),
            status=_project_status(project),
            template=_optional_string(project.get("selected_template_key"))
            or _optional_string(_brief_mapping(project).get("selected_template_key")),
            export=_export_mode(project.get("export")),
            url=_optional_string(project.get("repository_url"))
            or _optional_string(project.get("github_url")),
        )

    def _upsert_profile(self, identity: TelegramUserIdentity) -> Mapping[str, Any]:
        return self._user_repository.upsert_profile(
            telegram_user_id=identity.telegram_user_id,
            telegram_username=identity.username,
            display_name=identity.display_name,
            language_code=identity.language_code,
        )

    def _get_profile(self, identity: TelegramUserIdentity) -> Mapping[str, Any]:
        return self._user_repository.get_by_telegram_user_id(identity.telegram_user_id)


def _project_brief_payload(
    *,
    raw_idea: str,
    brief: ProjectBrief,
    selection: TemplateSelection,
    reference_image_analysis: ReferenceImageAnalysis | None = None,
) -> dict[str, Any]:
    intelligence = build_product_intelligence(
        raw_idea=raw_idea,
        brief=brief,
        selected_template_key=selection.selected_key,
    )
    reference_analysis = analyze_references(
        ReferenceInput(
            domain=intelligence.product_memory.domain,
            user_intent=raw_idea,
            image_analysis=reference_image_analysis,
            platform="telegram_mini_app",
        )
    )
    reference_product_analysis = _build_reference_product_analysis(
        raw_idea=raw_idea,
        domain=intelligence.product_memory.domain,
        reference_analysis=reference_analysis,
        reference_image_analysis=reference_image_analysis,
        platform="telegram_mini_app",
    )
    reference_ux_analysis = _build_reference_ux_analysis(
        raw_idea=raw_idea,
        domain=intelligence.product_memory.domain,
        reference_analysis=reference_analysis,
        reference_product_analysis=reference_product_analysis,
        reference_image_analysis=reference_image_analysis,
        platform="telegram_mini_app",
    )
    design_contract = build_design_contract(
        DesignInput(
            product_brief=intelligence.product_brief,
            domain=intelligence.product_memory.domain,
            user_prompt=raw_idea,
            references=[
                *_reference_product_design_references(reference_product_analysis),
                *_reference_ux_design_references(reference_ux_analysis),
            ],
            reference_analysis=reference_analysis,
            platform="telegram_mini_app",
        )
    )
    agent_task = AgentTask(
        user_prompt=raw_idea,
        domain=intelligence.product_memory.domain,
        platform="telegram_mini_app",
    )
    agent_workflow = plan_agent_workflow(agent_task)
    agent_execution = execute_agent_workflow(
        agent_workflow,
        AgentExecutionContext(
            user_prompt=raw_idea,
            product_intelligence=intelligence,
            reference_analysis=reference_analysis,
            design_contract=design_contract,
            reference_image_analysis=reference_image_analysis,
        ),
    )
    agent_critic = critic_review_agent_outputs(
        task=agent_task,
        workflow=agent_workflow,
        execution_results=agent_execution,
    )
    payload = {
        "raw_idea": raw_idea,
        "normalized_brief": brief.model_dump(mode="json"),
        "selected_template_key": selection.selected_key,
        "template_confidence": selection.confidence,
        "reference_analysis": reference_analysis.model_dump(mode="json"),
        "design_contract": design_contract.model_dump(mode="json"),
        "agent_workflow": agent_workflow.model_dump(mode="json"),
        "agent_execution": [
            result.model_dump(mode="json") for result in agent_execution
        ],
        "agent_critic": agent_critic.model_dump(mode="json"),
        **intelligence.to_project_brief_payload(),
    }
    if reference_image_analysis is not None:
        payload["reference_image_analysis"] = reference_image_analysis.model_dump(mode="json")
    if reference_product_analysis is not None:
        payload["reference_product_analysis"] = reference_product_analysis.model_dump(
            mode="json"
        )
    if reference_ux_analysis is not None:
        payload["reference_ux_analysis"] = reference_ux_analysis.model_dump(mode="json")
    return payload


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
    reference_image_analysis = _reference_image_analysis_from_project(project)
    if reference_image_analysis is not None:
        project_items.extend(reference_image_analysis_prompt_items(reference_image_analysis))
    project_items.extend(
        reference_analysis_prompt_items(_reference_analysis_from_project(project))
    )
    reference_product_analysis = _reference_product_analysis_from_project(project)
    if reference_product_analysis is not None:
        project_items.extend(reference_product_analysis_prompt_items(reference_product_analysis))
    reference_ux_analysis = _reference_ux_analysis_from_project(project)
    if reference_ux_analysis is not None:
        project_items.extend(reference_ux_analysis_prompt_items(reference_ux_analysis))
    project_items.extend(
        design_contract_prompt_items(_design_contract_from_project(project))
    )
    project_items.extend(_agent_workflow_from_project(project).prompt_items())
    for result in _agent_execution_from_project(project):
        project_items.extend(result.prompt_items())
    project_items.extend(_agent_critic_from_project(project).prompt_items())
    return augmented


def _build_reference_product_analysis(
    *,
    raw_idea: str,
    domain: str,
    reference_analysis: ReferenceAnalysis,
    reference_image_analysis: ReferenceImageAnalysis | None,
    platform: DesignPlatform,
) -> ReferenceProductAnalysis | None:
    if reference_image_analysis is None:
        return None
    analysis = analyze_reference_product(
        ReferenceProductInput(
            reference_analysis=reference_analysis,
            image_analysis=reference_image_analysis,
            user_intent=raw_idea,
            domain=domain,
            platform=platform,
        )
    )
    return None if analysis.product_type == "Unknown" else analysis


def _reference_product_design_references(
    analysis: ReferenceProductAnalysis | None,
) -> list[str]:
    if analysis is None:
        return []
    return reference_product_analysis_prompt_items(analysis)


def _build_reference_ux_analysis(
    *,
    raw_idea: str,
    domain: str,
    reference_analysis: ReferenceAnalysis,
    reference_product_analysis: ReferenceProductAnalysis | None,
    reference_image_analysis: ReferenceImageAnalysis | None,
    platform: DesignPlatform,
) -> ReferenceUXAnalysis | None:
    if reference_image_analysis is None:
        return None
    analysis = analyze_reference_ux(
        ReferenceUXInput(
            reference_analysis=reference_analysis,
            reference_product_analysis=reference_product_analysis,
            image_analysis=reference_image_analysis,
            user_intent=raw_idea,
            domain=domain,
            platform=platform,
        )
    )
    return None if analysis.primary_goal == "Unknown" else analysis


def _reference_ux_design_references(
    analysis: ReferenceUXAnalysis | None,
) -> list[str]:
    if analysis is None:
        return []
    return reference_ux_analysis_prompt_items(analysis)


def _reference_product_analysis_from_project(
    project: Mapping[str, Any],
) -> ReferenceProductAnalysis | None:
    payload = _brief_mapping(project)
    return load_reference_product_analysis(
        payload=payload,
        reference_analysis=_reference_analysis_from_project(project),
        image_analysis=_reference_image_analysis_from_project(project),
        user_intent=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        domain=_product_intelligence_from_project(project).product_memory.domain,
        platform=_design_platform_from_payload(payload),
    )


def _reference_ux_analysis_from_project(
    project: Mapping[str, Any],
) -> ReferenceUXAnalysis | None:
    payload = _brief_mapping(project)
    return load_reference_ux_analysis(
        payload=payload,
        reference_analysis=_reference_analysis_from_project(project),
        reference_product_analysis=_reference_product_analysis_from_project(project),
        image_analysis=_reference_image_analysis_from_project(project),
        user_intent=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        domain=_product_intelligence_from_project(project).product_memory.domain,
        platform=_design_platform_from_payload(payload),
    )


def _design_contract_from_project(project: Mapping[str, Any]) -> DesignContract:
    payload = _brief_mapping(project)
    intelligence = _product_intelligence_from_project(project)
    reference_product_analysis = _reference_product_analysis_from_project(project)
    reference_ux_analysis = _reference_ux_analysis_from_project(project)
    return load_design_contract(
        payload=payload,
        product_brief=intelligence.product_brief,
        domain=intelligence.product_memory.domain,
        user_prompt=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        platform=_design_platform_from_payload(payload),
        references=[
            *_reference_product_design_references(reference_product_analysis),
            *_reference_ux_design_references(reference_ux_analysis),
        ],
        reference_analysis=_reference_analysis_from_project(project),
    )


def _agent_workflow_from_project(project: Mapping[str, Any]) -> AgentWorkflow:
    payload = _brief_mapping(project)
    existing = payload.get("agent_workflow")
    if isinstance(existing, Mapping):
        return AgentWorkflow.model_validate(dict(existing))

    intelligence = _product_intelligence_from_project(project)
    return plan_agent_workflow(
        AgentTask(
            user_prompt=str(payload.get("raw_idea", project.get("title", "Build a product"))),
            domain=intelligence.product_memory.domain,
            platform=_design_platform_from_payload(payload),
        )
    )


def _agent_execution_from_project(project: Mapping[str, Any]) -> list[AgentExecutionResult]:
    payload = _brief_mapping(project)
    existing = payload.get("agent_execution")
    if isinstance(existing, list):
        return [AgentExecutionResult.model_validate(item) for item in existing]

    return execute_agent_workflow(
        _agent_workflow_from_project(project),
        _agent_execution_context_from_project(project),
    )


def _agent_critic_from_project(project: Mapping[str, Any]) -> AgentCriticResult:
    payload = _brief_mapping(project)
    existing = payload.get("agent_critic")
    if isinstance(existing, Mapping):
        return AgentCriticResult.model_validate(dict(existing))

    workflow = _agent_workflow_from_project(project)
    return critic_review_agent_outputs(
        task=workflow.task,
        workflow=workflow,
        execution_results=_agent_execution_from_project(project),
    )


def _agent_execution_context_from_project(
    project: Mapping[str, Any],
) -> AgentExecutionContext:
    payload = _brief_mapping(project)
    return AgentExecutionContext(
        user_prompt=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        product_intelligence=_product_intelligence_from_project(project),
        reference_analysis=_reference_analysis_from_project(project),
        design_contract=_design_contract_from_project(project),
        reference_image_analysis=_reference_image_analysis_from_project(project),
    )


def _reference_image_analysis_from_project(
    project: Mapping[str, Any],
) -> ReferenceImageAnalysis | None:
    return load_reference_image_analysis(payload=_brief_mapping(project))


def _reference_analysis_from_project(project: Mapping[str, Any]) -> ReferenceAnalysis:
    payload = _brief_mapping(project)
    intelligence = _product_intelligence_from_project(project)
    return load_reference_analysis(
        payload=payload,
        domain=intelligence.product_memory.domain,
        user_intent=str(payload.get("raw_idea", project.get("title", "Build a product"))),
        image_analysis=_reference_image_analysis_from_project(project),
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


def _brief_from_project(project: Mapping[str, Any]) -> ProjectBrief:
    brief_mapping = _brief_mapping(project)
    normalized_brief = brief_mapping.get("normalized_brief")
    if isinstance(normalized_brief, Mapping):
        return ProjectBrief.model_validate(dict(normalized_brief))

    return ProjectBrief(
        title=str(project.get("title", "Untitled project")),
        goal=str(brief_mapping.get("raw_idea", project.get("title", "Build a product"))),
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


def _project_status(project: Mapping[str, Any]) -> str:
    return str(project.get("status", ProjectStatus.DRAFT.value))


def _row_id(row: Mapping[str, Any]) -> str:
    return str(row["id"])


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.lower()).strip("-")
    normalized = re.sub(r"-+", "-", normalized)
    return normalized or "vuls-project"


def _clarification_questions(selection: TemplateSelection) -> list[str]:
    if not selection.needs_clarification or selection.clarification_question is None:
        return []
    return [selection.clarification_question]


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _export_mode(value: Any) -> Literal["zip", "github"] | None:
    if value == "zip":
        return "zip"
    if value == "github":
        return "github"
    return None
