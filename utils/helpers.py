from hook_utils import find_class


def has_native_power_saver():
    """exteraGram 12.6.4+ adds a "follow system power saving" toggle under
    the battery slider in Lite Mode settings (LiteMode.isPowerSaverFollowSystem).
    When that toggle exists, the plugin's job is done natively."""
    try:
        LiteMode = find_class("org.telegram.messenger.LiteMode")
        if not LiteMode:
            return False
        cls = LiteMode.getClass()
        cls.getDeclaredMethod("isPowerSaverFollowSystem")
        return True
    except Exception:
        return False
