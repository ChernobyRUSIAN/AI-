from collections.abc import Mapping, Sequence
from importlib import import_module
from typing import Any, Protocol, Self, cast

from vuls.core.config import Settings


class SupabaseDataError(RuntimeError):
    """Raised when a Supabase response does not match repository expectations."""


class ExecuteResult(Protocol):
    data: Any


class QueryBuilder(Protocol):
    def insert(self, payload: Mapping[str, Any]) -> Self: ...

    def upsert(self, payload: Mapping[str, Any], on_conflict: str | None = None) -> Self: ...

    def update(self, payload: Mapping[str, Any]) -> Self: ...

    def select(self, columns: str = "*") -> Self: ...

    def eq(self, column: str, value: Any) -> Self: ...

    def order(self, column: str, *, desc: bool = False) -> Self: ...

    def limit(self, count: int) -> Self: ...

    def single(self) -> Self: ...

    def execute(self) -> ExecuteResult: ...


class SupabaseClient(Protocol):
    def table(self, table_name: str) -> QueryBuilder: ...


JsonObject = dict[str, Any]
SUPABASE_HTTP_TIMEOUT_SECONDS = 120


def build_supabase_client(settings: Settings) -> SupabaseClient:
    try:
        supabase_module = import_module("supabase")
    except ImportError as exc:
        raise RuntimeError("Install the Supabase Python client before running Vuls.") from exc

    try:
        httpx_module = import_module("httpx")
    except ImportError as exc:
        raise RuntimeError("Install HTTPX before running Vuls.") from exc

    create_client = cast(Any, supabase_module).create_client
    client_options = cast(Any, supabase_module).ClientOptions
    httpx_client = cast(Any, httpx_module).Client(
        timeout=SUPABASE_HTTP_TIMEOUT_SECONDS,
        trust_env=False,
    )
    return cast(
        SupabaseClient,
        create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
            client_options(
                postgrest_client_timeout=SUPABASE_HTTP_TIMEOUT_SECONDS,
                httpx_client=httpx_client,
            ),
        ),
    )


def single_row(result: ExecuteResult) -> JsonObject:
    data = result.data
    if isinstance(data, list):
        if not data:
            raise SupabaseDataError("Expected one row, received none.")
        data = data[0]

    if not isinstance(data, dict):
        raise SupabaseDataError("Expected row data to be a mapping.")

    return dict(cast(Mapping[str, Any], data))


def many_rows(result: ExecuteResult) -> list[JsonObject]:
    data = result.data
    if not isinstance(data, Sequence) or isinstance(data, (str, bytes)):
        raise SupabaseDataError("Expected row data to be a sequence.")

    rows: list[JsonObject] = []
    for row in data:
        if not isinstance(row, dict):
            raise SupabaseDataError("Expected every row to be a mapping.")
        rows.append(dict(cast(Mapping[str, Any], row)))

    return rows
