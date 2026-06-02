from typing import Literal, Protocol

from vuls.bot.messages import (
    UNKNOWN_CALLBACK,
    BotReply,
    ProjectGenerationReply,
    TelegramUserIdentity,
    callback_data,
    identity_from_callback,
    render_generation_reply,
)


class CallbackService(Protocol):
    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply: ...


def handle_callback(callback: object, service: CallbackService) -> BotReply:
    data = callback_data(callback)
    parts = data.split(":")
    if len(parts) == 3 and parts[0] == "export" and parts[1] in {"zip", "github"}:
        export = _export_mode(parts[1])
        result = service.generate_project(
            identity_from_callback(callback),
            parts[2],
            export,
        )
        return BotReply(text=render_generation_reply(result))

    if len(parts) == 2 and parts[0] == "cancel":
        return BotReply(text=f"Project {parts[1]} cancelled.")

    if data == "action:new_project":
        return BotReply(text="Send /new followed by your product idea.")
    if data == "action:projects":
        return BotReply(text="Use /projects to see recent projects.")
    if data == "action:status":
        return BotReply(text="Use /status to see the active project.")

    return BotReply(text=UNKNOWN_CALLBACK)


def _export_mode(value: str) -> Literal["zip", "github"]:
    if value == "zip":
        return "zip"
    return "github"
