from vuls.bot.messages import (
    callback_data,
    identity_from_callback,
    identity_from_message,
    message_text,
)
from vuls.bot.update_adapter import TelegramUpdateAdapter


def test_message_update_converts_to_dispatcher_compatible_message() -> None:
    adapted = TelegramUpdateAdapter().adapt(
        {
            "update_id": 1001,
            "message": {
                "message_id": 77,
                "text": "Create a CRM for a car wash",
                "chat": {"id": 456, "type": "private"},
                "from": {
                    "id": 123,
                    "username": "artel",
                    "first_name": "Artel",
                    "last_name": "User",
                    "language_code": "en",
                },
            },
        }
    )

    assert adapted is not None
    assert adapted.kind == "message"
    assert adapted.message is not None
    assert adapted.callback is None
    assert message_text(adapted.message) == "Create a CRM for a car wash"
    assert adapted.message.chat.type == "private"
    assert identity_from_message(adapted.message).telegram_user_id == 123
    assert identity_from_message(adapted.message).telegram_chat_id == 456
    assert identity_from_message(adapted.message).display_name == "Artel User"


def test_callback_update_converts_to_dispatcher_compatible_callback() -> None:
    adapted = TelegramUpdateAdapter().adapt(
        {
            "update_id": 1002,
            "callback_query": {
                "id": "callback-1",
                "data": "export:github:project-1",
                "from": {"id": 123, "username": "artel", "language_code": "en"},
                "message": {
                    "message_id": 77,
                    "chat": {"id": 456, "type": "private"},
                    "text": "Choose export",
                },
            },
        }
    )

    assert adapted is not None
    assert adapted.kind == "callback"
    assert adapted.callback is not None
    assert adapted.message is None
    assert callback_data(adapted.callback) == "export:github:project-1"
    assert identity_from_callback(adapted.callback).telegram_user_id == 123
    assert identity_from_callback(adapted.callback).telegram_chat_id == 456


def test_unsupported_update_returns_none() -> None:
    adapted = TelegramUpdateAdapter().adapt({"update_id": 1003, "edited_message": {}})

    assert adapted is None
