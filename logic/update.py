import requests
import subprocess
import sys
import os
import shutil
import zipfile
from pathlib import Path

from utils.constantes import APP_VERSION, VERSION_URL


# =========================
# CHECK UPDATE
# =========================
def check_update():
    r = requests.get(VERSION_URL, timeout=5)
    r.raise_for_status()
    data = r.json()

    latest_version = data.get("version")
    if not latest_version:
        raise ValueError("version absente du manifest")

    return latest_version != APP_VERSION, data


# =========================
# DOWNLOAD FILE
# =========================
def download_file(url, target):
    r = requests.get(url, stream=True, timeout=10)
    r.raise_for_status()

    with open(target, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

    return target


# =========================
# WINDOWS (INNO SETUP)
# =========================
def update_windows(url):
    target = Path("update_setup.exe")

    download_file(url, target)

    # lance installateur
    subprocess.Popen([str(target)])
    sys.exit()


# =========================
# LINUX (APPIMAGE)
# =========================
def update_linux(url):
    app_path = Path.home() / "GestionFertilisant.AppImage"
    new_path = Path.home() / "GestionFertilisant.new.AppImage"

    download_file(url, new_path)

    os.chmod(new_path, 0o755)

    shutil.move(str(new_path), str(app_path))

    subprocess.Popen([str(app_path)])
    sys.exit()


# =========================
# MACOS (.APP ZIP)
# =========================
def update_macos(url):
    tmp_zip = Path.home() / "update.zip"

    download_file(url, tmp_zip)

    extract_dir = Path.home() / "update_tmp"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    extract_dir.mkdir()

    with zipfile.ZipFile(tmp_zip, "r") as z:
        z.extractall(extract_dir)

    new_app = next(extract_dir.glob("*.app"))

    app_path = Path("/Applications/GestionFertilisant.app")

    if app_path.exists():
        shutil.rmtree(app_path)

    shutil.move(str(new_app), str(app_path))

    subprocess.Popen(["open", str(app_path)])
    sys.exit()


# =========================
# DISPATCHER
# =========================
def run_update(data):
    url = None

    if sys.platform == "win32":
        url = data["windows"]
        update_windows(url)

    elif sys.platform.startswith("linux"):
        url = data["linux"]
        update_linux(url)

    elif sys.platform == "darwin":
        url = data["macos"]
        update_macos(url)

    else:
        raise OSError("OS non supporté")


# =========================
# MAIN CHECK
# =========================
def update_if_available():
    available, data = check_update()

    if not available:
        return False

    run_update(data)
    return True
