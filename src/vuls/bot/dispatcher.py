from typing import Literal, Protocol

from vuls.bot.handlers.callbacks import handle_callback
from vuls.bot.handlers.new_project import handle_new_project
from vuls.bot.handlers.projects import handle_projects
from vuls.bot.handlers.start import handle_start
from vuls.bot.handlers.status import handle_status
from vuls.bot.intent import ProjectIntentDetector
from vuls.bot.keyboards import export_choice_keyboard
from vuls.bot.messages import (
    BotReply,
    ProjectGenerationReply,
    ProjectIntakeResult,
    ProjectStatusView,
    ProjectSummary,
    TelegramUserIdentity,
    identity_from_message,
    message_text,
    render_intake_result,
)
from vuls.i18n import translate


class TelegramFlowService(Protocol):
    """Business boundary consumed by Telegram handlers."""

    def register_user(self, identity: TelegramUserIdentity) -> None: ...

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult: ...

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply: ...

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]: ...

    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None: ...


class TelegramDispatcher:
    def __init__(
        self,
        service: TelegramFlowService,
        *,
        intent_detector: ProjectIntentDetector | None = None,
        bot_username: str | None = None,
    ) -> None:
        self._service = service
        self._intent_detector = intent_detector or ProjectIntentDetector()
        self._bot_username = bot_username

    def dispatch_message(self, message: object) -> BotReply:
        text = message_text(message)
        if text.startswith("/start"):
            return handle_start(message, self._service)
        if text.startswith("/new"):
            return handle_new_project(message, self._service)
        if text.startswith("/projects"):
            return handle_projects(message, self._service)
        if text.startswith("/status"):
            return handle_status(message, self._service)
        identity = identity_from_message(message)
        intent = self._intent_detector.detect_message(message, bot_username=self._bot_username)
        if intent.is_project_request:
            result = self._service.start_new_project(identity, intent.idea)
            return BotReply(
                text=render_intake_result(result, identity.language_code),
                keyboard=export_choice_keyboard(result.project_id, identity.language_code),
            )
        return BotReply(text=translate("bot.new_project_help", identity.language_code))

    def dispatch_callback(self, callback: object) -> BotReply:
        return handle_callback(callback, self._service)


def create_dispatcher(
    service: TelegramFlowService,
    *,
    bot_username: str | None = None,
) -> TelegramDispatcher:
    return TelegramDispatcher(service, bot_username=bot_username)
