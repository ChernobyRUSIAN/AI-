from dataclasses import dataclass

from vuls.bot.handlers.start import handle_start
from vuls.bot.messages import TelegramUserIdentity


@dataclass
class FakeUser:
    id: int
    username: str | None = None
    full_name: str | None = None
    language_code: str | None = None


@dataclass
class FakeChat:
    id: int


@dataclass
class FakeMessage:
    text: str
    from_user: FakeUser
    chat: FakeChat


class FakeTelegramService:
    def __init__(self) -> None:
        self.registered: list[TelegramUserIdentity] = []

    def register_user(self, identity: TelegramUserIdentity) -> None:
        self.registered.append(identity)


def test_start_registers_user_and_returns_main_actions() -> None:
    service = FakeTelegramService()
    message = FakeMessage(
        text="/start",
        from_user=FakeUser(
            id=123,
            username="artel",
            full_name="Artel User",
            language_code="en",
        ),
        chat=FakeChat(id=456),
    )

    reply = handle_start(message, service)

    assert service.registered == [
        TelegramUserIdentity(
            telegram_user_id=123,
            telegram_chat_id=456,
            username="artel",
            display_name="Artel User",
            language_code="en",
        )
    ]
    assert "Vuls" in reply.text
    assert reply.keyboard is not None
    assert [button.callback_data for row in reply.keyboard.rows for button in row] == [
        "action:new_project",
        "action:projects",
        "action:status",
    ]
