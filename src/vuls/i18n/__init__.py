import json
from pathlib import Path
from typing import Literal, cast

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = (
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
)
META_DIRECTION_KEY = "__meta.direction"

_LOCALE_DIR = Path(__file__).parent / "locales"
_LOCALE_CACHE: dict[str, dict[str, str]] = {}


def translate(key: str, locale: str | None = None, **params: object) -> str:
    active_locale = normalize_locale(locale)
    catalog = load_locale(active_locale)
    fallback_catalog = load_locale(DEFAULT_LOCALE)

    value = catalog.get(key) or fallback_catalog.get(key)
    if value is None:
        raise KeyError(f"Missing i18n key: {key}")
    if params:
        return value.format(**params)
    return value


def load_locale(locale: str) -> dict[str, str]:
    normalized = normalize_locale(locale)
    if normalized in _LOCALE_CACHE:
        return _LOCALE_CACHE[normalized]

    if normalized not in SUPPORTED_LOCALES:
        normalized = DEFAULT_LOCALE

    path = _LOCALE_DIR / f"{normalized}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or any(not isinstance(key, str) for key in raw):
        raise ValueError(f"Invalid locale catalog: {normalized}")
    if any(not isinstance(value, str) for value in raw.values()):
        raise ValueError(f"Locale catalog values must be strings: {normalized}")

    catalog = cast(dict[str, str], raw)
    _LOCALE_CACHE[normalized] = catalog
    return catalog


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    language = locale.replace("_", "-").split("-", maxsplit=1)[0].lower()
    if language in SUPPORTED_LOCALES:
        return language
    return DEFAULT_LOCALE


def locale_direction(locale: str | None) -> Literal["ltr", "rtl"]:
    direction = translate(META_DIRECTION_KEY, locale)
    if direction == "rtl":
        return "rtl"
    return "ltr"


def validate_locale_keys() -> list[str]:
    expected_keys = set(load_locale(DEFAULT_LOCALE))
    errors: list[str] = []
    for locale in SUPPORTED_LOCALES:
        keys = set(load_locale(locale))
        missing = sorted(expected_keys - keys)
        extra = sorted(keys - expected_keys)
        if missing:
            errors.append(f"{locale} missing keys: {', '.join(missing)}")
        if extra:
            errors.append(f"{locale} extra keys: {', '.join(extra)}")
    return errors
