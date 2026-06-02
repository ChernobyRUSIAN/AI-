from typing import Any

from vuls.db.repositories.templates import TemplateRepository


class FakeResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, Any]] = []

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

    def single(self) -> "FakeQuery":
        self.calls.append(("single", None))
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


def test_list_active_templates_reads_active_catalog() -> None:
    rows = [{"key": "crm"}, {"key": "saas"}]
    client = FakeClient(rows)
    repository = TemplateRepository(client)

    result = repository.list_active_templates()

    assert result == rows
    assert client.tables == ["templates"]
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("is_active", True)),
        ("order", ("key", False)),
    ]


def test_get_latest_template_version_returns_newest_version() -> None:
    row = {"id": "version-1", "version": "1.0.0"}
    client = FakeClient([row])
    repository = TemplateRepository(client)

    result = repository.get_latest_version("template-1")

    assert result == row
    assert client.tables == ["template_versions"]
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("template_id", "template-1")),
        ("order", ("created_at", True)),
        ("limit", 1),
    ]
