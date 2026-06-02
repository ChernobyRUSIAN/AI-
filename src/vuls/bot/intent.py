import re
from dataclasses import dataclass
from typing import Literal

from vuls.bot.messages import message_text

ProjectIntentReason = Literal[
    "detected",
    "empty",
    "normal_chat",
    "group_requires_mention",
    "too_short",
    "missing_signal",
]


@dataclass(frozen=True)
class ProjectIntentResult:
    is_project_request: bool
    idea: str
    reason: ProjectIntentReason


class ProjectIntentDetector:
    _build_verbs = frozenset({"create", "build", "make", "generate", "develop"})
    _product_nouns = frozenset(
        {
            "agent",
            "app",
            "bot",
            "crm",
            "dashboard",
            "marketplace",
            "saas",
            "tool",
            "website",
        }
    )
    _normal_chat_phrases = frozenset(
        {
            "hello",
            "hi",
            "how are you",
            "ok",
            "thanks",
            "thank you",
            "what can you do",
        }
    )

    def detect_message(
        self,
        message: object,
        *,
        bot_username: str | None = None,
    ) -> ProjectIntentResult:
        return self.detect_text(
            message_text(message),
            chat_type=_chat_type(message),
            bot_username=bot_username,
        )

    def detect_text(
        self,
        text: str,
        *,
        chat_type: str = "private",
        bot_username: str | None = None,
    ) -> ProjectIntentResult:
        stripped = text.strip()
        if not stripped:
            return ProjectIntentResult(False, "", "empty")

        is_new_command = _is_new_command(stripped)
        is_group_chat = chat_type in {"group", "supergroup"}
        has_mention = _has_bot_mention(stripped, bot_username)
        if is_group_chat and not is_new_command and not has_mention:
            return ProjectIntentResult(False, stripped, "group_requires_mention")

        idea = _strip_new_command(stripped) if is_new_command else stripped
        idea = _strip_bot_mention(idea, bot_username)
        normalized_idea = " ".join(idea.split())
        if _is_normal_chat(normalized_idea):
            return ProjectIntentResult(False, normalized_idea, "normal_chat")

        words = _words(normalized_idea)
        if len(words) < 4:
            return ProjectIntentResult(False, normalized_idea, "too_short")

        has_build_verb = any(word in self._build_verbs for word in words)
        has_product_noun = any(word in self._product_nouns for word in words)
        if has_build_verb and has_product_noun:
            return ProjectIntentResult(True, normalized_idea, "detected")

        return ProjectIntentResult(False, normalized_idea, "missing_signal")


def _chat_type(message: object) -> str:
    chat = getattr(message, "chat", None)
    value = getattr(chat, "type", "private")
    return value if isinstance(value, str) and value else "private"


def _is_new_command(text: str) -> bool:
    return text.lower().startswith("/new")


def _strip_new_command(text: str) -> str:
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def _has_bot_mention(text: str, bot_username: str | None) -> bool:
    if bot_username is None:
        return False
    username = bot_username.removeprefix("@")
    return re.search(rf"@{re.escape(username)}\b", text, flags=re.IGNORECASE) is not None


def _strip_bot_mention(text: str, bot_username: str | None) -> str:
    if bot_username is None:
        return text
    username = bot_username.removeprefix("@")
    return re.sub(rf"@{re.escape(username)}\b", "", text, flags=re.IGNORECASE).strip()


def _is_normal_chat(text: str) -> bool:
    normalized = text.lower().strip(" .,!?:;")
    return normalized in ProjectIntentDetector._normal_chat_phrases


def _words(text: str) -> list[str]:
    return [word.lower() for word in re.findall(r"[A-Za-z0-9_]+", text)]
