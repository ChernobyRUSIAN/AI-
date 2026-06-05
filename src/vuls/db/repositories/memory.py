import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from vuls.db.client import ExecuteResult, JsonObject, SupabaseClient, many_rows, single_row
from vuls.db.models import MemorySource, MemoryType

LOGGER = logging.getLogger(__name__)
TRANSIENT_SUPABASE_WRITE_ERRORS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


class MemoryRepositoryTransientError(RuntimeError):
    """Raised when a transient Supabase memory write fails after retries."""


class MemoryRepository:
    def __init__(
        self,
        client: SupabaseClient,
        *,
        max_write_attempts: int = 3,
        retry_delay_seconds: float = 0.0,
    ) -> None:
        self._client = client
        self._max_write_attempts = max(max_write_attempts, 1)
        self._retry_delay_seconds = max(retry_delay_seconds, 0.0)

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
        return single_row(self._execute_memory_insert(payload))

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

    def _execute_memory_insert(self, payload: JsonObject) -> ExecuteResult:
        last_error: Exception | None = None
        for attempt in range(1, self._max_write_attempts + 1):
            try:
                return self._client.table("memory_items").insert(payload).execute()
            except TRANSIENT_SUPABASE_WRITE_ERRORS as exc:
                last_error = exc
                LOGGER.warning(
                    "Transient Supabase memory write failure: "
                    "table=memory_items attempt=%s max_attempts=%s error_type=%s",
                    attempt,
                    self._max_write_attempts,
                    exc.__class__.__name__,
                )
                if attempt < self._max_write_attempts and self._retry_delay_seconds > 0:
                    time.sleep(self._retry_delay_seconds)

        raise MemoryRepositoryTransientError(
            "Supabase memory_items insert failed after "
            f"{self._max_write_attempts} attempts."
        ) from last_error
