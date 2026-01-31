# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from utils.debug import debug

from logic.calculs import calculer_doses_surface

from tables.remplissages import remplir_tableaux

from paths import FERT_FILE, CULTURE_FILE

import json

"""
charger_fertilisants
charger_cultures
recharger_cultures
recharger_fertilisants
charger_ferts_pour_culture
"""

# ----------------------
# Charger les fertilisants
def charger_fertilisants(window):
    debug("=== charger_fertilisants ===")
    debug("=== Fichier :", FERT_FILE)
    
    try:
        with open(FERT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            if not isinstance(data, list):
                debug("⚠️ Données invalides : pas une liste → reset []")
                data = []

            debug(f"{len(data)} fertiliant(s) chergé(s) depuis le fichiers")

            # S'assurer que chaque élément est bien un dict avec les champs nécessaire
            for i, fert in enumerate(data):
                if not isinstance(fert, dict):
                    debug(f"⛔ Élément {i} ignoré (pas un dict)")
                    continue # Ignorer si ce n'est pas le cas

                fert.setdefault("stock", 0)
                fert.setdefault("unite", "kg")
                fert.setdefault("N", 0)
                fert.setdefault("P", 0)
                fert.setdefault("K", 0)
                fert.setdefault("conditionnement", 1)
                fert.setdefault("prix", 0)

                debug(
                    f"✔ Fertilisant {i} :",
                    fert.get("nom", "<sans nom>"),
                    f"NPK=({fert['N']},{fert['P']},{fert['K']})",
                    f"prix={fert['prix']}",
                    f"cond={fert['conditionnement']}"
                )

            return data
    except FileNotFoundError:
        debug("❌ Fichier fertilisants introuvable")
        return []
    
    except json.JSONDecodeError as e:
        debug("❌ Erreur JSON :", e)
        return
# ----------------------

# ----------------------
# Charger les cultures
def charger_cultures(window):
    debug("=== charger_cultures ===")
    debug("Fichiers :", CULTURE_FILE)

    try:
        with open(CULTURE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            if not isinstance(data, dict):
                debug("⚠️ Données invalides : pas un dict → reset {}")
                data = {}

            debug(f"{len(data)} culture(s) chargée(s)")

            for nom, culture in data.items():
                debug(
                    f"✔ Culture : {nom}",
                    f"N={culture.get('N', 0)}",
                    f"P={culture.get('P', 0)}",
                    f"K={culture.get('K', 0)}",
                    f"surface={culture.get('surface', '?')}"
                )

            return data
        
    except FileNotFoundError:
        debug("❌ Fichier fertilisants introuvable")
        return {}
    
    except json.JSONDecodeError as e:
        debug("❌ Erreur JSON :", e)
        return {}
# ----------------------

# ----------------------
# Recharger les cultures
def recharger_cultures(window):
    debug("=== recharger_cultures ===")

    window.cultures = charger_cultures(window)
    debug(f"{len(window.cultures)} culture(s) apres rechargement")

    remplir_tableaux(window)
    debug("Tableaux rafraîchis (cultures)")
# ----------------------

# ----------------------
# Recharger les fertilisants
def recharger_fertilisants(window):
    debug("=== recharger_fertilisants ===")

    window.fert_base = charger_fertilisants(window)
    debug(f"{len(window.fert_base)} fertilisant(s) après rechargement")

    remplir_tableaux(window)
    debug("Tableau rafraîchis (fertilisants)")
# ----------------------

# ----------------------
# Charger les fertilisants de la culture selectionnée
def charger_ferts_pour_culture(window, nom_culture):
    debug("\n=== charger_ferts_pour_culture ===")
    debug("Culture demandée :", nom_culture)

    culture = window.cultures.get(nom_culture)
    if not culture:
        debug("⛔ Culture introuvable")
        window.table_utiliser.setRowCount(0)
        return

    window.table_utiliser.setRowCount(0)
    window.table_doses_ha.setRowCount(0)
    window.table_doses_surface.setRowCount(0)

    ferts_utilises = culture.get("fertilisants_utilises", [])
    debug("Fertilisants culture :", ferts_utilises)

    for f in ferts_utilises:
        nom = f["nom"]
        fert_base = next((fb for fb in window.fert_base if fb["nom"] == nom), None)
        if not fert_base:
            debug("⛔ Fertilisant manquant dans base :", nom)
            continue

        row = window.table_utiliser.rowCount()
        window.table_utiliser.insertRow(row)

        window.table_utiliser.setItem(row, 0, QTableWidgetItem(nom))
        window.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
        window.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
        window.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
        window.table_utiliser.setItem(row, 4, QTableWidgetItem(str(f.get("doses_ha", 0))))

        debug(f"➕ table_utiliser ← {nom}")

    for f in ferts_utilises:
        nom = f["nom"]
        doses_ha = f.get("doses_ha", 0)
        fert_base = next((fb for fb in window.fert_base if fb["nom"] == nom), None)
        if not fert_base:
            continue

        N = doses_ha * fert_base.get("N", 0) / 100
        P = doses_ha * fert_base.get("P", 0) / 100
        K = doses_ha * fert_base.get("K", 0) / 100

        row = window.table_doses_ha.rowCount()
        window.table_doses_ha.insertRow(row)

        window.table_doses_ha.setItem(row, 0, QTableWidgetItem(nom))
        window.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{N:.1f}"))
        window.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{P:.1f}"))
        window.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{K:.1f}"))
        window.table_doses_ha.setItem(row, 4, QTableWidgetItem(f"{doses_ha:.1f}"))

        debug(f"📊 table_doses_ha ← {nom}")

    calculer_doses_surface(
        window,
        [
            {
                "nom": f["nom"],
                "doses_ha": f.get("doses_ha", 0),
                "N": window.table_doses_ha.item(i, 1).text(),
                "P": window.table_doses_ha.item(i, 2).text(),
                "K": window.table_doses_ha.item(i, 3).text(),
            }
            for i, f in enumerate(ferts_utilises)
        ],
        culture
    )

    debug("📐 Doses surface recalculées")
# ----------------------