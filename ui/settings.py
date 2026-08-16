from i18n.locales import get_string
from ui.settings import Header


def build_settings(plugin):
    settings = [
        Header(text=get_string("example")),
    ]
    return settings
