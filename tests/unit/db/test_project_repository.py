from typing import Any

from vuls.db.repositories.projects import ProjectRepository


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


def test_create_project_inserts_draft_project() -> None:
    row = {"id": "project-1", "status": "draft"}
    client = FakeClient([row])
    repository = ProjectRepository(client)

    result = repository.create_project(
        owner_profile_id="profile-1",
        title="Coffee CRM",
        slug="coffee-crm",
        brief={"idea": "CRM for a coffee shop"},
    )

    assert result == row
    assert client.tables == ["projects"]
    assert client.query.calls[0] == (
        "insert",
        {
            "owner_profile_id": "profile-1",
            "title": "Coffee CRM",
            "slug": "coffee-crm",
            "status": "draft",
            "selected_template_key": None,
            "brief": {"idea": "CRM for a coffee shop"},
        },
    )


def test_get_project_selects_single_project_by_id() -> None:
    row = {"id": "project-1", "title": "Coffee CRM"}
    client = FakeClient(row)
    repository = ProjectRepository(client)

    result = repository.get_project("project-1")

    assert result == row
    assert client.tables == ["projects"]
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("id", "project-1")),
        ("single", None),
    ]


def test_list_projects_for_owner_orders_by_recent_update() -> None:
    rows = [{"id": "project-1"}, {"id": "project-2"}]
    client = FakeClient(rows)
    repository = ProjectRepository(client)

    result = repository.list_projects_for_owner("profile-1", limit=2)

    assert result == rows
    assert client.query.calls == [
        ("select", "*"),
        ("eq", ("owner_profile_id", "profile-1")),
        ("order", ("updated_at", True)),
        ("limit", 2),
    ]
