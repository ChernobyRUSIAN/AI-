from typing import Protocol

from vuls.bot.messages import (
    BotReply,
    ProjectSummary,
    TelegramUserIdentity,
    identity_from_message,
    render_recent_projects,
)


class ProjectsService(Protocol):
    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]: ...


def handle_projects(message: object, service: ProjectsService) -> BotReply:
    identity = identity_from_message(message)
    projects = service.list_recent_projects(identity)
    return BotReply(text=render_recent_projects(projects, identity.language_code))
