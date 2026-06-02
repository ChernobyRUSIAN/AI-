from enum import StrEnum

JsonObject = dict[str, object]


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    CLARIFYING = "clarifying"
    GENERATING = "generating"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectStage(StrEnum):
    INTAKE = "intake"
    CLARIFICATION = "clarification"
    TEMPLATE_SELECTION = "template_selection"
    GENERATION = "generation"
    EXPORT = "export"
    COMPLETED = "completed"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MemberRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class MemoryType(StrEnum):
    USER = "user"
    PROJECT = "project"
    CONVERSATION = "conversation"
    KNOWLEDGE = "knowledge"


class MemorySource(StrEnum):
    TELEGRAM = "telegram"
    GENERATION = "generation"
    SYSTEM = "system"
    MANUAL = "manual"


class ArtifactType(StrEnum):
    MANIFEST = "manifest"
    ZIP = "zip"
    README = "readme"
    SOURCE_SNAPSHOT = "source_snapshot"
    LOG = "log"
