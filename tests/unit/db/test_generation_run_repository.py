from typing import Any

from vuls.db.repositories.generation_runs import GenerationRunRepository
from vuls.workflows.schemas import GenerationRunCreate, GenerationRunStatus


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

    def update(self, payload: dict[str, Any]) -> "FakeQuery":
        self.calls.append(("update", payload))
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


def test_create_generation_run_inserts_queued_run() -> None:
    row = {"id": "run-1", "status": "queued"}
    client = FakeClient([row])
    repository = GenerationRunRepository(client)

    result = repository.create_run(
        GenerationRunCreate(
            project_id="project-1",
            template_version_id="template-version-1",
            provider="openrouter",
            model="openai/gpt-4o",
            input_summary="Generate CRM manifest.",
            usage={"input_tokens": 10},
        )
    )

    assert result == row
    assert client.tables == ["generation_runs"]
    assert client.query.calls == [
        (
            "insert",
            {
                "project_id": "project-1",
                "template_version_id": "template-version-1",
                "status": "queued",
                "provider": "openrouter",
                "model": "openai/gpt-4o",
                "input_summary": "Generate CRM manifest.",
                "usage": {"input_tokens": 10},
            },
        )
    ]


def test_mark_generation_run_running_updates_status() -> None:
    row = {"id": "run-1", "status": "running"}
    client = FakeClient([row])
    repository = GenerationRunRepository(client)

    result = repository.mark_running("run-1")

    assert result == row
    assert client.tables == ["generation_runs"]
    assert client.query.calls == [
        ("update", {"status": "running"}),
        ("eq", ("id", "run-1")),
    ]


def test_mark_generation_run_completed_records_output_usage_and_completion_time() -> None:
    row = {"id": "run-1", "status": "completed"}
    client = FakeClient([row])
    repository = GenerationRunRepository(client, clock=lambda: "2026-06-04T12:00:00Z")

    result = repository.mark_completed(
        "run-1",
        output_manifest={"project_name": "crm"},
        usage={"input_tokens": 10, "output_tokens": 20},
    )

    assert result == row
    assert client.query.calls == [
        (
            "update",
            {
                "status": "completed",
                "output_manifest": {"project_name": "crm"},
                "usage": {"input_tokens": 10, "output_tokens": 20},
                "completed_at": "2026-06-04T12:00:00Z",
            },
        ),
        ("eq", ("id", "run-1")),
    ]


def test_mark_generation_run_failed_records_structured_error() -> None:
    row = {"id": "run-1", "status": "failed"}
    client = FakeClient([row])
    repository = GenerationRunRepository(client, clock=lambda: "2026-06-04T12:00:00Z")

    result = repository.mark_failed(
        "run-1",
        error={"code": "llm_provider_unavailable", "message": "No available providers."},
        usage={"input_tokens": 10},
    )

    assert result == row
    assert client.query.calls == [
        (
            "update",
            {
                "status": "failed",
                "error": {
                    "code": "llm_provider_unavailable",
                    "message": "No available providers.",
                },
                "usage": {"input_tokens": 10},
                "completed_at": "2026-06-04T12:00:00Z",
            },
        ),
        ("eq", ("id", "run-1")),
    ]


def test_mark_generation_run_cancelled_records_terminal_status() -> None:
    row = {"id": "run-1", "status": "cancelled"}
    client = FakeClient([row])
    repository = GenerationRunRepository(client, clock=lambda: "2026-06-04T12:00:00Z")

    result = repository.mark_cancelled(
        "run-1",
        error={"code": "user_cancelled", "message": "Cancelled by user."},
    )

    assert result == row
    assert client.query.calls == [
        (
            "update",
            {
                "status": "cancelled",
                "error": {"code": "user_cancelled", "message": "Cancelled by user."},
                "completed_at": "2026-06-04T12:00:00Z",
            },
        ),
        ("eq", ("id", "run-1")),
    ]


def test_get_latest_generation_run_for_project_returns_most_recent_row() -> None:
    row = {"id": "run-2", "status": GenerationRunStatus.COMPLETED.value}
    client = FakeClient([row])
    repository = GenerationRunRepository(client)

    result = repository.get_latest_for_project("project-1")

    assert result == row
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("project_id", "project-1")),
        ("order", ("created_at", True)),
        ("limit", 1),
    ]


def test_get_latest_generation_run_for_project_returns_none_when_empty() -> None:
    client = FakeClient([])
    repository = GenerationRunRepository(client)

    assert repository.get_latest_for_project("project-1") is None
