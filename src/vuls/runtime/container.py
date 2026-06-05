from dataclasses import dataclass
from pathlib import Path

from vuls.bot.dispatcher import TelegramDispatcher, create_dispatcher
from vuls.bot.sender import TelegramSender
from vuls.core.config import Settings, load_settings, openai_model_sequence
from vuls.db.client import SupabaseClient, build_supabase_client
from vuls.db.repositories.artifacts import ArtifactRepository
from vuls.db.repositories.audit import AuditRepository
from vuls.db.repositories.github import GitHubRepositoryMetadataRepository
from vuls.db.repositories.memory import MemoryRepository
from vuls.db.repositories.projects import ProjectRepository
from vuls.db.repositories.templates import TemplateRepository
from vuls.db.repositories.users import UserRepository
from vuls.generation.orchestrator import ProjectGenerationOrchestrator
from vuls.github.client import GitHubHttpClient
from vuls.github.service import GitHubApiClientProtocol, GitHubExportService
from vuls.llm.gateway import LLMClient, LLMGateway
from vuls.llm.openai_client import OpenAIResponsesClient
from vuls.memory.service import MemoryService
from vuls.runtime.project_service import RuntimeProjectService
from vuls.runtime.telegram_service import RuntimeTelegramFlowService
from vuls.templates.registry import TemplateRegistry


@dataclass(frozen=True)
class RuntimeContainer:
    settings: Settings
    supabase_client: SupabaseClient
    user_repository: UserRepository
    project_repository: ProjectRepository
    memory_repository: MemoryRepository
    artifact_repository: ArtifactRepository
    github_repository: GitHubRepositoryMetadataRepository
    template_repository: TemplateRepository
    audit_repository: AuditRepository
    memory_service: MemoryService
    template_registry: TemplateRegistry
    llm_client: LLMClient
    llm_gateway: LLMGateway
    github_client: GitHubApiClientProtocol
    github_export_service: GitHubExportService
    generation_orchestrator: ProjectGenerationOrchestrator
    project_service: RuntimeProjectService
    telegram_flow_service: RuntimeTelegramFlowService
    telegram_dispatcher: TelegramDispatcher
    telegram_sender: TelegramSender
    project_workdir: Path
    artifact_dir: Path


def build_runtime_container(
    *,
    settings: Settings | None = None,
    supabase_client: SupabaseClient | None = None,
    llm_client: LLMClient | None = None,
    github_client: GitHubApiClientProtocol | None = None,
) -> RuntimeContainer:
    runtime_settings = settings or load_settings()
    runtime_supabase_client = supabase_client or build_supabase_client(runtime_settings)

    user_repository = UserRepository(runtime_supabase_client)
    project_repository = ProjectRepository(runtime_supabase_client)
    memory_repository = MemoryRepository(runtime_supabase_client)
    artifact_repository = ArtifactRepository(runtime_supabase_client)
    github_repository = GitHubRepositoryMetadataRepository(runtime_supabase_client)
    template_repository = TemplateRepository(runtime_supabase_client)
    audit_repository = AuditRepository(runtime_supabase_client)

    memory_service = MemoryService(memory_repository)
    template_registry = TemplateRegistry()
    runtime_llm_client = llm_client or OpenAIResponsesClient(
        api_key=runtime_settings.openai_api_key,
        base_url=runtime_settings.openai_base_url,
        timeout_seconds=runtime_settings.openai_timeout_seconds,
    )
    configured_models = openai_model_sequence(runtime_settings)
    llm_gateway = LLMGateway(
        client=runtime_llm_client,
        model=configured_models[0],
        fallback_models=configured_models[1:],
    )

    runtime_github_client = github_client or GitHubHttpClient(
        token=runtime_settings.github_token,
        api_base_url=runtime_settings.github_api_base_url,
    )
    github_export_service = GitHubExportService(
        client=runtime_github_client,
        metadata_store=github_repository,
    )

    artifact_dir = _default_artifact_dir(runtime_settings.project_workdir)
    generation_orchestrator = ProjectGenerationOrchestrator(
        gateway=llm_gateway,
        template_registry=template_registry,
        artifact_repository=artifact_repository,
        project_workdir=runtime_settings.project_workdir,
        artifact_dir=artifact_dir,
        zip_max_bytes=runtime_settings.zip_max_bytes,
    )
    project_service = RuntimeProjectService(
        settings=runtime_settings,
        user_repository=user_repository,
        project_repository=project_repository,
        memory_service=memory_service,
        llm_gateway=llm_gateway,
        template_registry=template_registry,
        generation_orchestrator=generation_orchestrator,
        github_export_service=github_export_service,
        github_repository=github_repository,
    )
    telegram_flow_service = RuntimeTelegramFlowService(
        settings=runtime_settings,
        user_repository=user_repository,
        project_repository=project_repository,
        memory_service=memory_service,
        llm_gateway=llm_gateway,
        template_registry=template_registry,
        generation_orchestrator=generation_orchestrator,
        github_export_service=github_export_service,
    )
    telegram_dispatcher = create_dispatcher(telegram_flow_service)
    telegram_sender = TelegramSender.from_token(runtime_settings.telegram_bot_token)

    return RuntimeContainer(
        settings=runtime_settings,
        supabase_client=runtime_supabase_client,
        user_repository=user_repository,
        project_repository=project_repository,
        memory_repository=memory_repository,
        artifact_repository=artifact_repository,
        github_repository=github_repository,
        template_repository=template_repository,
        audit_repository=audit_repository,
        memory_service=memory_service,
        template_registry=template_registry,
        llm_client=runtime_llm_client,
        llm_gateway=llm_gateway,
        github_client=runtime_github_client,
        github_export_service=github_export_service,
        generation_orchestrator=generation_orchestrator,
        project_service=project_service,
        telegram_flow_service=telegram_flow_service,
        telegram_dispatcher=telegram_dispatcher,
        telegram_sender=telegram_sender,
        project_workdir=runtime_settings.project_workdir,
        artifact_dir=artifact_dir,
    )


def _default_artifact_dir(project_workdir: Path) -> Path:
    return project_workdir.parent / "artifacts"
