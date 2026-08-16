from java.util import Locale

STRINGS = {
    "en": {
        "plugin_obsolete": 'The functionality of this plugin is already implemented in this app version.\n\nPressing "OK" will redirect you to the power saving settings.',  # noqa: E501
        "btn_close": "Close",
        "btn_ok": "OK",
    },
    "ru": {
        "plugin_obsolete": 'Функционал этого плагина уже реализован в этой версии приложения.\n\nПри нажатии кнопки "OK", вас перенаправит в настройки энергосбережения.',  # noqa: E501
        "btn_close": "Закрыть",
        "btn_ok": "ОК",
    },
}


def get_language():
    try:
        return "ru" if Locale.getDefault().getLanguage() == "ru" else "en"
    except Exception:
        return "en"


def _s(key):
    lang = get_language()
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
