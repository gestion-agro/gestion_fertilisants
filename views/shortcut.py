# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug

from logic.enregistrement import enregistrer_doses_culture
from logic.calculs import calcul_auto, calcul_strict, calculer_doses_surface

from views.culture import ajout_culture, supprimer_culture
from views.fertilisants import ajout_fert, supprimer_fert
from views.fertilisants_utilises import enlever_fert_utiliser
from views.dialogs import redemarrer_debug

from tables.remplissages import remplir_table_doses_ha

"""
init_raccourcis
suppr
_nom_selectionnes
calcul_auto_clavier
calcul_strict_clavier
"""

def init_raccourcis(window):
    """
    Initialis tous les raccourcis clavier de l'application
    window = instance de MainWindow
    """

    debug.debug("Initialisation des raccourcis clavier")

    # Sauvegarde
    QShortcut(
        QKeySequence("Ctrl+S"),
        window
    ).activated.connect(
        lambda: enregistrer_doses_culture(window, True)
    )

    # Nouveau fertilisant
    QShortcut(
        QKeySequence("Ctrl+F"),
        window
    ).activated.connect(
        lambda: ajout_fert(window, clavier=True)
    )

    # Nouvelle culture
    QShortcut(
        QKeySequence("Ctrl+C"),
        window
    ).activated.connect(
        lambda: ajout_culture(window, clavier=True)
    )

    # Debug
    QShortcut(
        QKeySequence("Ctrl+D"),
        window
    ).activated.connect(
        lambda: redemarrer_debug(window, clavier=True)
    )

    # Supprimer ligne
    QShortcut(
        QKeySequence.Delete,
        window
    ).activated.connect(
        lambda: suppr(window)
    )

    # Calculer doses (strict)
    QShortcut(
        QKeySequence("Ctrl+Shift+A"),
        window
    ).activated.connect(
        lambda: calcul_strict_clavier(window)
    )

    # Calculer doses (auto)
    QShortcut(
        QKeySequence("Ctrl+A"),
        window
    ).activated.connect(
        lambda: calcul_auto_clavier(window)
    )

# Interception touche suppr
# ----------------------
def suppr(window):
    widget = QApplication.focusWidget()

    if widget is None:
        debug.debug("Pas de sélection")
        return
    
    # Cultures
    # ======================
    if widget == window.table_cultures:
        nom = _nom_selectionnes(window, window.table_cultures)
        if nom:
            debug.debug("Suppression de la culture", nom)
            supprimer_culture(window, nom)
        return
    # ======================

    # Fertilisant (base)
    # ======================
    if widget == window.table_fertilisants:
        nom = _nom_selectionnes(window, window.table_fertilisants)
        if nom:
            debug.debug("Suppression du fertilisant", nom)
            supprimer_fert(window, nom)
        return
    # ======================
    
    # Fertilisant utilisé
    # ======================
    if widget == window.table_utiliser:
        nom = _nom_selectionnes(window, window.table_utiliser)
        if nom:
            debug.debug(
                f"Suppression pour la cuture de",
                f"'{window.culture_active}' :",
                nom
            )
            enlever_fert_utiliser(window, nom)
        return
    # ======================
# ----------------------

# Récuperer nom premiere colone d'une lign d'un tableau
# ----------------------
def _nom_selectionnes(window, table):
    row = table.currentRow()
    if row < 0:
        return None
    
    item = table.item(row, 0)
    return item.text() if item else None
# ----------------------

# Raccourcis clavier pour renvoyer vers calcul auto
# ----------------------
def calcul_auto_clavier(window):
    debug.debug("Raccourcis clavier pour calcul auto des doses")
    # Vérifier culture
    if not hasattr(window, "culture_active") or not window.culture_active:
        debug.debug("⛔ Aucune culture active")
        QMessageBox.warning(window, "Erreur", "Aucune culture sélectionnée")
        return

    culture = window.cultures[window.culture_active]
    Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

    debug.debug(
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

    debug.debug(f"Fertilisants table_utiliser ({len(ferts)}) :", ferts)

    window.table_doses_ha.setRowCount(0)
    window.table_doses_surface.setRowCount(0)
    window.table_utiliser.setRowCount(0)
    
    resultats = calcul_auto(window, Nb, Pb, Kb)

    debug.debug("Résultats calcul :", resultats)

    remplir_table_doses_ha(window, resultats["fertilisants"])
    calculer_doses_surface(window, resultats["fertilisants"], culture)
# ----------------------

# Raccourcis clavier pour renvoyer vers calcul strict
# ----------------------
def calcul_strict_clavier(window):
    debug.debug("Raccourcis clavier pour calcul strict des doses")

    # Vérifier culture
    if not hasattr(window, "culture_active") or not window.culture_active:
        debug.debug("⛔ Aucune culture active")
        QMessageBox.warning(window, "Erreur", "Aucune culture sélectionnée")
        return

    culture = window.cultures[window.culture_active]
    Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

    debug.debug(
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

    debug.debug(f"Fertilisants table_utiliser ({len(ferts)}) :", ferts)

    # --- Choix du mode ---
    if not ferts:
        debug.debug("➡️ Aucun fertilisant manuel")
        QMessageBox.warning(
            window,
            "Aucun fertiliants",
            "Aucun fertilisans chargé pour la culture impossible de faire le calcul."
        )
        return
    else:
        resultats = calcul_strict(window, Nb, Pb, Kb, ferts)

    debug.debug("Résultats calcul :", resultats)

    window.table_doses_ha.setRowCount(0)
    window.table_doses_surface.setRowCount(0)

    remplir_table_doses_ha(window, resultats["fertilisants"])
    calculer_doses_surface(window, resultats["fertilisants"], culture)
# ----------------------