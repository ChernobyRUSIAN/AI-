from dataclasses import dataclass

from vuls.bot.handlers.projects import handle_projects
from vuls.bot.handlers.status import handle_status
from vuls.bot.messages import ProjectStatusView, ProjectSummary, TelegramUserIdentity


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


class FakeTelegramService:
    def __init__(self) -> None:
        self.project_calls: list[TelegramUserIdentity] = []
        self.status_calls: list[TelegramUserIdentity] = []

    def list_recent_projects(self, identity: TelegramUserIdentity) -> list[ProjectSummary]:
        self.project_calls.append(identity)
        return [
            ProjectSummary(project_id="project-1", title="Coffee CRM", status="completed"),
            ProjectSummary(project_id="project-2", title="Tutor Marketplace", status="draft"),
        ]

    def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None:
        self.status_calls.append(identity)
        return ProjectStatusView(
            project_id="project-1",
            title="Coffee CRM",
            status="completed",
            template="crm",
            export="github",
            url="https://github.com/acme/coffee-crm",
        )


def test_projects_lists_recent_projects() -> None:
    service = FakeTelegramService()
    message = FakeMessage(text="/projects", from_user=FakeUser(id=123), chat=FakeChat(id=456))

    reply = handle_projects(message, service)

    assert "Coffee CRM" in reply.text
    assert "Tutor Marketplace" in reply.text
    assert "project-1" in reply.text
    assert service.project_calls[0].telegram_chat_id == 456


def test_status_returns_active_project_status() -> None:
    service = FakeTelegramService()
    message = FakeMessage(text="/status", from_user=FakeUser(id=123), chat=FakeChat(id=456))

    reply = handle_status(message, service)

    assert "Coffee CRM" in reply.text
    assert "completed" in reply.text
    assert "https://github.com/acme/coffee-crm" in reply.text
    assert service.status_calls[0].telegram_user_id == 123


def test_status_handles_no_active_project() -> None:
    class NoActiveProjectService(FakeTelegramService):
        def get_active_project(self, identity: TelegramUserIdentity) -> ProjectStatusView | None:
            self.status_calls.append(identity)
            return None

    reply = handle_status(
        FakeMessage(text="/status", from_user=FakeUser(id=123), chat=FakeChat(id=456)),
        NoActiveProjectService(),
    )

    assert "No active project" in reply.text
