from typing import Any

import httpx
import pytest

from vuls.db.models import ArtifactType
from vuls.db.repositories.artifacts import (
    ArtifactRepository,
    ArtifactRepositoryTransientError,
)


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


def test_create_artifact_inserts_artifact_row() -> None:
    row = {"id": "artifact-1", "artifact_type": "zip"}
    client = FakeClient([row])
    repository = ArtifactRepository(client)

    result = repository.create_artifact(
        project_id="project-1",
        artifact_type=ArtifactType.ZIP,
        generation_run_id="run-1",
        storage_path="artifacts/project-1.zip",
        content={"size_bytes": 1234},
    )

    assert result == row
    assert client.tables == ["artifacts"]
    assert client.query.calls == [
        (
            "insert",
            {
                "project_id": "project-1",
                "generation_run_id": "run-1",
                "artifact_type": "zip",
                "storage_path": "artifacts/project-1.zip",
                "content": {"size_bytes": 1234},
            },
        )
    ]


@pytest.mark.parametrize(
    "transient_error",
    [
        httpx.ReadError("connection closed by remote host"),
        httpx.ConnectError("connection failed"),
        httpx.TimeoutException("request timed out"),
        httpx.RemoteProtocolError("remote protocol closed"),
    ],
)
def test_create_artifact_retries_transient_supabase_transport_errors(
    transient_error: Exception,
) -> None:
    row = {"id": "artifact-1", "artifact_type": "manifest"}
    client = RetryingFakeClient([transient_error, [row]])
    repository = ArtifactRepository(client, max_write_attempts=2)

    result = repository.create_artifact(
        project_id="project-1",
        artifact_type=ArtifactType.MANIFEST,
        content={"project_name": "car-wash-crm"},
    )

    assert result == row
    assert client.execute_count == 2
    assert client.tables == ["artifacts", "artifacts"]


def test_create_artifact_raises_typed_transient_error_after_retry_budget() -> None:
    client = RetryingFakeClient(
        [
            httpx.ReadError("connection closed by remote host"),
            httpx.ReadError("connection closed by remote host"),
        ]
    )
    repository = ArtifactRepository(client, max_write_attempts=2)

    with pytest.raises(ArtifactRepositoryTransientError) as exc_info:
        repository.create_artifact(
            project_id="project-1",
            artifact_type=ArtifactType.ZIP,
            storage_path="artifacts/project-1.zip",
        )

    assert "artifacts" in str(exc_info.value)
    assert "2 attempts" in str(exc_info.value)
    assert client.execute_count == 2
