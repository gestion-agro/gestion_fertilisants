# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

# paths.py
import sys
import shutil
from pathlib import Path

APP_NAME = "GestionFertilisants"

def resource_path(relative_path: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path


USER_DATA_DIR = Path.home() / f".{APP_NAME}" / "data"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

def ensure_user_data():
    internal_data = resource_path("data")

    if not internal_data.exists():
        return

    for file in internal_data.iterdir():
        if file.is_file():
            dest = USER_DATA_DIR / file.name
            if not dest.exists():
                shutil.copy(file, dest)


FERT_FILE = USER_DATA_DIR / "fertilisants.json"
CULTURE_FILE = USER_DATA_DIR / "culture.json"
TOTAL_LABEL = "TOTAL"
ICON_FILE = resource_path("icon.ico")