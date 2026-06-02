from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vuls.db.models import MemorySource, MemoryType


class ConversationDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
    SYSTEM = "system"


class ConversationMessageType(StrEnum):
    TEXT = "text"
    COMMAND = "command"
    CALLBACK = "callback"
    DOCUMENT = "document"
    SYSTEM = "system"


class MemoryContentCategory(StrEnum):
    USER_PREFERENCE = "user_preference"
    PROJECT_GOAL = "project_goal"
    EXTRACTED_REQUIREMENT = "extracted_requirement"
    CONVERSATION_SUMMARY = "conversation_summary"


class ConversationMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    direction: ConversationDirection
    message_type: ConversationMessageType = ConversationMessageType.TEXT
    text: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    telegram_message_id: int | None = None


class MemoryRecordData(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str | None = None
    profile_id: str
    project_id: str | None = None
    source: MemorySource
    content: dict[str, Any] = Field(default_factory=dict)
    summary: str = Field(min_length=1)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class UserMemory(MemoryRecordData):
    memory_type: Literal[MemoryType.USER] = MemoryType.USER


class ProjectMemory(MemoryRecordData):
    memory_type: Literal[MemoryType.PROJECT] = MemoryType.PROJECT


class ConversationMemory(MemoryRecordData):
    memory_type: Literal[MemoryType.CONVERSATION] = MemoryType.CONVERSATION


class KnowledgeMemory(MemoryRecordData):
    memory_type: Literal[MemoryType.KNOWLEDGE] = MemoryType.KNOWLEDGE


MemoryFact = UserMemory | ProjectMemory | ConversationMemory | KnowledgeMemory


class MemoryContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    project_id: str
    user: list[UserMemory] = Field(default_factory=list)
    project: list[ProjectMemory] = Field(default_factory=list)
    conversation: list[ConversationMemory] = Field(default_factory=list)
    knowledge: list[KnowledgeMemory] = Field(default_factory=list)

    def to_prompt_context(self) -> dict[str, list[str]]:
        return {
            "user": [item.summary for item in self.user],
            "project": [item.summary for item in self.project],
            "conversation": [item.summary for item in self.conversation],
            "knowledge": [item.summary for item in self.knowledge],
        }


class ProjectMemorySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    project_id: str
    goals: list[ProjectMemory] = Field(default_factory=list)
    requirements: list[ProjectMemory] = Field(default_factory=list)
    facts: list[ProjectMemory] = Field(default_factory=list)


class UserMemorySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str
    preferences: list[UserMemory] = Field(default_factory=list)
    facts: list[UserMemory] = Field(default_factory=list)
