from dataclasses import dataclass
from typing import Literal

from vuls.bot.handlers.callbacks import handle_callback
from vuls.bot.handlers.new_project import handle_new_project
from vuls.bot.messages import (
    ProjectGenerationReply,
    ProjectIntakeResult,
    TelegramUserIdentity,
)


@dataclass
class FakeUser:
    id: int
    username: str | None = None
    full_name: str | None = None
    language_code: str | None = None


@dataclass
class FakeChat:
    id: int


@dataclass
class FakeMessage:
    text: str
    from_user: FakeUser
    chat: FakeChat


@dataclass
class FakeCallback:
    data: str
    from_user: FakeUser
    message: FakeMessage


class FakeTelegramService:
    def __init__(self) -> None:
        self.new_project_calls: list[tuple[TelegramUserIdentity, str]] = []
        self.generate_calls: list[tuple[TelegramUserIdentity, str, Literal["zip", "github"]]] = []

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult:
        self.new_project_calls.append((identity, idea))
        return ProjectIntakeResult(
            project_id="project-1",
            status="clarifying",
            message="I can build this CRM.",
            clarification_questions=[
                "Who will use it?",
                "Which entities matter most?",
                "Do you prefer ZIP or GitHub?",
                "This fourth question must not be shown.",
            ],
            recommended_template="crm",
        )

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply:
        self.generate_calls.append((identity, project_id, export))
        return ProjectGenerationReply(
            project_id=project_id,
            status="completed",
            template="crm",
            github_url="https://github.com/acme/coffee-crm" if export == "github" else None,
            zip_artifact_id="artifact-zip-1" if export == "zip" else None,
        )


def test_new_project_starts_intake_and_limits_clarifying_questions_to_three() -> None:
    service = FakeTelegramService()
    message = FakeMessage(
        text="/new Create a CRM for a coffee shop",
        from_user=FakeUser(id=123, username="artel", full_name="Artel User", language_code="en"),
        chat=FakeChat(id=456),
    )

    reply = handle_new_project(message, service)

    assert service.new_project_calls[0][1] == "Create a CRM for a coffee shop"
    assert reply.text.count("?") == 3
    assert "This fourth question must not be shown." not in reply.text
    assert "Recommended template: crm" in reply.text
    assert reply.keyboard is not None
    assert [button.callback_data for row in reply.keyboard.rows for button in row] == [
        "export:zip:project-1",
        "export:github:project-1",
        "cancel:project-1",
    ]


def test_new_project_without_idea_does_not_call_service() -> None:
    service = FakeTelegramService()
    message = FakeMessage(
        text="/new",
        from_user=FakeUser(id=123),
        chat=FakeChat(id=456),
    )

    reply = handle_new_project(message, service)

    assert service.new_project_calls == []
    assert "Send /new followed by your product idea" in reply.text


def test_export_callbacks_call_generation_with_requested_export_mode() -> None:
    service = FakeTelegramService()
    callback = FakeCallback(
        data="export:github:project-1",
        from_user=FakeUser(id=123, username="artel", language_code="en"),
        message=FakeMessage(text="", from_user=FakeUser(id=123), chat=FakeChat(id=456)),
    )

    reply = handle_callback(callback, service)

    assert service.generate_calls == [
        (
            TelegramUserIdentity(
                telegram_user_id=123,
                telegram_chat_id=456,
                username="artel",
                display_name=None,
                language_code="en",
            ),
            "project-1",
            "github",
        )
    ]
    assert "https://github.com/acme/coffee-crm" in reply.text
