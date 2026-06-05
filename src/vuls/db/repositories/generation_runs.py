from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from vuls.db.client import JsonObject, SupabaseClient, many_rows, single_row
from vuls.workflows.schemas import GenerationRunCreate, GenerationRunStatus

Clock = Callable[[], str]


class GenerationRunRepository:
    def __init__(
        self,
        client: SupabaseClient,
        *,
        clock: Clock | None = None,
    ) -> None:
        self._client = client
        self._clock = clock or _utc_now_iso

    def create_run(self, request: GenerationRunCreate) -> JsonObject:
        payload: JsonObject = {
            "project_id": request.project_id,
            "template_version_id": request.template_version_id,
            "status": request.status.value,
            "provider": request.provider,
            "model": request.model,
            "input_summary": request.input_summary,
            "usage": dict(request.usage),
        }
        return single_row(self._client.table("generation_runs").insert(payload).execute())

    def mark_running(self, generation_run_id: str) -> JsonObject:
        return self._update_run(
            generation_run_id,
            {"status": GenerationRunStatus.RUNNING.value},
        )

    def mark_completed(
        self,
        generation_run_id: str,
        *,
        output_manifest: Mapping[str, Any],
        usage: Mapping[str, Any],
    ) -> JsonObject:
        return self._update_run(
            generation_run_id,
            {
                "status": GenerationRunStatus.COMPLETED.value,
                "output_manifest": dict(output_manifest),
                "usage": dict(usage),
                "completed_at": self._clock(),
            },
        )

    def mark_failed(
        self,
        generation_run_id: str,
        *,
        error: Mapping[str, Any],
        usage: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        payload: JsonObject = {
            "status": GenerationRunStatus.FAILED.value,
            "error": dict(error),
            "completed_at": self._clock(),
        }
        if usage is not None:
            payload["usage"] = dict(usage)
        return self._update_run(generation_run_id, payload)

    def mark_cancelled(
        self,
        generation_run_id: str,
        *,
        error: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        payload: JsonObject = {
            "status": GenerationRunStatus.CANCELLED.value,
            "completed_at": self._clock(),
        }
        if error is not None:
            payload["error"] = dict(error)
        return self._update_run(generation_run_id, payload)

    def get_latest_for_project(self, project_id: str) -> JsonObject | None:
        rows = many_rows(
            self._client.table("generation_runs")
            .select("*")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return rows[0] if rows else None

    def _update_run(
        self,
        generation_run_id: str,
        payload: Mapping[str, Any],
    ) -> JsonObject:
        return single_row(
            self._client.table("generation_runs")
            .update(dict(payload))
            .eq("id", generation_run_id)
            .execute()
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
