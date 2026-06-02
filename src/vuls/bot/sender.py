from typing import Protocol, Self

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from vuls.bot.messages import BotKeyboard, BotReply


class TelegramBotClient(Protocol):
    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> object: ...


class TelegramSender:
    def __init__(self, *, bot: TelegramBotClient) -> None:
        self._bot = bot

    @classmethod
    def from_token(cls, token: str) -> Self:
        return cls(bot=Bot(token))

    async def send_reply(self, *, chat_id: int, reply: BotReply) -> None:
        await self._bot.send_message(
            chat_id=chat_id,
            text=reply.text,
            reply_markup=inline_keyboard_markup(reply.keyboard),
        )


def inline_keyboard_markup(keyboard: BotKeyboard | None) -> InlineKeyboardMarkup | None:
    if keyboard is None:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=button.text, callback_data=button.callback_data)
                for button in row
            ]
            for row in keyboard.rows
        ]
    )
