import json
from pathlib import Path

DATA_FILE = Path("data/donnees.json")

def charger_donnees():
	if not DATA_FILE.exists():
		return {"ferilisant": []}
	with open(DATA_FILE, "w", encoding="utf-8") as f:
		return json.load(f)

def sauvegarder_donnees(data):
	DATA_FILE.parent.mkdir(exist_ok=True)
	with open(DATA_FILE, "w", encoding="utf-8") as f:
		json.dump(data, f, indent=2, ensure_ascii=False)