from types import SimpleNamespace
from typing import Any

from vuls.core.config import AppEnv, Settings
from vuls.db.client import build_supabase_client


class FakeHttpxClient:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeClientOptions:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs


class FakeSupabaseModule:
    ClientOptions = FakeClientOptions

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_client(
        self,
        supabase_url: str,
        supabase_key: str,
        options: FakeClientOptions,
    ) -> object:
        self.calls.append(
            {
                "supabase_url": supabase_url,
                "supabase_key": supabase_key,
                "options": options,
            }
        )
        return object()


def test_build_supabase_client_disables_httpx_environment_proxy_trust(monkeypatch) -> None:
    supabase_module = FakeSupabaseModule()

    def fake_import_module(module_name: str) -> Any:
        if module_name == "supabase":
            return supabase_module
        if module_name == "httpx":
            return SimpleNamespace(Client=FakeHttpxClient)
        raise AssertionError(f"Unexpected import: {module_name}")

    monkeypatch.setattr("vuls.db.client.import_module", fake_import_module)

    build_supabase_client(settings())

    options = supabase_module.calls[0]["options"]
    assert isinstance(options, FakeClientOptions)
    httpx_client = options.kwargs["httpx_client"]
    assert isinstance(httpx_client, FakeHttpxClient)
    assert httpx_client.kwargs["trust_env"] is False
    assert httpx_client.kwargs["timeout"] == 120


def settings() -> Settings:
    return Settings(
        app_env=AppEnv.LOCAL,
        app_base_url="https://vuls.example.com",
        app_secret_key="dev-secret-key",
        telegram_bot_token="123456:telegram-token",
        telegram_webhook_secret="telegram-webhook-secret",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="supabase-service-role",
        supabase_storage_bucket="vuls-artifacts",
        openai_api_key="openai-key",
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir="./var/projects",
        _env_file=None,
    )
