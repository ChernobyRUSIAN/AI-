from typing import Any

import httpx
import pytest

from vuls.db.models import MemorySource, MemoryType
from vuls.db.repositories.memory import MemoryRepository, MemoryRepositoryTransientError


class FakeResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, Any]] = []

    def insert(self, payload: dict[str, Any]) -> "FakeQuery":
        self.calls.append(("insert", payload))
        return self

    def select(self, columns: str) -> "FakeQuery":
        self.calls.append(("select", columns))
        return self

    def eq(self, column: str, value: Any) -> "FakeQuery":
        self.calls.append(("eq", (column, value)))
        return self

    def order(self, column: str, desc: bool = False) -> "FakeQuery":
        self.calls.append(("order", (column, desc)))
        return self

    def limit(self, count: int) -> "FakeQuery":
        self.calls.append(("limit", count))
        return self

    def execute(self) -> FakeResult:
        return FakeResult(self.result)


class FakeClient:
    def __init__(self, result: Any) -> None:
        self.query = FakeQuery(result)
        self.tables: list[str] = []

    def table(self, table_name: str) -> FakeQuery:
        self.tables.append(table_name)
        return self.query


class RetryingFakeQuery:
    def __init__(self, client: "RetryingFakeClient") -> None:
        self._client = client
        self.calls: list[tuple[str, Any]] = []

    def insert(self, payload: dict[str, Any]) -> "RetryingFakeQuery":
        self.calls.append(("insert", payload))
        return self

    def execute(self) -> FakeResult:
        self._client.execute_count += 1
        result = self._client.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return FakeResult(result)


class RetryingFakeClient:
    def __init__(self, results: list[Any | Exception]) -> None:
        self.results = results
        self.tables: list[str] = []
        self.queries: list[RetryingFakeQuery] = []
        self.execute_count = 0

    def table(self, table_name: str) -> RetryingFakeQuery:
        self.tables.append(table_name)
        query = RetryingFakeQuery(self)
        self.queries.append(query)
        return query


def test_write_memory_inserts_durable_memory_item() -> None:
    row = {"id": "memory-1", "summary": "User prefers Python"}
    client = FakeClient([row])
    repository = MemoryRepository(client)

    result = repository.write_memory(
        profile_id="profile-1",
        project_id=None,
        memory_type=MemoryType.USER,
        source=MemorySource.TELEGRAM,
        content={"preferred_stack": "Python"},
        summary="User prefers Python",
        confidence=0.9,
    )

    assert result == row
    assert client.tables == ["memory_items"]
    assert client.query.calls[0] == (
        "insert",
        {
            "profile_id": "profile-1",
            "project_id": None,
            "memory_type": "user",
            "source": "telegram",
            "content": {"preferred_stack": "Python"},
            "summary": "User prefers Python",
            "confidence": 0.9,
        },
    )


@pytest.mark.parametrize(
    "transient_error",
    [
        httpx.ReadError("connection closed by remote host"),
        httpx.ConnectError("connection failed"),
    ],
)
def test_write_memory_retries_transient_supabase_transport_errors(
    transient_error: Exception,
) -> None:
    row = {"id": "memory-1", "summary": "Project goal"}
    client = RetryingFakeClient([transient_error, [row]])
    repository = MemoryRepository(client, max_write_attempts=2)

    result = repository.write_memory(
        profile_id="profile-1",
        project_id="project-1",
        memory_type=MemoryType.PROJECT,
        source=MemorySource.TELEGRAM,
        content={"goal": "Create a CRM"},
        summary="Create a CRM",
    )

    assert result == row
    assert client.execute_count == 2
    assert client.tables == ["memory_items", "memory_items"]


def test_write_memory_raises_typed_transient_error_after_retry_budget() -> None:
    client = RetryingFakeClient(
        [
            httpx.ReadError("connection closed by remote host"),
            httpx.ReadError("connection closed by remote host"),
        ]
    )
    repository = MemoryRepository(client, max_write_attempts=2)

    with pytest.raises(MemoryRepositoryTransientError) as exc_info:
        repository.write_memory(
            profile_id="profile-1",
            project_id="project-1",
            memory_type=MemoryType.PROJECT,
            source=MemorySource.TELEGRAM,
            content={"goal": "Create a CRM"},
            summary="Create a CRM",
        )

    assert "memory_items" in str(exc_info.value)
    assert "2 attempts" in str(exc_info.value)
    assert client.execute_count == 2


def test_load_memory_filters_by_profile_project_and_type() -> None:
    rows = [{"id": "memory-1"}, {"id": "memory-2"}]
    client = FakeClient(rows)
    repository = MemoryRepository(client)

    result = repository.load_memory(
        profile_id="profile-1",
        project_id="project-1",
        memory_type=MemoryType.PROJECT,
        limit=2,
    )

    assert result == rows
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("profile_id", "profile-1")),
        ("eq", ("project_id", "project-1")),
        ("eq", ("memory_type", "project")),
        ("order", ("updated_at", True)),
        ("limit", 2),
    ]
