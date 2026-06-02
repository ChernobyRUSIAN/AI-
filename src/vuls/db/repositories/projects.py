from collections.abc import Mapping
from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, many_rows, single_row
from vuls.db.models import ProjectStatus


class ProjectRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def create_project(
        self,
        *,
        owner_profile_id: str,
        title: str,
        slug: str,
        brief: Mapping[str, Any],
    ) -> JsonObject:
        payload: JsonObject = {
            "owner_profile_id": owner_profile_id,
            "title": title,
            "slug": slug,
            "status": ProjectStatus.DRAFT.value,
            "selected_template_key": None,
            "brief": dict(brief),
        }
        return single_row(self._client.table("projects").insert(payload).execute())

    def get_project(self, project_id: str) -> JsonObject:
        return single_row(
            self._client.table("projects")
            .select("*")
            .eq("id", project_id)
            .single()
            .execute()
        )

    def list_projects_for_owner(
        self, owner_profile_id: str, *, limit: int = 10
    ) -> list[JsonObject]:
        return many_rows(
            self._client.table("projects")
            .select("*")
            .eq("owner_profile_id", owner_profile_id)
            .order("updated_at", desc=True)
            .limit(limit)
            .execute()
        )

    def update_project_status(
        self,
        *,
        project_id: str,
        status: ProjectStatus,
        error: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        payload: JsonObject = {"status": status.value}
        if error is not None:
            payload["error"] = dict(error)

        return single_row(
            self._client.table("projects")
            .update(payload)
            .eq("id", project_id)
            .execute()
        )
