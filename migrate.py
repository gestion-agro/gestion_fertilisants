# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX
#
# Script de migration one-shot : JSON -> SQLite
# Lancer UNE SEULE FOIS depuis la racine du projet :
#   python3 migrate.py
# ─────────────────────────────────────────────

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import init_db, get_connection

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

CULTURES_FILE     = os.path.join(DATA_DIR, "culture.json")
FERTILISANTS_FILE = os.path.join(DATA_DIR, "fertilisants.json")


def migrate_cultures(cur):
    with open(CULTURES_FILE, encoding="utf-8") as f:
        cultures = json.load(f)

    count = 0
    for nom, data in cultures.items():
        cur.execute("""
            INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k, surface)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(nom) DO UPDATE SET
                besoin_n = excluded.besoin_n,
                besoin_p = excluded.besoin_p,
                besoin_k = excluded.besoin_k,
                surface  = excluded.surface
        """, (
            nom,
            data.get("N", 0),
            data.get("P", 0),
            data.get("K", 0),
            data.get("surface", 10000),
        ))
        count += 1

    print(f"  OK {count} culture(s) migree(s)")


def migrate_fertilisants(cur):
    with open(FERTILISANTS_FILE, encoding="utf-8") as f:
        fertilisants = json.load(f)

    count = 0
    for fert in fertilisants:
        cur.execute("""
            INSERT INTO fertilisants (nom, n, p, k, conditionnement, unite, prix, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nom) DO UPDATE SET
                n               = excluded.n,
                p               = excluded.p,
                k               = excluded.k,
                conditionnement = excluded.conditionnement,
                unite           = excluded.unite,
                prix            = excluded.prix,
                stock           = excluded.stock
        """, (
            fert.get("nom"),
            fert.get("N", 0),
            fert.get("P", 0),
            fert.get("K", 0),
            fert.get("conditionnement", 25),
            fert.get("unite", "kg"),
            fert.get("prix", 0),
            fert.get("stock", 0),
        ))
        count += 1

    print(f"  OK {count} fertilisant(s) migre(s)")


def main():
    print("=== Migration JSON -> SQLite ===")
    print("Initialisation de la base de donnees...")
    init_db()

    conn = get_connection()
    cur = conn.cursor()

    print("\nMigration des cultures...")
    migrate_cultures(cur)

    print("Migration des fertilisants...")
    migrate_fertilisants(cur)

    conn.commit()
    cur.close()
    

    print("\nOK Migration terminee avec succes.")
    print("Vous pouvez maintenant archiver les fichiers JSON.")


if __name__ == "__main__":
    main()