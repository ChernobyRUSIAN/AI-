from vuls.bot.messages import BotButton, BotKeyboard
from vuls.i18n import translate
from vuls.templates.registry import EXPECTED_TEMPLATE_KEYS


def main_actions_keyboard(language_code: str = "en") -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(
                    text=translate("bot.keyboard.new_project", language_code),
                    callback_data="action:new_project",
                ),
                BotButton(
                    text=translate("bot.keyboard.recent_projects", language_code),
                    callback_data="action:projects",
                ),
                BotButton(
                    text=translate("bot.keyboard.status", language_code),
                    callback_data="action:status",
                ),
            ]
        ]
    )


def export_choice_keyboard(project_id: str, language_code: str = "en") -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(
                    text=translate("bot.keyboard.generate_zip", language_code),
                    callback_data=f"export:zip:{project_id}",
                ),
                BotButton(
                    text=translate("bot.keyboard.github_repo", language_code),
                    callback_data=f"export:github:{project_id}",
                ),
            ],
            [
                BotButton(
                    text=translate("bot.keyboard.cancel", language_code),
                    callback_data=f"cancel:{project_id}",
                )
            ],
        ]
    )


def template_choice_keyboard(project_id: str, language_code: str = "en") -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(
                    text=translate(
                        "bot.keyboard.use_template",
                        language_code,
                        template_name=template_key.replace("_", " ").title(),
                    ),
                    callback_data=f"template:{template_key}:{project_id}",
                )
            ]
            for template_key in EXPECTED_TEMPLATE_KEYS
        ]
    )
