from pathlib import Path

from fastapi.testclient import TestClient

from vuls.api.app import create_api_app
from vuls.bot.messages import BotReply, message_text
from vuls.core.config import AppEnv, Settings


def test_telegram_webhook_rejects_invalid_secret() -> None:
    client = TestClient(
        create_api_app(
            settings=_settings(telegram_webhook_secret="expected-secret"),
            build_runtime=False,
        )
    )

    response = client.post("/webhooks/telegram/wrong-secret", json={"update_id": 1})

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "invalid_webhook_secret",
            "message": "Invalid Telegram webhook secret",
        }
    }


def test_telegram_webhook_dispatches_valid_message_and_sends_reply() -> None:
    dispatcher = FakeDispatcher()
    sender = FakeSender()
    app = create_api_app(
        settings=_settings(telegram_webhook_secret="expected-secret"),
        build_runtime=False,
    )
    app.state.telegram_dispatcher = dispatcher
    app.state.telegram_sender = sender
    client = TestClient(app)

    response = client.post(
        "/webhooks/telegram/expected-secret",
        json={
            "update_id": 1001,
            "message": {
                "message_id": 77,
                "text": "Create a CRM for a car wash",
                "chat": {"id": 456, "type": "private"},
                "from": {"id": 123, "language_code": "en"},
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert dispatcher.messages == ["Create a CRM for a car wash"]
    assert sender.replies == [(456, "Received: Create a CRM for a car wash")]


class FakeDispatcher:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def dispatch_message(self, message: object) -> BotReply:
        text = message_text(message)
        self.messages.append(text)
        return BotReply(text=f"Received: {text}")

    def dispatch_callback(self, callback: object) -> BotReply:
        raise AssertionError("callback should not be dispatched")


class FakeSender:
    def __init__(self) -> None:
        self.replies: list[tuple[int, str]] = []

    async def send_reply(self, *, chat_id: int, reply: BotReply) -> None:
        self.replies.append((chat_id, reply.text))


def _settings(*, telegram_webhook_secret: str = "telegram-webhook-secret") -> Settings:
    return Settings(
        app_env=AppEnv.LOCAL,
        app_base_url="https://vuls.example.com",
        app_secret_key="dev-secret-key",
        telegram_bot_token="123456:telegram-token",
        telegram_webhook_secret=telegram_webhook_secret,
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="supabase-service-role",
        supabase_storage_bucket="vuls-artifacts",
        openai_api_key="openai-key",
        openai_model="gpt-5.1",
        github_token="github-token",
        github_owner="vuls",
        project_workdir=Path("var/projects"),
    )
