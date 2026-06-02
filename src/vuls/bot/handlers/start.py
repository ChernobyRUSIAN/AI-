from typing import Protocol

from vuls.bot.keyboards import main_actions_keyboard
from vuls.bot.messages import BotReply, TelegramUserIdentity, identity_from_message
from vuls.i18n import translate


class StartService(Protocol):
    def register_user(self, identity: TelegramUserIdentity) -> None: ...


def handle_start(message: object, service: StartService) -> BotReply:
    identity = identity_from_message(message)
    service.register_user(identity)
    return BotReply(
        text=translate("bot.welcome", identity.language_code),
        keyboard=main_actions_keyboard(identity.language_code),
    )
