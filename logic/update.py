import requests
import subprocess
import sys
from pathlib import Path

from utils.constantes import APP_VERSION, VERSION_URL


# =========================
# CHECK VERSION
# =========================
def check_update(url=VERSION_URL):
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    data = r.json()

    latest_version = data.get("version")
    if not latest_version:
        raise ValueError("version absente du manifest")

    download_url = data.get("windows")  # ex: Setup.exe

    if not download_url:
        raise ValueError("URL de téléchargement manquante (windows)")

    return latest_version != APP_VERSION, data


# =========================
# DOWNLOAD FILE (SETUP.EXE)
# =========================
def download_update(url, target_path):
    r = requests.get(url, stream=True, timeout=10)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))

    with open(target_path, "wb") as f:
        downloaded = 0

        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)

    return target_path


# =========================
# INSTALL UPDATE (WINDOWS)
# =========================
def run_installer(installer_path: Path):
    """
    Lance l'installateur Inno Setup.
    Peut être silencieux si /VERYSILENT est activé côté Inno Setup.
    """

    if sys.platform == "win32":
        subprocess.Popen([str(installer_path)])
        sys.exit(0)
    else:
        raise OSError("Update installer only supported on Windows")


# =========================
# FULL UPDATE FLOW
# =========================
def update_if_available():
    update_available, data = check_update()

    if not update_available:
        return False

    url = data["windows"]  # Setup.exe
    target = Path("update_installer.exe")

    download_update(url, target)
    run_installer(target)

    return True
