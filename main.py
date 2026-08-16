import base64

from android_utils import run_on_ui_thread
from base_plugin import BasePlugin
from client_utils import get_last_fragment
from dalvik.system import InMemoryDexClassLoader
from hook_utils import find_class
from java.nio import ByteBuffer
from ui.alert import AlertDialogBuilder

from data.constants import DEX_B64
from header import __id__
from i18n.locales import _s
from utils.helpers import get_client_version_tuple


class Plugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.receiver_class = None

    def on_plugin_load(self):
        if get_client_version_tuple() >= (12, 6, 0):
            msg = _s("plugin_obsolete")
            self.log(f"[SystemPowersaver] {msg}")

            def _delete_self():
                try:
                    from com.exteragram.messenger.plugins import PluginsController

                    PluginsController.getInstance().deletePlugin(__id__, None)
                except Exception as e:
                    self.log(f"[SystemPowersaver] Error deleting plugin: {e}")

            def _do_alert():
                try:
                    fragment = get_last_fragment()
                    host = fragment.getParentActivity() if fragment else None
                    if host is None:
                        self.log("[SystemPowersaver] host is None! Cannot show alert.")
                        # DO NOT delete self here, otherwise the log is wiped and the user can't read it.
                        return

                    def _ok_clicked(bld, which):
                        try:
                            bld.dismiss()
                        except Exception:
                            pass
                        try:
                            LiteModeSettingsActivity = find_class("org.telegram.ui.LiteModeSettingsActivity")
                            if LiteModeSettingsActivity:
                                fragment.presentFragment(LiteModeSettingsActivity())
                        except Exception as ex:
                            self.log(f"[SystemPowersaver] Failed to open Power Saving settings: {ex}")
                        _delete_self()

                    def _close_clicked(bld, which):
                        try:
                            bld.dismiss()
                        except Exception:
                            pass
                        _delete_self()

                    dlg = AlertDialogBuilder(host)
                    dlg.set_title("Warning" if _s("btn_ok") == "OK" else "Предупреждение")
                    dlg.set_message(msg)
                    dlg.set_positive_button(_s("btn_ok"), _ok_clicked)
                    dlg.set_negative_button(_s("btn_close"), _close_clicked)
                    dlg.show()
                    self.log("[SystemPowersaver] Alert shown successfully.")
                except Exception as e:
                    self.log(f"[SystemPowersaver] Alert error: {e}")
                    # DO NOT delete self on error so the log can be read!

            run_on_ui_thread(_do_alert)
            return

        try:
            ApplicationLoader = find_class("org.telegram.messenger.ApplicationLoader")
            if not ApplicationLoader:
                return
            context = ApplicationLoader.applicationContext
            if not context:
                return

            dex_bytes = base64.b64decode(DEX_B64)
            dex_buffer = ByteBuffer.wrap(dex_bytes)
            parent_cl = context.getClassLoader()
            class_loader = InMemoryDexClassLoader(dex_buffer, parent_cl)

            receiver_class = class_loader.loadClass("non.feature.powersaver.PowerSaveReceiver")
            if not receiver_class:
                return

            register_method = receiver_class.getMethod("register", find_class("android.content.Context"))
            register_method.invoke(None, context)
            self.receiver_class = receiver_class

            self.log("[SystemPowersaver] Native Java System Power Saver loaded.")
        except Exception as e:
            self.log(f"[SystemPowersaver] Error on load: {e}")

    def on_plugin_unload(self):
        try:
            if hasattr(self, "receiver_class") and self.receiver_class:
                ApplicationLoader = find_class("org.telegram.messenger.ApplicationLoader")
                context = ApplicationLoader.applicationContext
                if context:
                    unregister_method = self.receiver_class.getMethod("unregister", find_class("android.content.Context"))
                    unregister_method.invoke(None, context)
                    self.log("[SystemPowersaver] BroadcastReceiver unregistered successfully.")
        except Exception as e:
            self.log(f"[SystemPowersaver] Error on unload: {e}")
