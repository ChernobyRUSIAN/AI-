from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks/telegram", tags=["telegram"])


class TelegramWebhookResponse(BaseModel):
    ok: bool


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

    _: dict[str, Any] = await request.json()
    return TelegramWebhookResponse(ok=True)
