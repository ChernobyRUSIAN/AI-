from collections.abc import Sequence

from vuls.memory.schemas import ConversationDirection, ConversationMessage

_SPEAKER_LABELS = {
    ConversationDirection.INBOUND: "User",
    ConversationDirection.OUTBOUND: "Vuls",
    ConversationDirection.SYSTEM: "System",
}


def summarize_conversation(
    messages: Sequence[ConversationMessage],
    *,
    max_chars: int = 1200,
) -> str:
    lines: list[str] = []

    for message in messages:
        text = _normalize_text(message.text)
        if not text:
            continue
        label = _SPEAKER_LABELS[message.direction]
        lines.append(f"{label}: {text}")

    summary = " | ".join(lines) if lines else "No conversation text was provided."
    return _truncate(summary, max_chars=max_chars)


def _normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(text.split())


def _truncate(text: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    if max_chars <= 3:
        return text[:max_chars]
    return f"{text[: max_chars - 3].rstrip()}..."
