from typing import Protocol

from vuls.bot.messages import (
    BotReply,
    ProjectStatusView,
    TelegramUserIdentity,
    identity_from_message,
    render_project_status,
)


class StatusService(Protocol):
    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None: ...


def handle_status(message: object, service: StatusService) -> BotReply:
    project = service.get_active_project(identity_from_message(message))
    return BotReply(text=render_project_status(project))
