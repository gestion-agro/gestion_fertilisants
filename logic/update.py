# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import requests
import subprocess
import sys
import os
import shutil
import zipfile
from pathlib import Path

import utils.debug as debug
from utils.constantes import APP_VERSION, VERSION_URL


# =========================
# CHECK UPDATE
# =========================
def check_update():
    debug.debug(f"[update] Version actuelle : {APP_VERSION}")
    debug.debug(f"[update] URL manifest : {VERSION_URL}")

    try:
        r = requests.get(VERSION_URL, timeout=5)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError("Impossible de contacter le serveur. Vérifiez votre connexion.")
    except requests.exceptions.Timeout:
        raise ConnectionError("La vérification a expiré (timeout 5s).")
    except requests.exceptions.HTTPError as e:
        raise ConnectionError(f"Erreur HTTP {e.response.status_code} : {VERSION_URL}")

    try:
        data = r.json()
    except Exception:
        raise ValueError(f"Réponse invalide (non JSON) : {r.text[:200]}")

    debug.debug(f"[update] Manifest reçu : {data}")

    latest_version = data.get("version")
    if not latest_version:
        raise ValueError("Champ 'version' absent du manifest.")

    debug.debug(f"[update] Version distante : {latest_version}")
    available = latest_version != APP_VERSION
    debug.debug(f"[update] Mise à jour disponible : {available}")

    return available, data


# =========================
# DOWNLOAD FILE
# =========================
def download_file(url, target, progress_callback=None):
    debug.debug(f"[update] Téléchargement : {url} → {target}")

    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Impossible de télécharger : {url}")

    total = int(r.headers.get("content-length", 0))
    downloaded = 0

    with open(target, "wb") as f:
        for chunk in r.iter_content(65536):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback and total:
                    pct = int(downloaded / total * 100)
                    progress_callback(pct)

    debug.debug(f"[update] Téléchargement terminé : {downloaded} octets")
    return target


# =========================
# WINDOWS (installateur .exe)
# =========================
def update_windows(url):
    debug.debug("[update] Plateforme : Windows")
    target = Path(os.environ.get("TEMP", ".")) / "GestionFertilisant_setup.exe"

    download_file(url, target)

    debug.debug(f"[update] Lancement installateur : {target}")
    subprocess.Popen([str(target)])
    sys.exit()


# =========================
# LINUX (binaire)
# =========================
def update_linux(url):
    debug.debug("[update] Plateforme : Linux")

    # On télécharge à côté du binaire courant
    if getattr(sys, "frozen", False):
        # Mode PyInstaller — exe actuel
        current_exe = Path(sys.executable)
    else:
        # Mode script — dans le dossier du projet
        current_exe = Path(__file__).parent.parent / "dist" / "Gestion_Fertilisant"

    new_path = current_exe.parent / (current_exe.name + ".new")

    debug.debug(f"[update] Binaire actuel : {current_exe}")
    debug.debug(f"[update] Téléchargement vers : {new_path}")

    download_file(url, new_path)
    os.chmod(new_path, 0o755)

    # Script de remplacement externe
    script = new_path.parent / "update_replace.sh"
    with open(script, "w") as f:
        f.write(f"""#!/bin/bash
sleep 1
mv "{new_path}" "{current_exe}"
chmod +x "{current_exe}"
"{current_exe}" &
""")
    os.chmod(script, 0o755)
    debug.debug(f"[update] Script de remplacement : {script}")

    subprocess.Popen(["bash", str(script)])
    sys.exit()


# =========================
# MACOS (.app dans zip)
# =========================
def update_macos(url):
    debug.debug("[update] Plateforme : macOS")
    tmp_zip = Path.home() / "GestionFertilisant_update.zip"

    download_file(url, tmp_zip)

    extract_dir = Path.home() / "GestionFertilisant_update_tmp"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir()

    debug.debug(f"[update] Extraction dans : {extract_dir}")
    with zipfile.ZipFile(tmp_zip, "r") as z:
        z.extractall(extract_dir)

    new_app = next(extract_dir.glob("*.app"), None)
    if not new_app:
        raise FileNotFoundError("Aucun .app trouvé dans l'archive.")

    app_path = Path("/Applications/GestionFertilisant.app")
    if app_path.exists():
        shutil.rmtree(app_path)

    shutil.move(str(new_app), str(app_path))
    debug.debug(f"[update] Application installée : {app_path}")

    subprocess.Popen(["open", str(app_path)])
    sys.exit()


# =========================
# DISPATCHER
# =========================
def run_update(data):
    debug.debug(f"[update] run_update appelé, plateforme : {sys.platform}")

    if sys.platform == "win32":
        url = data.get("windows")
        if not url:
            raise KeyError("URL 'windows' absente du manifest.")
        update_windows(url)

    elif sys.platform.startswith("linux"):
        url = data.get("linux")
        if not url:
            raise KeyError("URL 'linux' absente du manifest.")
        update_linux(url)

    elif sys.platform == "darwin":
        url = data.get("macos")
        if not url:
            raise KeyError("URL 'macos' absente du manifest.")
        update_macos(url)

    else:
        raise OSError(f"Plateforme non supportée : {sys.platform}")


# =========================
# MAIN CHECK (auto au démarrage)
# =========================
def update_if_available():
    debug.debug("[update] Vérification automatique des mises à jour...")
    try:
        available, data = check_update()
    except Exception as e:
        debug.debug(f"[update] Erreur vérification : {e}")
        return False

    if not available:
        debug.debug("[update] Pas de mise à jour disponible.")
        return False

    debug.debug("[update] Mise à jour disponible, lancement...")
    run_update(data)
    return True