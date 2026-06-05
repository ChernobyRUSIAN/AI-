import logging
import time
from collections.abc import Mapping
from typing import Any

import httpx

from vuls.db.client import ExecuteResult, JsonObject, SupabaseClient, single_row
from vuls.db.models import ArtifactType

LOGGER = logging.getLogger(__name__)
TRANSIENT_SUPABASE_WRITE_ERRORS = (
    httpx.ReadError,
    httpx.ConnectError,
    httpx.TimeoutException,
    httpx.RemoteProtocolError,
)


class ArtifactRepositoryTransientError(RuntimeError):
    """Raised when a transient Supabase artifact write fails after retries."""


class ArtifactRepository:
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

    def create_artifact(
        self,
        *,
        project_id: str,
        artifact_type: ArtifactType,
        generation_run_id: str | None = None,
        storage_path: str | None = None,
        content: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        payload: JsonObject = {
            "project_id": project_id,
            "generation_run_id": generation_run_id,
            "artifact_type": artifact_type.value,
            "storage_path": storage_path,
            "content": dict(content) if content is not None else None,
        }
        return single_row(self._execute_artifact_insert(payload))

    def _execute_artifact_insert(self, payload: JsonObject) -> ExecuteResult:
        last_error: Exception | None = None
        for attempt in range(1, self._max_write_attempts + 1):
            try:
                return self._client.table("artifacts").insert(payload).execute()
            except TRANSIENT_SUPABASE_WRITE_ERRORS as exc:
                last_error = exc
                LOGGER.warning(
                    "Transient Supabase artifact write failure: "
                    "table=artifacts attempt=%s max_attempts=%s error_type=%s",
                    attempt,
                    self._max_write_attempts,
                    exc.__class__.__name__,
                )
                if attempt < self._max_write_attempts and self._retry_delay_seconds > 0:
                    time.sleep(self._retry_delay_seconds)

        raise ArtifactRepositoryTransientError(
            "Supabase artifacts insert failed after "
            f"{self._max_write_attempts} attempts."
        ) from last_error
