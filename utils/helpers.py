from hook_utils import find_class


def get_client_version_tuple():
    try:
        BuildVars = find_class("org.telegram.messenger.BuildVars")
        if BuildVars and BuildVars.BUILD_VERSION_STRING:
            return tuple(map(int, str(BuildVars.BUILD_VERSION_STRING).split(".")))
    except Exception:
        pass
    return (0, 0, 0)
