from base_plugin import BasePlugin, MethodHook

from ui.settings import build_settings


class Plugin(BasePlugin):
    def on_plugin_load(self):
        pass

    def on_plugin_unload(self):
        pass

    def create_settings(self):
        return build_settings(self)


class ExampleHook(MethodHook):
    def __init__(self, plugin):
        self.plugin = plugin

    def after_hooked_method(self, param):
        pass
