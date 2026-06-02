from dataclasses import dataclass
from typing import Literal

from vuls.bot.dispatcher import TelegramDispatcher
from vuls.bot.intent import ProjectIntentDetector
from vuls.bot.messages import (
    ProjectGenerationReply,
    ProjectIntakeResult,
    TelegramUserIdentity,
)


@dataclass
class FakeChat:
    id: int
    type: Literal["private", "group", "supergroup"] = "private"


@dataclass
class FakeUser:
    id: int
    username: str | None = None
    language_code: str | None = None
    full_name: str | None = None


@dataclass
class FakeMessage:
    text: str
    from_user: FakeUser
    chat: FakeChat


class FakeTelegramService:
    def __init__(self) -> None:
        self.started_projects: list[tuple[TelegramUserIdentity, str]] = []

    def register_user(self, identity: TelegramUserIdentity) -> None:
        raise AssertionError("register_user should not be called")

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult:
        self.started_projects.append((identity, idea))
        return ProjectIntakeResult(
            project_id="project-1",
            status="clarifying",
            message="I can build this CRM.",
            clarification_questions=[],
            recommended_template="crm",
        )

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply:
        raise AssertionError("generate_project should not be called")

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[object]:
        raise AssertionError("list_recent_projects should not be called")

    def get_active_project(self, identity: TelegramUserIdentity) -> object | None:
        raise AssertionError("get_active_project should not be called")


def test_private_car_wash_crm_text_is_project_intent() -> None:
    result = ProjectIntentDetector().detect_message(
        FakeMessage(
            text="Create a CRM for a car wash",
            from_user=FakeUser(id=123),
            chat=FakeChat(id=456, type="private"),
        )
    )

    assert result.is_project_request is True
    assert result.idea == "Create a CRM for a car wash"


def test_normal_private_chat_is_not_project_intent() -> None:
    result = ProjectIntentDetector().detect_message(
        FakeMessage(
            text="hello, thanks for your help today",
            from_user=FakeUser(id=123),
            chat=FakeChat(id=456, type="private"),
        )
    )

    assert result.is_project_request is False


def test_group_plain_text_requires_bot_mention_or_new_command() -> None:
    detector = ProjectIntentDetector()
    unmentioned = FakeMessage(
        text="Create a CRM for a car wash",
        from_user=FakeUser(id=123),
        chat=FakeChat(id=456, type="group"),
    )
    mentioned = FakeMessage(
        text="@vuls_bot Create a CRM for a car wash",
        from_user=FakeUser(id=123),
        chat=FakeChat(id=456, type="group"),
    )
    command = FakeMessage(
        text="/new Create a CRM for a car wash",
        from_user=FakeUser(id=123),
        chat=FakeChat(id=456, type="group"),
    )

    assert detector.detect_message(unmentioned, bot_username="vuls_bot").is_project_request is False
    assert detector.detect_message(mentioned, bot_username="vuls_bot").is_project_request is True
    assert detector.detect_message(command, bot_username="vuls_bot").is_project_request is True


def test_dispatcher_starts_project_for_detected_plain_text_intent() -> None:
    service = FakeTelegramService()
    dispatcher = TelegramDispatcher(service)

    reply = dispatcher.dispatch_message(
        FakeMessage(
            text="Create a CRM for a car wash",
            from_user=FakeUser(id=123, username="artel", language_code="en"),
            chat=FakeChat(id=456, type="private"),
        )
    )

    assert service.started_projects[0][1] == "Create a CRM for a car wash"
    assert "I can build this CRM." in reply.text
    assert reply.keyboard is not None
