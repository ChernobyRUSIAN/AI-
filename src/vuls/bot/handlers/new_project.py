from typing import Protocol

from vuls.bot.keyboards import export_choice_keyboard
from vuls.bot.messages import (
    NEW_PROJECT_HELP,
    BotReply,
    ProjectIntakeResult,
    TelegramUserIdentity,
    command_payload,
    identity_from_message,
    message_text,
    render_intake_result,
)


class NewProjectService(Protocol):
    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult: ...


def handle_new_project(message: object, service: NewProjectService) -> BotReply:
    idea = command_payload(message_text(message), "/new")
    if not idea:
        return BotReply(text=NEW_PROJECT_HELP)

    result = service.start_new_project(identity_from_message(message), idea)
    return BotReply(
        text=render_intake_result(result),
        keyboard=export_choice_keyboard(result.project_id),
    )
