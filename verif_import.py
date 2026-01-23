import os
import re
from pathlib import Path

# Dossier racine du projet
ROOT_DIR = Path(".").resolve()

# Extensions à scanner
EXT = ".py"

# Exclure certains dossiers
EXCLUDE_DIRS = {"venv", "__pycache__"}

# Récupérer tous les fichiers .py
all_py_files = []
for root, dirs, files in os.walk(ROOT_DIR):
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    for f in files:
        if f.endswith(EXT):
            full_path = os.path.join(root, f)
            all_py_files.append(os.path.relpath(full_path, ROOT_DIR))

# Construire un set des modules importés
imported_modules = set()
import_pattern = re.compile(r"^\s*(?:from\s+(\S+)|import\s+(\S+))")

for py_file in all_py_files:
    with open(py_file, "r", encoding="utf-8") as f:
        for line in f:
            match = import_pattern.match(line)
            if match:
                mod1, mod2 = match.groups()
                if mod1:
                    imported_modules.add(mod1.split(".")[0])
                elif mod2:
                    imported_modules.add(mod2.split(",")[0].strip().split(".")[0])

# Comparer avec les fichiers du projet
unused_files = []
for py_file in all_py_files:
    name = os.path.splitext(os.path.basename(py_file))[0]
    if name not in imported_modules and name != "app":  # on garde app.py
        unused_files.append(py_file)

print("Fichiers potentiellement inutilisés :")
for f in unused_files:
    print(f)
