from collections.abc import Mapping
from typing import Any, Protocol

from vuls.db.client import JsonObject
from vuls.db.models import MemorySource, MemoryType
from vuls.memory.schemas import (
    ConversationMemory,
    ConversationMessage,
    KnowledgeMemory,
    MemoryContentCategory,
    MemoryContext,
    MemoryFact,
    ProjectMemory,
    ProjectMemorySnapshot,
    UserMemory,
    UserMemorySnapshot,
)
from vuls.memory.summarizer import summarize_conversation


class MemoryRepositoryProtocol(Protocol):
    def load_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[JsonObject]: ...

    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: Mapping[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject: ...


class MemoryService:
    def __init__(self, repository: MemoryRepositoryProtocol) -> None:
        self._repository = repository

    def build_context(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit_per_type: int = 5,
    ) -> MemoryContext:
        limit = max(limit_per_type, 0)
        user_memory = self.get_user_memory(profile_id=profile_id, limit=limit)
        project_memory = self.get_project_memory(
            profile_id=profile_id,
            project_id=project_id,
            limit=limit,
        )

        return MemoryContext(
            profile_id=profile_id,
            project_id=project_id,
            user=[*user_memory.preferences, *user_memory.facts],
            project=[*project_memory.goals, *project_memory.requirements, *project_memory.facts],
            conversation=self.get_recent_conversation(
                profile_id=profile_id,
                project_id=project_id,
                limit=limit,
            ),
            knowledge=[
                _knowledge_memory_from_row(row)
                for row in self._repository.load_memory(
                    profile_id=profile_id,
                    project_id=project_id,
                    memory_type=MemoryType.KNOWLEDGE,
                    limit=limit,
                )
            ],
        )

    def write_fact(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: Mapping[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> MemoryFact:
        row = self._repository.write_memory(
            profile_id=profile_id,
            project_id=project_id,
            memory_type=memory_type,
            source=source,
            content=dict(content),
            summary=summary,
            confidence=confidence,
        )
        return _memory_from_row(row, expected_type=memory_type)

    def record_project_goal(
        self,
        *,
        profile_id: str,
        project_id: str,
        goal: str,
        source: MemorySource = MemorySource.TELEGRAM,
        confidence: float = 1.0,
    ) -> MemoryFact:
        return self.write_fact(
            profile_id=profile_id,
            project_id=project_id,
            memory_type=MemoryType.PROJECT,
            source=source,
            content={
                "category": MemoryContentCategory.PROJECT_GOAL.value,
                "goal": goal,
            },
            summary=goal,
            confidence=confidence,
        )

    def record_extracted_requirement(
        self,
        *,
        profile_id: str,
        project_id: str,
        requirement: str,
        source: MemorySource = MemorySource.TELEGRAM,
        confidence: float = 1.0,
    ) -> MemoryFact:
        return self.write_fact(
            profile_id=profile_id,
            project_id=project_id,
            memory_type=MemoryType.PROJECT,
            source=source,
            content={
                "category": MemoryContentCategory.EXTRACTED_REQUIREMENT.value,
                "requirement": requirement,
            },
            summary=requirement,
            confidence=confidence,
        )

    def record_user_preference(
        self,
        *,
        profile_id: str,
        preference: str,
        source: MemorySource = MemorySource.TELEGRAM,
        confidence: float = 1.0,
    ) -> MemoryFact:
        return self.write_fact(
            profile_id=profile_id,
            project_id=None,
            memory_type=MemoryType.USER,
            source=source,
            content={
                "category": MemoryContentCategory.USER_PREFERENCE.value,
                "preference": preference,
            },
            summary=preference,
            confidence=confidence,
        )

    def record_conversation_summary(
        self,
        *,
        profile_id: str,
        project_id: str,
        messages: list[ConversationMessage],
        confidence: float = 1.0,
        max_summary_chars: int = 1200,
    ) -> MemoryFact:
        raw_messages = [message.model_dump(mode="json") for message in messages]
        summary = summarize_conversation(messages, max_chars=max_summary_chars)

        return self.write_fact(
            profile_id=profile_id,
            project_id=project_id,
            memory_type=MemoryType.CONVERSATION,
            source=MemorySource.TELEGRAM,
            content={"messages": raw_messages},
            summary=summary,
            confidence=confidence,
        )

    def get_project_memory(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit: int = 10,
    ) -> ProjectMemorySnapshot:
        memories = [
            _project_memory_from_row(row)
            for row in self._repository.load_memory(
                profile_id=profile_id,
                project_id=project_id,
                memory_type=MemoryType.PROJECT,
                limit=max(limit, 0),
            )
        ]

        return ProjectMemorySnapshot(
            profile_id=profile_id,
            project_id=project_id,
            goals=[
                memory
                for memory in memories
                if _content_category(memory.content) == MemoryContentCategory.PROJECT_GOAL
            ],
            requirements=[
                memory
                for memory in memories
                if _content_category(memory.content)
                == MemoryContentCategory.EXTRACTED_REQUIREMENT
            ],
            facts=[
                memory
                for memory in memories
                if _content_category(memory.content)
                not in {
                    MemoryContentCategory.PROJECT_GOAL,
                    MemoryContentCategory.EXTRACTED_REQUIREMENT,
                }
            ],
        )

    def get_user_memory(
        self,
        *,
        profile_id: str,
        limit: int = 10,
    ) -> UserMemorySnapshot:
        memories = [
            _user_memory_from_row(row)
            for row in self._repository.load_memory(
                profile_id=profile_id,
                project_id=None,
                memory_type=MemoryType.USER,
                limit=max(limit, 0),
            )
        ]

        return UserMemorySnapshot(
            profile_id=profile_id,
            preferences=[
                memory
                for memory in memories
                if _content_category(memory.content) == MemoryContentCategory.USER_PREFERENCE
            ],
            facts=[
                memory
                for memory in memories
                if _content_category(memory.content) != MemoryContentCategory.USER_PREFERENCE
            ],
        )

    def get_recent_conversation(
        self,
        *,
        profile_id: str,
        project_id: str,
        limit: int = 10,
    ) -> list[ConversationMemory]:
        return [
            _conversation_memory_from_row(row)
            for row in self._repository.load_memory(
                profile_id=profile_id,
                project_id=project_id,
                memory_type=MemoryType.CONVERSATION,
                limit=max(limit, 0),
            )
        ]


def _memory_from_row(row: Mapping[str, Any], *, expected_type: MemoryType) -> MemoryFact:
    match expected_type:
        case MemoryType.USER:
            return _user_memory_from_row(row)
        case MemoryType.PROJECT:
            return _project_memory_from_row(row)
        case MemoryType.CONVERSATION:
            return _conversation_memory_from_row(row)
        case MemoryType.KNOWLEDGE:
            return _knowledge_memory_from_row(row)


def _user_memory_from_row(row: Mapping[str, Any]) -> UserMemory:
    return UserMemory(**_normalized_row(row, expected_type=MemoryType.USER))


def _project_memory_from_row(row: Mapping[str, Any]) -> ProjectMemory:
    return ProjectMemory(**_normalized_row(row, expected_type=MemoryType.PROJECT))


def _conversation_memory_from_row(row: Mapping[str, Any]) -> ConversationMemory:
    return ConversationMemory(**_normalized_row(row, expected_type=MemoryType.CONVERSATION))


def _knowledge_memory_from_row(row: Mapping[str, Any]) -> KnowledgeMemory:
    return KnowledgeMemory(**_normalized_row(row, expected_type=MemoryType.KNOWLEDGE))


def _normalized_row(row: Mapping[str, Any], *, expected_type: MemoryType) -> dict[str, Any]:
    return {
        "id": _optional_string(row.get("id")),
        "profile_id": str(row.get("profile_id", "")),
        "project_id": _optional_string(row.get("project_id")),
        "memory_type": _memory_type(row.get("memory_type", expected_type)),
        "source": _memory_source(row.get("source", MemorySource.SYSTEM)),
        "content": _content(row.get("content", {})),
        "summary": str(row.get("summary", "")),
        "confidence": float(row.get("confidence", 1.0)),
    }


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _memory_type(value: Any) -> MemoryType:
    if isinstance(value, MemoryType):
        return value
    return MemoryType(str(value))


def _memory_source(value: Any) -> MemorySource:
    if isinstance(value, MemorySource):
        return value
    return MemorySource(str(value))


def _content(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {"value": value}


def _content_category(content: Mapping[str, Any]) -> MemoryContentCategory | None:
    value = content.get("category")
    if not isinstance(value, str):
        return None
    try:
        return MemoryContentCategory(value)
    except ValueError:
        return None
