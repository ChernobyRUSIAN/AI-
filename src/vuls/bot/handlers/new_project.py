from typing import Protocol

from vuls.bot.keyboards import export_choice_keyboard
from vuls.bot.messages import (
    BotReply,
    ProjectIntakeResult,
    TelegramUserIdentity,
    command_payload,
    identity_from_message,
    message_text,
    render_intake_result,
)
from vuls.i18n import translate


class NewProjectService(Protocol):
    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult: ...


def handle_new_project(message: object, service: NewProjectService) -> BotReply:
    identity = identity_from_message(message)
    idea = command_payload(message_text(message), "/new")
    if not idea:
        return BotReply(text=translate("bot.new_project_help", identity.language_code))

    result = service.start_new_project(identity, idea)
    return BotReply(
        text=render_intake_result(result, identity.language_code),
        keyboard=export_choice_keyboard(result.project_id, identity.language_code),
    )
