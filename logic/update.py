import requests
from pathlib import Path
from utils.constantes import APP_VERSION, VERSION_URL

def check_update(url):
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    data = r.json()

    latest_version = data.get("version")
    if not latest_version:
        raise ValueError("version absente du manifest")
    
    return latest_version != APP_VERSION, data

def download_update(url, target_path):
    r = requests.get(url, stream=True)
    r.raise_for_status()

    with open(target_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)