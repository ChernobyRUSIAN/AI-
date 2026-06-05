from typing import Any

from vuls.db.client import JsonObject
from vuls.db.models import MemorySource, MemoryType
from vuls.db.repositories.memory import MemoryRepositoryTransientError
from vuls.memory.schemas import ConversationMessage
from vuls.memory.service import MemoryService


class FakeMemoryRepository:
    def __init__(self, rows: dict[tuple[str | None, MemoryType | None], list[JsonObject]]) -> None:
        self.rows = rows
        self.load_calls: list[tuple[str, str | None, MemoryType | None, int]] = []
        self.writes: list[JsonObject] = []

    def load_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[JsonObject]:
        self.load_calls.append((profile_id, project_id, memory_type, limit))
        return self.rows.get((project_id, memory_type), [])

    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: dict[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject:
        row: JsonObject = {
            "id": f"memory-{len(self.writes) + 1}",
            "profile_id": profile_id,
            "project_id": project_id,
            "memory_type": memory_type,
            "source": source,
            "content": content,
            "summary": summary,
            "confidence": confidence,
        }
        self.writes.append(row)
        return row


class FailingMemoryRepository(FakeMemoryRepository):
    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: dict[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject:
        raise MemoryRepositoryTransientError("Supabase memory_items insert failed")


def memory_row(
    *,
    memory_id: str,
    profile_id: str = "profile-1",
    project_id: str | None = "project-1",
    memory_type: MemoryType,
    source: MemorySource,
    summary: str,
    content: dict[str, Any] | None = None,
    confidence: float = 1.0,
) -> JsonObject:
    return {
        "id": memory_id,
        "profile_id": profile_id,
        "project_id": project_id,
        "memory_type": memory_type.value,
        "source": source.value,
        "content": content or {},
        "summary": summary,
        "confidence": confidence,
    }


def test_build_context_loads_bounded_project_memory_for_returning_user() -> None:
    repository = FakeMemoryRepository(
        {
            (None, MemoryType.USER): [
                memory_row(
                    memory_id="memory-user-1",
                    project_id=None,
                    memory_type=MemoryType.USER,
                    source=MemorySource.MANUAL,
                    summary="User prefers Python and FastAPI.",
                )
            ],
            ("project-1", MemoryType.PROJECT): [
                memory_row(
                    memory_id="memory-project-1",
                    memory_type=MemoryType.PROJECT,
                    source=MemorySource.GENERATION,
                    summary="Project is a coffee shop CRM.",
                )
            ],
            ("project-1", MemoryType.CONVERSATION): [
                memory_row(
                    memory_id="memory-conversation-1",
                    memory_type=MemoryType.CONVERSATION,
                    source=MemorySource.TELEGRAM,
                    summary="User confirmed staff and owner roles.",
                )
            ],
            ("project-1", MemoryType.KNOWLEDGE): [
                memory_row(
                    memory_id="memory-knowledge-1",
                    memory_type=MemoryType.KNOWLEDGE,
                    source=MemorySource.SYSTEM,
                    summary="CRM projects need customer and order entities.",
                )
            ],
        }
    )
    service = MemoryService(repository)

    context = service.build_context(
        profile_id="profile-1",
        project_id="project-1",
        limit_per_type=2,
    )

    assert context.profile_id == "profile-1"
    assert context.project_id == "project-1"
    assert context.to_prompt_context() == {
        "user": ["User prefers Python and FastAPI."],
        "project": ["Project is a coffee shop CRM."],
        "conversation": ["User confirmed staff and owner roles."],
        "knowledge": ["CRM projects need customer and order entities."],
    }
    assert repository.load_calls == [
        ("profile-1", None, MemoryType.USER, 2),
        ("profile-1", "project-1", MemoryType.PROJECT, 2),
        ("profile-1", "project-1", MemoryType.CONVERSATION, 2),
        ("profile-1", "project-1", MemoryType.KNOWLEDGE, 2),
    ]


def test_write_fact_persists_source_confidence_profile_and_project() -> None:
    repository = FakeMemoryRepository({})
    service = MemoryService(repository)

    fact = service.write_fact(
        profile_id="profile-1",
        project_id="project-1",
        memory_type=MemoryType.PROJECT,
        source=MemorySource.GENERATION,
        content={"selected_template": "crm"},
        summary="Selected CRM template for the project.",
        confidence=0.82,
    )

    assert fact.profile_id == "profile-1"
    assert fact.project_id == "project-1"
    assert fact.memory_type == MemoryType.PROJECT
    assert fact.source == MemorySource.GENERATION
    assert fact.confidence == 0.82
    assert repository.writes == [
        {
            "id": "memory-1",
            "profile_id": "profile-1",
            "project_id": "project-1",
            "memory_type": MemoryType.PROJECT,
            "source": MemorySource.GENERATION,
            "content": {"selected_template": "crm"},
            "summary": "Selected CRM template for the project.",
            "confidence": 0.82,
        }
    ]


def test_record_conversation_summary_separates_raw_messages_from_durable_summary() -> None:
    repository = FakeMemoryRepository({})
    service = MemoryService(repository)
    messages = [
        ConversationMessage(
            direction="inbound",
            message_type="text",
            text="Build a CRM for my coffee shop.",
            telegram_message_id=10,
        ),
        ConversationMessage(
            direction="outbound",
            message_type="text",
            text="I will ask about users and exports.",
        ),
    ]

    fact = service.record_conversation_summary(
        profile_id="profile-1",
        project_id="project-1",
        messages=messages,
        confidence=0.95,
    )

    assert fact.memory_type == MemoryType.CONVERSATION
    assert fact.source == MemorySource.TELEGRAM
    assert fact.summary == (
        "User: Build a CRM for my coffee shop. | "
        "Vuls: I will ask about users and exports."
    )
    assert repository.writes[0]["content"] == {
        "messages": [message.model_dump(mode="json") for message in messages]
    }
    assert "summary" not in repository.writes[0]["content"]
    assert repository.writes[0]["confidence"] == 0.95


def test_record_project_goal_stores_goal_separately_from_chat_history() -> None:
    repository = FakeMemoryRepository({})
    service = MemoryService(repository)

    fact = service.record_project_goal(
        profile_id="profile-1",
        project_id="project-1",
        goal="Build a CRM for a small coffee shop.",
        confidence=0.9,
    )

    assert fact.memory_type == MemoryType.PROJECT
    assert fact.project_id == "project-1"
    assert repository.writes == [
        {
            "id": "memory-1",
            "profile_id": "profile-1",
            "project_id": "project-1",
            "memory_type": MemoryType.PROJECT,
            "source": MemorySource.TELEGRAM,
            "content": {
                "category": "project_goal",
                "goal": "Build a CRM for a small coffee shop.",
            },
            "summary": "Build a CRM for a small coffee shop.",
            "confidence": 0.9,
        }
    ]


def test_memory_write_transient_failure_returns_unsaved_fact_without_raising() -> None:
    repository = FailingMemoryRepository({})
    service = MemoryService(repository)

    fact = service.record_project_goal(
        profile_id="profile-1",
        project_id="project-1",
        goal="Build a CRM for a car wash.",
    )

    assert fact.id is None
    assert fact.profile_id == "profile-1"
    assert fact.project_id == "project-1"
    assert fact.memory_type == MemoryType.PROJECT
    assert fact.source == MemorySource.TELEGRAM
    assert fact.content == {
        "category": "project_goal",
        "goal": "Build a CRM for a car wash.",
    }
    assert fact.summary == "Build a CRM for a car wash."


def test_record_extracted_requirement_stores_requirement_separately_from_raw_messages() -> None:
    repository = FakeMemoryRepository({})
    service = MemoryService(repository)

    fact = service.record_extracted_requirement(
        profile_id="profile-1",
        project_id="project-1",
        requirement="Staff can manage customers and orders.",
        confidence=0.88,
    )

    assert fact.memory_type == MemoryType.PROJECT
    assert repository.writes[0]["content"] == {
        "category": "extracted_requirement",
        "requirement": "Staff can manage customers and orders.",
    }
    assert "messages" not in repository.writes[0]["content"]
    assert repository.writes[0]["confidence"] == 0.88


def test_record_user_preference_stores_preference_outside_project_memory() -> None:
    repository = FakeMemoryRepository({})
    service = MemoryService(repository)

    fact = service.record_user_preference(
        profile_id="profile-1",
        preference="User prefers Python and FastAPI.",
        confidence=0.92,
    )

    assert fact.memory_type == MemoryType.USER
    assert fact.project_id is None
    assert repository.writes[0] == {
        "id": "memory-1",
        "profile_id": "profile-1",
        "project_id": None,
        "memory_type": MemoryType.USER,
        "source": MemorySource.TELEGRAM,
        "content": {
            "category": "user_preference",
            "preference": "User prefers Python and FastAPI.",
        },
        "summary": "User prefers Python and FastAPI.",
        "confidence": 0.92,
    }


def test_get_project_memory_returns_goals_requirements_and_facts() -> None:
    repository = FakeMemoryRepository(
        {
            ("project-1", MemoryType.PROJECT): [
                memory_row(
                    memory_id="goal-1",
                    memory_type=MemoryType.PROJECT,
                    source=MemorySource.TELEGRAM,
                    summary="Build a CRM for a coffee shop.",
                    content={"category": "project_goal", "goal": "Build a CRM."},
                ),
                memory_row(
                    memory_id="requirement-1",
                    memory_type=MemoryType.PROJECT,
                    source=MemorySource.TELEGRAM,
                    summary="Staff can manage customers.",
                    content={
                        "category": "extracted_requirement",
                        "requirement": "Staff can manage customers.",
                    },
                ),
                memory_row(
                    memory_id="fact-1",
                    memory_type=MemoryType.PROJECT,
                    source=MemorySource.GENERATION,
                    summary="Selected CRM template.",
                    content={"selected_template": "crm"},
                ),
            ]
        }
    )
    service = MemoryService(repository)

    project_memory = service.get_project_memory(
        profile_id="profile-1",
        project_id="project-1",
        limit=3,
    )

    assert [item.summary for item in project_memory.goals] == ["Build a CRM for a coffee shop."]
    assert [item.summary for item in project_memory.requirements] == [
        "Staff can manage customers."
    ]
    assert [item.summary for item in project_memory.facts] == ["Selected CRM template."]
    assert repository.load_calls == [
        ("profile-1", "project-1", MemoryType.PROJECT, 3),
    ]


def test_get_user_memory_returns_preferences_and_user_facts() -> None:
    repository = FakeMemoryRepository(
        {
            (None, MemoryType.USER): [
                memory_row(
                    memory_id="preference-1",
                    project_id=None,
                    memory_type=MemoryType.USER,
                    source=MemorySource.TELEGRAM,
                    summary="User prefers Python.",
                    content={"category": "user_preference", "preference": "Python"},
                ),
                memory_row(
                    memory_id="fact-1",
                    project_id=None,
                    memory_type=MemoryType.USER,
                    source=MemorySource.MANUAL,
                    summary="User is building SaaS tools.",
                    content={"domain": "saas"},
                ),
            ]
        }
    )
    service = MemoryService(repository)

    user_memory = service.get_user_memory(profile_id="profile-1", limit=2)

    assert [item.summary for item in user_memory.preferences] == ["User prefers Python."]
    assert [item.summary for item in user_memory.facts] == ["User is building SaaS tools."]
    assert repository.load_calls == [
        ("profile-1", None, MemoryType.USER, 2),
    ]


def test_get_recent_conversation_returns_project_scoped_summaries() -> None:
    repository = FakeMemoryRepository(
        {
            ("project-1", MemoryType.CONVERSATION): [
                memory_row(
                    memory_id="conversation-1",
                    memory_type=MemoryType.CONVERSATION,
                    source=MemorySource.TELEGRAM,
                    summary="User confirmed owner and staff roles.",
                    content={"category": "conversation_summary", "messages": []},
                )
            ]
        }
    )
    service = MemoryService(repository)

    conversation = service.get_recent_conversation(
        profile_id="profile-1",
        project_id="project-1",
        limit=5,
    )

    assert [item.summary for item in conversation] == [
        "User confirmed owner and staff roles."
    ]
    assert repository.load_calls == [
        ("profile-1", "project-1", MemoryType.CONVERSATION, 5),
    ]
