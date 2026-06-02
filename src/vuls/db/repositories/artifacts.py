from collections.abc import Mapping
from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, single_row
from vuls.db.models import ArtifactType


class ArtifactRepository:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

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
        return single_row(self._client.table("artifacts").insert(payload).execute())
