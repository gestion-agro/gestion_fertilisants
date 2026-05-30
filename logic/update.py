import sys

from updater.windows import update_windows
from updater.linux import update_linux
from updater.macos import update_macos


def run_update(data):
    if sys.platform == "win32":
        return update_windows(data["windows"])

    elif sys.platform.startswith("linux"):
        return update_linux(data["linux"])

    elif sys.platform == "darwin":
        return update_macos(data["macos"])

    else:
        raise OSError("OS non supporté")
