from pathlib import Path

import vuls.i18n as i18n
from vuls.bot.handlers.start import handle_start
from vuls.bot.keyboards import main_actions_keyboard
from vuls.bot.messages import BotButton, BotKeyboard, ProjectStatusView, render_project_status


class FakeUser:
    id = 123
    username = "artel"
    full_name = "Artel User"
    language_code = "zz"


class FakeChat:
    id = 456


class FakeMessage:
    text = "/start"
    from_user = FakeUser()
    chat = FakeChat()


class FakeStartService:
    def __init__(self) -> None:
        self.registered = False

    def register_user(self, identity: object) -> None:
        self.registered = True


def test_all_required_locale_files_exist_and_share_keys() -> None:
    assert set(i18n.SUPPORTED_LOCALES) == {
        "ru",
        "en",
        "es",
        "de",
        "fr",
        "pt",
        "it",
        "tr",
        "ar",
        "zh",
        "ja",
        "ko",
    }

    locale_dir = Path("src/vuls/i18n/locales")
    key_sets = {
        locale: set(i18n.load_locale(locale))
        for locale in i18n.SUPPORTED_LOCALES
        if (locale_dir / f"{locale}.json").exists()
    }

    assert set(key_sets) == set(i18n.SUPPORTED_LOCALES)
    assert i18n.validate_locale_keys() == []
    assert all(keys == key_sets["en"] for keys in key_sets.values())


def test_translate_falls_back_to_english_for_unknown_locale() -> None:
    assert i18n.translate("bot.no_active_project", "zz") == (
        "No active project. Send /new to start one."
    )


def test_translate_falls_back_to_english_for_missing_locale_key(
    monkeypatch: object,
) -> None:
    monkeypatch.setattr(
        i18n,
        "_LOCALE_CACHE",
        {
            "en": {"__meta.direction": "ltr", "bot.welcome": "English fallback"},
            "ru": {"__meta.direction": "ltr"},
        },
    )

    assert i18n.translate("bot.welcome", "ru") == "English fallback"


def test_arabic_locale_direction_is_rtl() -> None:
    assert i18n.locale_direction("ar") == "rtl"
    assert i18n.locale_direction("en-US") == "ltr"


def test_bot_renders_english_fallback_for_unknown_language() -> None:
    service = FakeStartService()
    reply = handle_start(FakeMessage(), service)

    assert service.registered is True
    assert reply.text == (
        "Vuls is ready. New project: send /new with a product idea and I will turn it "
        "into a project."
    )
    assert reply.keyboard == BotKeyboard(
        rows=[
            [
                BotButton(text="New project", callback_data="action:new_project"),
                BotButton(text="Recent projects", callback_data="action:projects"),
                BotButton(text="Status", callback_data="action:status"),
            ]
        ]
    )


def test_bot_keyboard_can_render_non_english_locale() -> None:
    keyboard = main_actions_keyboard("ru")

    assert keyboard.rows[0][0].text == "Новый проект"
    assert keyboard.rows[0][1].text == "Последние проекты"


def test_project_status_uses_localized_labels() -> None:
    text = render_project_status(
        ProjectStatusView(
            project_id="project-1",
            title="Coffee CRM",
            status="completed",
            template="crm",
            export="github",
            url="https://github.com/acme/coffee-crm",
        ),
        "es",
    )

    assert "Proyecto activo: Coffee CRM" in text
    assert "Estado: completed" in text
    assert "Plantilla: crm" in text


def test_bot_message_sources_do_not_keep_legacy_literals() -> None:
    sources = [
        Path("src/vuls/bot/messages.py"),
        Path("src/vuls/bot/keyboards.py"),
        Path("src/vuls/bot/dispatcher.py"),
        Path("src/vuls/bot/handlers/callbacks.py"),
        Path("src/vuls/bot/handlers/new_project.py"),
        Path("src/vuls/bot/handlers/start.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in sources)

    assert "Vuls is ready. New project:" not in combined
    assert "Send /new followed by your product idea." not in combined
    assert "Generate ZIP" not in combined
    assert "Create GitHub Repo" not in combined
