import requests
import os
import tarfile
import subprocess
import sys
import tempfile
from packaging import version

# Repo GitHub
REPO = "Clemcl0um/gestion_fertilisants"

def get_current_version():
    """
    Retourne la version actuelle de l'app.
    Compatible mode script et binaire PyInstaller.
    """
    try:
        if getattr(sys, 'frozen', False):
            # mode PyInstaller
            base = sys._MEIPASS
        else:
            # mode script Python
            base = os.path.dirname(os.path.abspath(__file__))

        version_file = os.path.join(base, "version.txt")
        with open(version_file) as f:
            return f.read().strip().lstrip("v")
    except Exception as e:
        print("DEBUG: cannot read version.txt:", e)
        return "0.0.0"

def check_update():
    """
    Vérifie la dernière release GitHub.
    Retourne (latest_version, download_url) si update disponible, sinon (None, None)
    """
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    r = requests.get(url).json()
    latest_version = r["tag_name"].lstrip("v")
    current_version = get_current_version()

    if version.parse(latest_version) > version.parse(current_version):
        asset_url = r["assets"][0]["browser_download_url"]
        return latest_version, asset_url

    return None, None

def run_update(download_url):
    """
    Télécharge la release et remplace le binaire en cours.
    Utilise un script temporaire pour éviter conflit lors du remplacement.
    """
    tmpdir = tempfile.mkdtemp()
    archive = os.path.join(tmpdir, "update.tar.gz")

    # Download
    r = requests.get(download_url, stream=True)
    with open(archive, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    # Extract
    with tarfile.open(archive) as tar:
        tar.extractall(tmpdir)

    new_binary = os.path.join(tmpdir, "Gestion_Fertilisant")
    current_binary = os.path.realpath(sys.executable)

    # Script externe pour remplacer le binaire
    script = os.path.join(tmpdir, "replace.sh")
    with open(script, "w") as f:
        f.write(f"""#!/bin/bash
sleep 1
cp "{new_binary}" "{current_binary}"
chmod +x "{current_binary}"
"{current_binary}" &
""")
    os.chmod(script, 0o755)
    subprocess.Popen(["bash", script])
    sys.exit()
