from vuls.db.client import JsonObject, SupabaseClient, many_rows, single_row


class TemplateRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def list_active_templates(self) -> list[JsonObject]:
        return many_rows(
            self._client.table("templates")
            .select("*")
            .eq("is_active", True)
            .order("key")
            .execute()
        )

    def get_active_template(self, key: str) -> JsonObject:
        return single_row(
            self._client.table("templates")
            .select("*")
            .eq("key", key)
            .eq("is_active", True)
            .single()
            .execute()
        )

    def get_latest_version(self, template_id: str) -> JsonObject | None:
        rows = many_rows(
            self._client.table("template_versions")
            .select("*")
            .eq("template_id", template_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return rows[0] if rows else None
