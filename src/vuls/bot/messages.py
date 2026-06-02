from dataclasses import dataclass, field
from typing import Literal

from vuls.i18n import translate


@dataclass(frozen=True)
class TelegramUserIdentity:
    telegram_user_id: int
    telegram_chat_id: int
    username: str | None = None
    display_name: str | None = None
    language_code: str = "en"


@dataclass(frozen=True)
class BotButton:
    text: str
    callback_data: str


@dataclass(frozen=True)
class BotKeyboard:
    rows: list[list[BotButton]]


@dataclass(frozen=True)
class BotReply:
    text: str
    keyboard: BotKeyboard | None = None


@dataclass(frozen=True)
class ProjectIntakeResult:
    project_id: str
    status: str
    message: str
    clarification_questions: list[str] = field(default_factory=list)
    recommended_template: str | None = None


@dataclass(frozen=True)
class ProjectGenerationReply:
    project_id: str
    status: Literal["completed", "failed"]
    template: str
    github_url: str | None = None
    zip_artifact_id: str | None = None


@dataclass(frozen=True)
class ProjectSummary:
    project_id: str
    title: str
    status: str


@dataclass(frozen=True)
class ProjectStatusView:
    project_id: str
    title: str
    status: str
    template: str | None = None
    export: Literal["zip", "github"] | None = None
    url: str | None = None


MAX_CLARIFICATION_QUESTIONS = 3


def identity_from_message(message: object) -> TelegramUserIdentity:
    from_user = getattr(message, "from_user", None)
    chat = getattr(message, "chat", None)
    return TelegramUserIdentity(
        telegram_user_id=_int_attr(from_user, "id"),
        telegram_chat_id=_int_attr(chat, "id"),
        username=_optional_str_attr(from_user, "username"),
        display_name=_optional_str_attr(from_user, "full_name"),
        language_code=_optional_str_attr(from_user, "language_code") or "en",
    )


def identity_from_callback(callback: object) -> TelegramUserIdentity:
    message = getattr(callback, "message", None)
    from_user = getattr(callback, "from_user", None)
    chat = getattr(message, "chat", None)
    return TelegramUserIdentity(
        telegram_user_id=_int_attr(from_user, "id"),
        telegram_chat_id=_int_attr(chat, "id"),
        username=_optional_str_attr(from_user, "username"),
        display_name=_optional_str_attr(from_user, "full_name"),
        language_code=_optional_str_attr(from_user, "language_code") or "en",
    )


def message_text(message: object) -> str:
    text = getattr(message, "text", "")
    return text if isinstance(text, str) else ""


def callback_data(callback: object) -> str:
    data = getattr(callback, "data", "")
    return data if isinstance(data, str) else ""


def command_payload(text: str, command: str) -> str:
    stripped = text.strip()
    if not stripped.startswith(command):
        return ""
    return stripped[len(command) :].strip()


def render_intake_result(result: ProjectIntakeResult, language_code: str = "en") -> str:
    lines = [result.message]
    if result.recommended_template is not None:
        lines.append(
            translate(
                "bot.intake.recommended_template",
                language_code,
                template=result.recommended_template,
            )
        )

    questions = result.clarification_questions[:MAX_CLARIFICATION_QUESTIONS]
    if questions:
        lines.append(translate("bot.intake.clarifying_questions", language_code))
        lines.extend(
            translate(
                "bot.intake.question_line",
                language_code,
                index=index,
                question=question,
            )
            for index, question in enumerate(questions, start=1)
        )

    return "\n".join(lines)


def render_generation_reply(result: ProjectGenerationReply, language_code: str = "en") -> str:
    lines = [
        translate("bot.generation.completed", language_code, project_id=result.project_id),
        translate("bot.generation.template", language_code, template=result.template),
    ]
    if result.github_url is not None:
        lines.append(translate("bot.generation.github_url", language_code, url=result.github_url))
    if result.zip_artifact_id is not None:
        lines.append(
            translate(
                "bot.generation.zip_artifact",
                language_code,
                artifact_id=result.zip_artifact_id,
            )
        )
    return "\n".join(lines)


def render_recent_projects(projects: list[ProjectSummary], language_code: str = "en") -> str:
    if not projects:
        return translate("bot.no_recent_projects", language_code)
    lines = [translate("bot.projects.header", language_code)]
    lines.extend(
        translate(
            "bot.projects.item",
            language_code,
            title=project.title,
            status=project.status,
            project_id=project.project_id,
        )
        for project in projects
    )
    return "\n".join(lines)


def render_project_status(project: ProjectStatusView | None, language_code: str = "en") -> str:
    if project is None:
        return translate("bot.no_active_project", language_code)

    lines = [
        translate("bot.status.header", language_code, title=project.title),
        translate("bot.status.status", language_code, status=project.status),
        translate("bot.status.project_id", language_code, project_id=project.project_id),
    ]
    if project.template is not None:
        lines.append(translate("bot.status.template", language_code, template=project.template))
    if project.export is not None:
        lines.append(translate("bot.status.export", language_code, export=project.export))
    if project.url is not None:
        lines.append(translate("bot.status.url", language_code, url=project.url))
    return "\n".join(lines)


def _int_attr(source: object, attr: str) -> int:
    value = getattr(source, attr, 0)
    return value if isinstance(value, int) else 0


def _optional_str_attr(source: object, attr: str) -> str | None:
    value = getattr(source, attr, None)
    return value if isinstance(value, str) and value else None
