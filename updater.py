import requests
import os
import tarfile
import subprocess
import sys
import tempfile

REPO = "Clemcl0um/gestion_fertilisants"

def get_current_version():
    try:
        base = os.path.dirname(sys.executable)
        with open(os.path.join(base, "version.txt")) as f:
            return f.read().strip()
    except:
        return "0.0.0"

def check_update():
    url = f"https://api.github.com/repos/{REPO}/releases/latest"
    r = requests.get(url).json()
    latest = r["tag_name"].replace("v", "")
    current = get_current_version()
    if latest > current:
        asset = r["assets"][0]["browser_download_url"]
        return latest, asset
    return None, None

def run_update(download_url):
    tmpdir = tempfile.mkdtemp()
    archive = os.path.join(tmpdir, "update.tar.gz")

    # download
    r = requests.get(download_url, stream=True)
    with open(archive, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    # extract
    with tarfile.open(archive) as tar:
        tar.extractall(tmpdir)

    new_binary = os.path.join(tmpdir, "Gestion_Fertilisant")
    current_binary = os.path.realpath(sys.executable)

    # script externe pour remplacer binaire en cours
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
