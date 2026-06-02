from dataclasses import dataclass

from vuls.bot.dispatcher import TelegramDispatcher, TelegramFlowService, create_dispatcher


@dataclass(frozen=True)
class TelegramBotApp:
    token: str
    dispatcher: TelegramDispatcher


def create_bot_app(*, token: str, service: TelegramFlowService) -> TelegramBotApp:
    return TelegramBotApp(token=token, dispatcher=create_dispatcher(service))
