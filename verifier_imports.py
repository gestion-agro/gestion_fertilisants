#!/usr/bin/env python3
"""
Script de vérification rapide de tout le projet :
1. Syntaxe Python valide (ast.parse) sur chaque fichier .py
2. Import réel de chaque module (détecte ImportError, NameError au
   chargement, fonctions/symboles manquants entre fichiers)

USAGE :
    cd ~/Bureau/gestion_fertilisants
    python3 verifier_imports.py

Affiche un rapport coloré : ✅ OK / ❌ ERREUR avec le détail.
Code de sortie 0 si tout est bon, 1 sinon (utile pour un script CI/pre-commit).
"""

import ast
import sys
import os
import importlib
import traceback
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Dossiers à ignorer
IGNORER = {"venv", "ancien", "__pycache__", ".git", "build", "dist"}

VERT = "\033[92m"
ROUGE = "\033[91m"
JAUNE = "\033[93m"
RESET = "\033[0m"


def trouver_fichiers_py() -> list[Path]:
    fichiers = []
    for path in ROOT.rglob("*.py"):
        if any(part in IGNORER for part in path.parts):
            continue
        fichiers.append(path)
    return sorted(fichiers)


def verifier_syntaxe(fichier: Path) -> tuple[bool, str]:
    """Étape 1 : le fichier est-il du Python valide ?"""
    try:
        source = fichier.read_text(encoding="utf-8")
        ast.parse(source, filename=str(fichier))
        return True, ""
    except SyntaxError as e:
        return False, f"Ligne {e.lineno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def chemin_vers_module(fichier: Path) -> str:
    """Convertit un chemin de fichier en nom de module importable."""
    rel = fichier.relative_to(ROOT)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def verifier_import(module_name: str) -> tuple[bool, str]:
    """Étape 2 : le module s'importe-t-il réellement (sans erreur) ?"""
    try:
        if module_name in sys.modules:
            del sys.modules[module_name]
        importlib.import_module(module_name)
        return True, ""
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        return False, f"{type(e).__name__}: {e}\n{tb}"


def main():
    sys.path.insert(0, str(ROOT))

    fichiers = trouver_fichiers_py()
    print(f"📂 {len(fichiers)} fichier(s) Python trouvé(s) dans {ROOT}\n")

    erreurs_syntaxe = []
    erreurs_import = []
    ok_count = 0

    for fichier in fichiers:
        rel = fichier.relative_to(ROOT)

        # Étape 1 : syntaxe
        syntaxe_ok, msg_syntaxe = verifier_syntaxe(fichier)
        if not syntaxe_ok:
            print(f"{ROUGE}❌ SYNTAXE  {rel}{RESET}")
            print(f"   {msg_syntaxe}")
            erreurs_syntaxe.append((rel, msg_syntaxe))
            continue  # pas la peine d'essayer l'import

        # Fichiers d'entrée connus pour avoir des effets de bord lourds
        # (lancent l'app, ouvrent des fenêtres, MODIFIENT LA BASE) — on
        # les skip à l'import mais on garde la vérif syntaxe.
        # ⚠️ Tout script de migration/reconstruction de BDD doit être
        # ajouté ici : son simple import ne doit jamais être exécuté.
        FICHIERS_A_RISQUE = {
            "app.py",
            "reconstruction.py",
            "reconstruire_db.py",
        }
        if rel.name in FICHIERS_A_RISQUE:
            print(f"{JAUNE}⏭️  SKIP IMPORT (effets de bord / risque BDD) {rel}{RESET}")
            ok_count += 1
            continue

        # Étape 2 : import réel
        module_name = chemin_vers_module(fichier)
        import_ok, msg_import = verifier_import(module_name)
        if not import_ok:
            print(f"{ROUGE}❌ IMPORT   {rel}  (module: {module_name}){RESET}")
            print(f"   {msg_import}")
            erreurs_import.append((rel, msg_import))
        else:
            print(f"{VERT}✅ OK       {rel}{RESET}")
            ok_count += 1

    print("\n" + "=" * 60)
    print(f"Résumé : {ok_count}/{len(fichiers)} fichier(s) OK")
    if erreurs_syntaxe:
        print(f"{ROUGE}{len(erreurs_syntaxe)} erreur(s) de SYNTAXE{RESET}")
    if erreurs_import:
        print(f"{ROUGE}{len(erreurs_import)} erreur(s) d'IMPORT{RESET}")

    if erreurs_syntaxe or erreurs_import:
        print(f"\n{ROUGE}❌ DES ERREURS ONT ÉTÉ TROUVÉES{RESET}")
        sys.exit(1)
    else:
        print(f"\n{VERT}✅ TOUT EST BON{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
