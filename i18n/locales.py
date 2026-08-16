from java.util import Locale

STRINGS = {
    "en": {
        "plugin_obsolete": 'The features of this plugin already work here, so the plugin will delete itself.\n\nTap "OK" to go to the power saving settings.',
        "btn_close": "Close",
        "btn_ok": "OK",
    },
    "ru": {
        "plugin_obsolete": "Функции данного плагина уже здесь работают, так что плагин удалится сам.\n\nНажми «ОК», чтобы перейти в настройки энергосбережения.",  # noqa: E501
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
