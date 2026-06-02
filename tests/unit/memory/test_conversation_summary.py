from vuls.memory.schemas import ConversationMessage
from vuls.memory.summarizer import summarize_conversation


def test_summarize_conversation_uses_deterministic_local_fallback() -> None:
    messages = [
        ConversationMessage(
            direction="inbound",
            message_type="text",
            text="Create a CRM\nfor a coffee shop",
        ),
        ConversationMessage(
            direction="outbound",
            message_type="text",
            text="Should it include customers and orders?",
        ),
        ConversationMessage(
            direction="inbound",
            message_type="text",
            text="Yes, owner and staff need it.",
        ),
    ]

    summary = summarize_conversation(messages, max_chars=500)

    assert (
        summary
        == "User: Create a CRM for a coffee shop | "
        "Vuls: Should it include customers and orders? | "
        "User: Yes, owner and staff need it."
    )


def test_summarize_conversation_bounds_prompt_context() -> None:
    messages = [
        ConversationMessage(
            direction="inbound",
            message_type="text",
            text="Build a CRM with customers, orders, tasks, reports and staff permissions.",
        )
    ]

    summary = summarize_conversation(messages, max_chars=48)

    assert len(summary) <= 48
    assert summary.endswith("...")
