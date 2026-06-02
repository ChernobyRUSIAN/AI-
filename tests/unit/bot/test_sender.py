import asyncio

from vuls.bot.messages import BotButton, BotKeyboard, BotReply
from vuls.bot.sender import TelegramSender


class FakeBot:
    def __init__(self) -> None:
        self.sent_messages: list[dict[str, object]] = []

    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: object | None = None,
    ) -> object:
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
            }
        )
        return object()


def test_sender_sends_text_message() -> None:
    bot = FakeBot()
    sender = TelegramSender(bot=bot)

    asyncio.run(sender.send_reply(chat_id=456, reply=BotReply(text="Project started.")))

    assert bot.sent_messages == [
        {
            "chat_id": 456,
            "text": "Project started.",
            "reply_markup": None,
        }
    ]


def test_sender_maps_bot_keyboard_to_inline_keyboard() -> None:
    bot = FakeBot()
    sender = TelegramSender(bot=bot)

    asyncio.run(
        sender.send_reply(
            chat_id=456,
            reply=BotReply(
                text="Choose export.",
                keyboard=BotKeyboard(
                    rows=[
                        [
                            BotButton(text="ZIP", callback_data="export:zip:project-1"),
                            BotButton(text="GitHub", callback_data="export:github:project-1"),
                        ],
                        [BotButton(text="Cancel", callback_data="cancel:project-1")],
                    ]
                ),
            ),
        )
    )

    reply_markup = bot.sent_messages[0]["reply_markup"]

    assert reply_markup is not None
    assert reply_markup.inline_keyboard[0][0].text == "ZIP"
    assert reply_markup.inline_keyboard[0][0].callback_data == "export:zip:project-1"
    assert reply_markup.inline_keyboard[0][1].text == "GitHub"
    assert reply_markup.inline_keyboard[1][0].callback_data == "cancel:project-1"
