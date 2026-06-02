from vuls.db.client import SupabaseClient, single_row


class GitHubRepositoryMetadataRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def save_repository_metadata(
        self,
        *,
        project_id: str,
        owner: str,
        repo_name: str,
        html_url: str,
        default_branch: str,
    ) -> None:
        payload = {
            "project_id": project_id,
            "provider": "github",
            "owner": owner,
            "repo_name": repo_name,
            "html_url": html_url,
            "default_branch": default_branch,
        }
        single_row(
            self._client.table("repositories")
            .upsert(payload, on_conflict="project_id")
            .execute()
        )
