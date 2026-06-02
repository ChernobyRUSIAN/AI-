from vuls.bot.messages import BotButton, BotKeyboard
from vuls.templates.registry import EXPECTED_TEMPLATE_KEYS


def main_actions_keyboard() -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(text="New project", callback_data="action:new_project"),
                BotButton(text="Recent projects", callback_data="action:projects"),
                BotButton(text="Status", callback_data="action:status"),
            ]
        ]
    )


def export_choice_keyboard(project_id: str) -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(text="Generate ZIP", callback_data=f"export:zip:{project_id}"),
                BotButton(text="Create GitHub Repo", callback_data=f"export:github:{project_id}"),
            ],
            [BotButton(text="Cancel", callback_data=f"cancel:{project_id}")],
        ]
    )


def template_choice_keyboard(project_id: str) -> BotKeyboard:
    return BotKeyboard(
        rows=[
            [
                BotButton(
                    text=f"Use {template_key.replace('_', ' ').title()} Template",
                    callback_data=f"template:{template_key}:{project_id}",
                )
            ]
            for template_key in EXPECTED_TEMPLATE_KEYS
        ]
    )
