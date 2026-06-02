from dataclasses import dataclass
from typing import Literal

from vuls.bot.handlers.callbacks import handle_callback
from vuls.bot.handlers.new_project import handle_new_project
from vuls.bot.handlers.projects import handle_projects
from vuls.bot.handlers.start import handle_start
from vuls.bot.handlers.status import handle_status
from vuls.bot.messages import (
    ProjectGenerationReply,
    ProjectIntakeResult,
    ProjectStatusView,
    ProjectSummary,
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
        self.registered = False
        self.active_project_id: str | None = None
        self.export: Literal["zip", "github"] | None = None

    def register_user(self, identity: TelegramUserIdentity) -> None:
        self.registered = True

    def start_new_project(
        self,
        identity: TelegramUserIdentity,
        idea: str,
    ) -> ProjectIntakeResult:
        self.active_project_id = "project-1"
        return ProjectIntakeResult(
            project_id="project-1",
            status="clarifying",
            message="Vuls prepared your project brief.",
            clarification_questions=["Who will use it?", "What must be included?"],
            recommended_template="crm",
        )

    def generate_project(
        self,
        identity: TelegramUserIdentity,
        project_id: str,
        export: Literal["zip", "github"],
    ) -> ProjectGenerationReply:
        self.export = export
        return ProjectGenerationReply(
            project_id=project_id,
            status="completed",
            template="crm",
            github_url="https://github.com/acme/coffee-crm" if export == "github" else None,
            zip_artifact_id="zip-1" if export == "zip" else None,
        )

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]:
        return [
            ProjectSummary(
                project_id="project-1",
                title="Coffee CRM",
                status="completed" if self.export else "clarifying",
            )
        ]

    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None:
        if self.active_project_id is None:
            return None
        return ProjectStatusView(
            project_id=self.active_project_id,
            title="Coffee CRM",
            status="completed" if self.export else "clarifying",
            template="crm",
            export=self.export,
            url="https://github.com/acme/coffee-crm" if self.export == "github" else None,
        )


def test_telegram_intake_flow_from_start_to_github_export_and_status() -> None:
    service = FakeTelegramService()
    user = FakeUser(id=123, username="artel", full_name="Artel User", language_code="en")
    chat = FakeChat(id=456)

    start_reply = handle_start(FakeMessage(text="/start", from_user=user, chat=chat), service)
    intake_reply = handle_new_project(
        FakeMessage(text="/new Create a CRM for a coffee shop", from_user=user, chat=chat),
        service,
    )
    export_reply = handle_callback(
        FakeCallback(
            data="export:github:project-1",
            from_user=user,
            message=FakeMessage(text="", from_user=user, chat=chat),
        ),
        service,
    )
    projects_reply = handle_projects(
        FakeMessage(text="/projects", from_user=user, chat=chat),
        service,
    )
    status_reply = handle_status(FakeMessage(text="/status", from_user=user, chat=chat), service)

    assert service.registered is True
    assert "New project" in start_reply.text
    assert intake_reply.text.count("?") == 2
    assert "https://github.com/acme/coffee-crm" in export_reply.text
    assert "Coffee CRM" in projects_reply.text
    assert "completed" in status_reply.text
