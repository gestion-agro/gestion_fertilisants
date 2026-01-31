# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import pulp
import numpy as np
import cvxpy as cp
import math

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from utils.debug import debug

from ui.dialog_mode_calcul import ChoixModeCalcul

from tables.tables import aligner_table
from tables.remplissages import remplir_table_doses_ha

"""
calculer_doses
calcul_auto
calcul_strict
calculer_does_surface
"""

# Base pour envoyer vers calcul auto ou strict
# ----------------------
def calculer_doses(window):
    debug("\n=== calculer_doses ===")

    # Vérifier culture
    if not hasattr(window, "culture_active") or not window.culture_active:
        debug("⛔ Aucune culture active")
        QMessageBox.warning(window, "Erreur", "Aucune culture sélectionnée")
        return

    culture = window.cultures[window.culture_active]
    Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

    debug(
        f"Culture active : {window.culture_active}",
        f"Besoins → N={Nb} P={Pb} K={Kb}"
    )

    # --- Fertilisants table milieu ---
    ferts = []
    for row in range(window.table_utiliser.rowCount()):
        fert = {
            "nom": window.table_utiliser.item(row, 0).text(),
            "N": float(window.table_utiliser.item(row, 1).text()),
            "P": float(window.table_utiliser.item(row, 2).text()),
            "K": float(window.table_utiliser.item(row, 3).text())
        }
        ferts.append(fert)

    debug(f"Fertilisants table_utiliser ({len(ferts)}) :", ferts)

    window.table_doses_ha.setRowCount(0)
    window.table_doses_surface.setRowCount(0)

    # --- Choix du mode ---
    if not ferts:
        debug("➡️ Aucun fertilisant manuel → mode AUTO forcé")
        resultats = calcul_auto(window, Nb, Pb, Kb)
    else:
        dlg = ChoixModeCalcul(window)
        if dlg.exec() != QDialog.Accepted:
            debug("❌ Choix du mode annulé")
            return

        mode = dlg.mode
        debug("Mode choisi :", mode)

        if mode == "auto":
            resultats = calcul_auto(window, Nb, Pb, Kb)
            window.table_utiliser.setRowCount(0)
        else:
            resultats = calcul_strict(window, Nb, Pb, Kb, ferts)

    debug("Résultats calcul :", resultats)

    remplir_table_doses_ha(window, resultats["fertilisants"])
    calculer_doses_surface(window, resultats["fertilisants"], culture)
# ----------------------

def calcul_auto(window, Nb, Pb, Kb):
    debug("\n=== calcul_auto ===")

    window.fertilisants_autorises = []

    for row in range(window.table_fertilisants.rowCount()):
        cell_widget = window.table_fertilisants.cellWidget(row, 6)
        if not cell_widget:
            debug(f"⛔ Pas de widget checkbox ligne {row}")
            continue

        chk = cell_widget.layout().itemAt(0).widget()
        nom = window.table_fertilisants.item(row, 0).text()

        debug(f"Ligne {row} → {nom} | checked={chk.isChecked()}")

        if chk.isChecked():
            fert = next((f for f in window.fert_base if f["nom"] == nom), None)
            if not fert:
                debug("⛔ Fertilisant absent de fert_base :", nom)
                continue
            window.fertilisants_autorises.append(fert)

    debug(
        f"Fertilisants autorisés ({len(window.fertilisants_autorises)}) :",
        [f["nom"] for f in window.fertilisants_autorises]
    )

    if not window.fertilisants_autorises:
        debug("❌ Aucun fertilisant autorisé → abandon")
        return {"fertilisants": []}

    prob = pulp.LpProblem("Optimisation_Fertilisants", pulp.LpMinimize)

    noms = [f["nom"] for f in window.fertilisants_autorises]
    x = {nom: pulp.LpVariable(f"x_{nom}", cat="Binary") for nom in noms}
    y = {nom: pulp.LpVariable(f"y_{nom}", lowBound=0) for nom in noms}

    debug("Variables x :", list(x.keys()))
    debug("Variables y :", list(y.keys()))

    max_fertilisants = 4
    penalite_nb_fertilisants = 5
    M = 10000

    prob += (
        pulp.lpSum((y[f["nom"]] / f["conditionnement"]) * f["prix"]
                for f in window.fertilisants_autorises)
        + penalite_nb_fertilisants
        * pulp.lpSum(x[f["nom"]] for f in window.fertilisants_autorises)
    )

    debug("Objectif OK")

    prob += pulp.lpSum(y[f["nom"]] * f["N"] / 100 for f in window.fertilisants_autorises) == Nb
    prob += pulp.lpSum(y[f["nom"]] * f["P"] / 100 for f in window.fertilisants_autorises) == Pb
    prob += pulp.lpSum(y[f["nom"]] * f["K"] / 100 for f in window.fertilisants_autorises) == Kb

    debug("Contraintes NPK posées")

    for f in window.fertilisants_autorises:
        prob += y[f["nom"]] <= M * x[f["nom"]]
        debug(f"Lien x/y :", f["nom"])

    prob += pulp.lpSum(x[f["nom"]] for f in window.fertilisants_autorises) <= max_fertilisants
    debug("Limite nb fertilisants =", max_fertilisants)

    debug("=== Solveur CBC ===")
    prob.solve(pulp.PULP_CBC_CMD(msg=window.DEBUG))

    debug("Status solveur :", pulp.LpStatus[prob.status])

    fertilisants = []
    for f in window.fertilisants_autorises:
        dose = y[f["nom"]].value()
        debug(f"Résultat {f['nom']} → dose = {dose}")

        if dose and dose > 0.01:
            fertilisants.append({
                "nom": f["nom"],
                "doses_ha": round(dose, 1),
                "N": round(dose * f["N"] / 100, 1),
                "P": round(dose * f["P"] / 100, 1),
                "K": round(dose * f["K"] / 100, 1),
            })

    debug("Fertilisants FINALS :", [f["nom"] for f in fertilisants])
    return {"fertilisants": fertilisants}
