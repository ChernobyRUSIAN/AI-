from typing import Literal, Protocol

from vuls.bot.messages import (
    BotReply,
    ProjectGenerationReply,
    TelegramUserIdentity,
    callback_data,
    identity_from_callback,
    render_generation_reply,
)
from vuls.i18n import translate


class CallbackService(Protocol):
    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply: ...


def handle_callback(callback: object, service: CallbackService) -> BotReply:
    identity = identity_from_callback(callback)
    data = callback_data(callback)
    parts = data.split(":")
    if len(parts) == 3 and parts[0] == "export" and parts[1] in {"zip", "github"}:
        export = _export_mode(parts[1])
        result = service.generate_project(
            identity,
            parts[2],
            export,
        )
        return BotReply(text=render_generation_reply(result, identity.language_code))

    if len(parts) == 2 and parts[0] == "cancel":
        return BotReply(
            text=translate("bot.callback.cancelled", identity.language_code, project_id=parts[1])
        )

    if data == "action:new_project":
        return BotReply(text=translate("bot.new_project_help", identity.language_code))
    if data == "action:projects":
        return BotReply(text=translate("bot.callback.projects_hint", identity.language_code))
    if data == "action:status":
        return BotReply(text=translate("bot.callback.status_hint", identity.language_code))

    return BotReply(text=translate("bot.unknown_callback", identity.language_code))


def _export_mode(value: str) -> Literal["zip", "github"]:
    if value == "zip":
        return "zip"
    return "github"
