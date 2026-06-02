from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, single_row


class UserRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def create_profile(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        display_name: str | None,
        language_code: str,
        preferred_stack: dict[str, Any] | None = None,
    ) -> JsonObject:
        payload: JsonObject = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "display_name": display_name,
            "language_code": language_code,
            "preferred_stack": preferred_stack or {},
        }
        return single_row(self._client.table("profiles").insert(payload).execute())

    def upsert_profile(
        self,
        *,
        telegram_user_id: int,
        telegram_username: str | None,
        display_name: str | None,
        language_code: str,
    ) -> JsonObject:
        payload: JsonObject = {
            "telegram_user_id": telegram_user_id,
            "telegram_username": telegram_username,
            "display_name": display_name,
            "language_code": language_code,
        }
        return single_row(
            self._client.table("profiles")
            .upsert(payload, on_conflict="telegram_user_id")
            .execute()
        )

    def get_by_telegram_user_id(self, telegram_user_id: int) -> JsonObject:
        return single_row(
            self._client.table("profiles")
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .single()
            .execute()
        )
