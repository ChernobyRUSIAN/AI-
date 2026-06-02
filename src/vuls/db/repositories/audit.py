from collections.abc import Mapping
from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, single_row


class AuditRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def record_event(
        self,
        *,
        event_type: str,
        profile_id: str | None = None,
        project_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        event: JsonObject = {
            "profile_id": profile_id,
            "project_id": project_id,
            "event_type": event_type,
            "payload": dict(payload) if payload is not None else {},
        }
        return single_row(self._client.table("audit_events").insert(event).execute())
