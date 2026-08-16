from java.util import Locale

STRINGS = {
    "ru": {
        "example": "Пример",
    },
    "en": {
        "example": "Example",
    },
}


def get_language():
    try:
        return "ru" if Locale.getDefault().getLanguage() == "ru" else "en"
    except Exception:
        return "en"


def get_string(key):
    lang = get_language()
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, ""))
