#!/usr/bin/env python3
"""
Smoke-test UI : lance l'application avec une base de données TEMPORAIRE
(jamais ta vraie base) et navigue automatiquement sur chaque page pour
vérifier qu'aucune ne lève d'exception au chargement.

⚠️ SÉCURITÉ : ce script redirige db.DB_FILE vers un fichier temporaire
   AVANT tout import de pages, donc il ne touche jamais
   ~/.GestionFertilisants/gestion.db. Vérifié par une assertion explicite.

USAGE :
    cd ~/Bureau/gestion_fertilisants
    python3 smoke_test_ui.py

Ferme automatiquement après le test (pas besoin d'interaction).
Code de sortie 0 si toutes les pages s'affichent sans erreur, 1 sinon.
"""

import sys
import os
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Sécurité : rediriger la BDD vers un fichier temporaire AVANT tout ──
TEMP_DB = os.path.join(tempfile.gettempdir(), "smoke_test_gestion.db")
if os.path.exists(TEMP_DB):
    os.remove(TEMP_DB)

import db
db.DB_FILE = TEMP_DB
db._conn = None  # force une nouvelle connexion vers le fichier temp

assert db.DB_FILE != os.path.expanduser("~/.GestionFertilisants/gestion.db"), \
    "🛑 ARRÊT : le script pointe vers la vraie base, refus de continuer."
print(f"✅ BDD de test isolée : {db.DB_FILE}")

db.init_db()

# ── Création d'un jeu de données minimal pour que les pages aient
#    quelque chose à afficher sans planter sur des listes vides ──
conn = db.get_connection()
cur = conn.cursor()
cur.execute("""
    INSERT INTO users (id, nom, prenom, username, password_hash, role)
    VALUES (1, 'Test', 'Smoke', 'smoke.test', 'x', 'admin')
""")
cur.execute("""
    INSERT INTO entreprise (id, nom, has_ruches) VALUES (1, 'Ferme Test', 1)
""")
cur.execute("INSERT INTO parcelles (nom, surface_ha) VALUES ('Parcelle Test', 1.0)")
pid = cur.lastrowid
cur.execute("""
    INSERT INTO cultures_parcelle (parcelle_id, categorie, espece)
    VALUES (?, 'maraichage', 'Tomate')
""", (pid,))
cur.execute("INSERT INTO ruches (nom, parcelle_id) VALUES ('Ruche1', ?)", (pid,))
cur.execute("INSERT INTO fertilisants (nom, n, p, k) VALUES ('Ferti Test', 10, 5, 5)")
conn.commit()
cur.close()
print("✅ Jeu de données minimal créé en mémoire/temp")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)

CURRENT_USER = {"id": 1, "nom": "Test", "prenom": "Smoke",
                "role": "admin", "certiphyto_type": "CON"}

VERT = "\033[92m"
ROUGE = "\033[91m"
RESET = "\033[0m"

resultats = []


def tester_page(nom_page, fabrique):
    """Instancie une page et capture toute exception au chargement."""
    try:
        widget = fabrique()
        resultats.append((nom_page, True, ""))
        print(f"{VERT}✅ {nom_page}{RESET}")
        return widget
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        resultats.append((nom_page, False, msg))
        print(f"{ROUGE}❌ {nom_page}{RESET}")
        print(f"   {msg}")
        traceback.print_exc(limit=3)
        return None


def main():
    print("\n--- Test des pages individuelles ---\n")

    from exploit.exploit import ExploitPage
    tester_page("ExploitPage", lambda: ExploitPage(current_user=CURRENT_USER))

    from parcelles.parcelles import ParcellePage
    tester_page("ParcellePage", lambda: ParcellePage(current_user=CURRENT_USER))

    from irrigation.irrigation import IrrigationPage
    tester_page("IrrigationPage", lambda: IrrigationPage(current_user=CURRENT_USER))

    from ruches.ruches import RuchesPage
    tester_page("RuchesPage", lambda: RuchesPage(current_user=CURRENT_USER))

    from ppp.catalogue import CataloguePPP
    tester_page("CataloguePPP", lambda: CataloguePPP())

    from ppp.aide_decision import AideDecision
    tester_page("AideDecision (PPP)", lambda: AideDecision(current_user=CURRENT_USER))

    from ppp.carnet import CarnetPage
    tester_page("CarnetPage (PPP)", lambda: CarnetPage(current_user=CURRENT_USER))

    from fertilisants.catalogue import CatalogueFertilisants
    tester_page("CatalogueFertilisants",
                lambda: CatalogueFertilisants(current_user=CURRENT_USER))

    from fertilisants.aide_decision import AideDecisionFerti
    tester_page("AideDecisionFerti",
                lambda: AideDecisionFerti(current_user=CURRENT_USER))

    from fertilisants.carnet import CarnetFertilisation
    tester_page("CarnetFertilisation",
                lambda: CarnetFertilisation(current_user=CURRENT_USER))

    from admin.admin import AdminPage
    tester_page("AdminPage", lambda: AdminPage(current_user=CURRENT_USER))

    from views.parametres import ParametresPage
    tester_page("ParametresPage", lambda: ParametresPage(current_user=CURRENT_USER))

    print("\n--- Test de la fenêtre principale complète ---\n")
    from views.main_window import MainWindow
    tester_page("MainWindow (complète)",
                lambda: MainWindow(current_user=CURRENT_USER))

    # ── Rapport final ──
    print("\n" + "=" * 60)
    ok = sum(1 for _, success, _ in resultats if success)
    total = len(resultats)
    print(f"Résumé : {ok}/{total} page(s) chargée(s) sans erreur")

    echecs = [r for r in resultats if not r[1]]
    if echecs:
        print(f"\n{ROUGE}❌ ÉCHECS :{RESET}")
        for nom, _, msg in echecs:
            print(f"  - {nom}: {msg}")
        app.exit(1)
    else:
        print(f"\n{VERT}✅ TOUTES LES PAGES SE CHARGENT SANS ERREUR{RESET}")
        app.exit(0)


QTimer.singleShot(100, main)
exit_code = app.exec()

# Nettoyage
if os.path.exists(TEMP_DB):
    os.remove(TEMP_DB)

sys.exit(exit_code)
