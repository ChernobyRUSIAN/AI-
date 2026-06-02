from typing import Any, Protocol, cast

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from vuls.bot.messages import BotReply
from vuls.bot.update_adapter import AdaptedTelegramUpdate, TelegramUpdateAdapter

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])


class TelegramWebhookResponse(BaseModel):
    ok: bool


class TelegramDispatcherProtocol(Protocol):
    def dispatch_message(self, message: object) -> BotReply: ...

    def dispatch_callback(self, callback: object) -> BotReply: ...


class TelegramSenderProtocol(Protocol):
    async def send_reply(self, *, chat_id: int, reply: BotReply) -> object: ...


@router.post("/{secret}", response_model=TelegramWebhookResponse)
async def receive_telegram_update(
    secret: str,
    request: Request,
) -> TelegramWebhookResponse | JSONResponse:
    expected_secret = str(request.app.state.telegram_webhook_secret)
    if secret != expected_secret:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": {
                    "code": "invalid_webhook_secret",
                    "message": "Invalid Telegram webhook secret",
                }
            },
        )

    payload: dict[str, Any] = await request.json()
    adapted_update = TelegramUpdateAdapter().adapt(payload)
    if adapted_update is not None:
        await _dispatch_update(request, adapted_update)

    return TelegramWebhookResponse(ok=True)


async def _dispatch_update(request: Request, update: AdaptedTelegramUpdate) -> None:
    dispatcher = _state_dependency(request, "telegram_dispatcher")
    sender = _state_dependency(request, "telegram_sender")
    if dispatcher is None or sender is None:
        return

    typed_dispatcher = cast(TelegramDispatcherProtocol, dispatcher)
    typed_sender = cast(TelegramSenderProtocol, sender)
    if update.kind == "message" and update.message is not None:
        reply = typed_dispatcher.dispatch_message(update.message)
        await typed_sender.send_reply(chat_id=update.message.chat.id, reply=reply)
        return

    if update.kind == "callback" and update.callback is not None:
        reply = typed_dispatcher.dispatch_callback(update.callback)
        await typed_sender.send_reply(chat_id=update.callback.message.chat.id, reply=reply)


def _state_dependency(request: Request, name: str) -> object | None:
    direct_value = cast(object | None, getattr(request.app.state, name, None))
    if direct_value is not None:
        return direct_value

    runtime = cast(object | None, getattr(request.app.state, "runtime", None))
    if runtime is None:
        return None
    return cast(object | None, getattr(runtime, name, None))