# ----------------------

# Calcul strict
# ----------------------
def calcul_strict(window, Nb, Pb, Kb, ferts):
    debug("\n=== calcul_strict ===")

    debug("Besoins :", Nb, Pb, Kb)
    debug("Fertilisants :", ferts)

    if len(ferts) < 3:
        debug("⛔ Strict impossible (<3 fertilisants)")
        QMessageBox.warning(
            window, "Erreur",
            "Le mode strict nécessite au moins 3 fertilisants"
        )
        return {"fertilisants": []}

    A = np.array([
        [f["N"] / 100 for f in ferts],
        [f["P"] / 100 for f in ferts],
        [f["K"] / 100 for f in ferts],
    ])
    B = np.array([Nb, Pb, Kb])

    debug("Matrice A :", A)
    debug("Vecteur B :", B)

    doses, *_ = np.linalg.lstsq(A, B, rcond=None)
    debug("Doses brutes :", doses)

    resultats = []
    for dose, fert in zip(doses, ferts):
        dose = max(dose, 0)
        debug(f"{fert['nom']} → dose corrigée = {dose}")

        resultats.append({
            "nom": fert["nom"],
            "doses_ha": dose,
            "N": dose * fert["N"] / 100,
            "P": dose * fert["P"] / 100,
            "K": dose * fert["K"] / 100,
        })

    return {"fertilisants": resultats}
# ----------------------

# Remplissage des doses pour la surface dans table_doses_surface
# ----------------------
def calculer_doses_surface(window, resultats, culture):
    debug("\n=== calculer_doses_surface ===")
    surface = culture.get("surface", 1)
    debug(f"Surface culture = {surface} m²")

    window.table_doses_surface.setRowCount(0)
    total_prix = total_dose = 0        

    for r in resultats:
        dose_surface = r["doses_ha"] * surface / 10000
        fert = next((f for f in window.fert_base if f["nom"] == r["nom"]), None)

        if not fert:
            debug(f"⚠️ Fertilisant {r['nom']} introuvable dans fert_base")
            continue

        conditionnement = fert.get("conditionnement", 1)
        unite = fert.get("unite", "kg")
        prix_unitaire = fert.get("prix", 0)
        prix_kg = prix_unitaire / conditionnement
        prix_dose = prix_kg * dose_surface
        quantite = math.ceil(dose_surface / conditionnement) if conditionnement > 0 else 0
        prix_ht = quantite * prix_unitaire

        total_prix += prix_ht
        total_dose += prix_dose

        debug(f"{r['nom']} → dose_surface={dose_surface:.2f} {unite}, prix_dose={prix_dose:.2f}€, quantite={quantite}, prix_ht={prix_ht:.2f}€")

        row = window.table_doses_surface.rowCount()
        window.table_doses_surface.insertRow(row)
        window.table_doses_surface.setItem(row, 0, QTableWidgetItem(r["nom"]))
        window.table_doses_surface.setItem(row, 1, QTableWidgetItem(f"{dose_surface:.1f} {unite}"))
        window.table_doses_surface.setItem(row, 2, QTableWidgetItem(f"{prix_dose:.2f} €"))
        window.table_doses_surface.setItem(row, 3, QTableWidgetItem(f"{conditionnement} {unite}"))
        window.table_doses_surface.setItem(row, 4, QTableWidgetItem(f"{prix_unitaire:.2f} €"))
        window.table_doses_surface.setItem(row, 5, QTableWidgetItem(str(quantite)))
        window.table_doses_surface.setItem(row, 6, QTableWidgetItem(f"{prix_ht:.2f} €"))

    # Ligne TOTAL
    row = window.table_doses_surface.rowCount()
    window.table_doses_surface.insertRow(row)
    debug(f"Ligne TOTAL → total_dose={total_dose:.2f}€, total_prix={total_prix:.2f}€")

    window.table_doses_surface.setItem(row, 0, QTableWidgetItem("TOTAL"))
    window.table_doses_surface.setItem(row, 1, QTableWidgetItem())
    window.table_doses_surface.setItem(row, 2, QTableWidgetItem(f"{total_dose:.2f} €"))
    window.table_doses_surface.setItem(row, 3, QTableWidgetItem())
    window.table_doses_surface.setItem(row, 4, QTableWidgetItem())
    window.table_doses_surface.setItem(row, 5, QTableWidgetItem())
    window.table_doses_surface.setItem(row, 6, QTableWidgetItem(f"{total_prix:.2f} €"))

    font = QFont()
    font.setBold(True)
    for col in range(window.table_doses_surface.columnCount()):
        item = window.table_doses_surface.item(row, col)
        if item:
            item.setFont(font)
            item.setBackground(QBrush(QColor("#e6e6e6")))

    window.table_doses_surface.setRowHeight(row, 32)
    aligner_table(window.table_doses_surface, "table_doses_surface")
# ----------------------