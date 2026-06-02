from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast


@dataclass(frozen=True)
class TelegramUser:
    id: int
    username: str | None = None
    full_name: str | None = None
    language_code: str | None = None


@dataclass(frozen=True)
class TelegramChat:
    id: int
    type: str = "private"


@dataclass(frozen=True)
class TelegramMessage:
    message_id: int
    text: str
    from_user: TelegramUser
    chat: TelegramChat


@dataclass(frozen=True)
class TelegramCallbackQuery:
    id: str
    data: str
    from_user: TelegramUser
    message: TelegramMessage


@dataclass(frozen=True)
class AdaptedTelegramUpdate:
    update_id: int
    kind: Literal["message", "callback"]
    message: TelegramMessage | None = None
    callback: TelegramCallbackQuery | None = None


class TelegramUpdateAdapter:
    def adapt(self, update: Mapping[str, Any]) -> AdaptedTelegramUpdate | None:
        message_payload = _mapping_field(update, "message")
        if message_payload:
            message = _message_from_payload(message_payload)
            return AdaptedTelegramUpdate(
                update_id=_int_field(update, "update_id"),
                kind="message",
                message=message,
            )

        callback_payload = _mapping_field(update, "callback_query")
        if callback_payload:
            callback = TelegramCallbackQuery(
                id=_str_field(callback_payload, "id"),
                data=_str_field(callback_payload, "data"),
                from_user=_user_from_payload(_mapping_field(callback_payload, "from")),
                message=_message_from_payload(_mapping_field(callback_payload, "message")),
            )
            return AdaptedTelegramUpdate(
                update_id=_int_field(update, "update_id"),
                kind="callback",
                callback=callback,
            )

        return None


def _message_from_payload(payload: Mapping[str, Any]) -> TelegramMessage:
    return TelegramMessage(
        message_id=_int_field(payload, "message_id"),
        text=_str_field(payload, "text"),
        from_user=_user_from_payload(_mapping_field(payload, "from")),
        chat=_chat_from_payload(_mapping_field(payload, "chat")),
    )


def _user_from_payload(payload: Mapping[str, Any]) -> TelegramUser:
    first_name = _optional_str_field(payload, "first_name")
    last_name = _optional_str_field(payload, "last_name")
    full_name = _full_name(first_name, last_name)
    return TelegramUser(
        id=_int_field(payload, "id"),
        username=_optional_str_field(payload, "username"),
        full_name=full_name,
        language_code=_optional_str_field(payload, "language_code"),
    )


def _chat_from_payload(payload: Mapping[str, Any]) -> TelegramChat:
    return TelegramChat(
        id=_int_field(payload, "id"),
        type=_str_field(payload, "type", default="private"),
    )


def _mapping_field(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}


def _int_field(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    return value if isinstance(value, int) else 0


def _str_field(payload: Mapping[str, Any], key: str, *, default: str = "") -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else default


def _optional_str_field(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _full_name(first_name: str | None, last_name: str | None) -> str | None:
    parts = [part for part in (first_name, last_name) if part]
    return " ".join(parts) if parts else None
