from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerationRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationRunCreate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    input_summary: str = Field(min_length=1)
    template_version_id: str | None = None
    status: GenerationRunStatus = GenerationRunStatus.QUEUED
    usage: dict[str, Any] = Field(default_factory=dict)


class GenerationRunTerminalUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: GenerationRunStatus
    completed_at: str
    output_manifest: dict[str, Any] | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
