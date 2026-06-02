from typing import Any

from vuls.db.repositories.github import GitHubRepositoryMetadataRepository


class FakeResult:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, result: Any) -> None:
        self.result = result
        self.calls: list[tuple[str, Any]] = []

    def upsert(self, payload: dict[str, Any], on_conflict: str | None = None) -> "FakeQuery":
        self.calls.append(("upsert", (payload, on_conflict)))
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


def test_save_repository_metadata_upserts_github_repository_record() -> None:
    row = {"id": "repository-1", "project_id": "project-1"}
    client = FakeClient([row])
    repository = GitHubRepositoryMetadataRepository(client)

    repository.save_repository_metadata(
        project_id="project-1",
        owner="acme",
        repo_name="coffee-crm",
        html_url="https://github.com/acme/coffee-crm",
        default_branch="main",
    )

    assert client.tables == ["repositories"]
    assert client.query.calls == [
        (
            "upsert",
            (
                {
                    "project_id": "project-1",
                    "provider": "github",
                    "owner": "acme",
                    "repo_name": "coffee-crm",
                    "html_url": "https://github.com/acme/coffee-crm",
                    "default_branch": "main",
                },
                "project_id",
            ),
        )
    ]
