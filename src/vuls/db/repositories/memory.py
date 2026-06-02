from collections.abc import Mapping
from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, many_rows, single_row
from vuls.db.models import MemorySource, MemoryType


class MemoryRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def write_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None,
        memory_type: MemoryType,
        source: MemorySource,
        content: Mapping[str, Any],
        summary: str,
        confidence: float = 1.0,
    ) -> JsonObject:
        payload: JsonObject = {
            "profile_id": profile_id,
            "project_id": project_id,
            "memory_type": memory_type.value,
            "source": source.value,
            "content": dict(content),
            "summary": summary,
            "confidence": confidence,
        }
        return single_row(self._client.table("memory_items").insert(payload).execute())

    def load_memory(
        self,
        *,
        profile_id: str,
        project_id: str | None = None,
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[JsonObject]:
        query = self._client.table("memory_items").select("*").eq("profile_id", profile_id)

        if project_id is not None:
            query = query.eq("project_id", project_id)

        if memory_type is not None:
            query = query.eq("memory_type", memory_type.value)

        return many_rows(query.order("updated_at", desc=True).limit(limit).execute())
