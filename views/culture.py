# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug


from ui.ajouter_culture import AjouterCultureWindow

from logic.chargement import recharger_cultures, charger_ferts_pour_culture
from logic.enregistrement import enregistrer_doses_culture
from logic.calculs import calculer_doses_surface

from tables.remplissages import remplir_tableaux, remplir_table_doses_ha
from tables.tables import aligner_table

from views.fertilisants_utilises import mark_doses_modifiees


""" 
ajout_culture
modifier_culture
supprimer_culture
culture_selectionne_changed
"""

# ----------------------
# Ajouter une culture
def ajout_culture(window, culture=None, clavier=False):
    debug.debug("=== ajout_culture ===")

    if clavier:
        debug.debug("Depuis raccourcis clavier")
        
    debug.debug("Culture passée :", culture)

    window.ajout_window = AjouterCultureWindow(culture)

    # Connecter le signal pour recharger les fertiliants
    window.ajout_window.culture_ajoute.connect(
        lambda : recharger_cultures(window)
    )
    debug.debug("Signel culture_ajoute connecté → recharger_cultures")

    window.ajout_window.show()
    debug.debug("Fenêtre AjouterCultureWindow affiché")
# ----------------------

# ----------------------
# Modifier une culture
def modifier_culture(window, nom):
    culture = window.cultures.get(nom)
    if not culture:
        return
    culture_complet = culture.copy()
    culture_complet["nom"] = nom
    ajout_culture(window, culture_complet)
# ----------------------

# ----------------------
# Supprimer une culture
def supprimer_culture(window, nom):
    from db import get_connection
    from logic.enregistrement import supprimer_culture as supprimer_culture_db
    import traceback
 
    debug.debug("=== supprimer_culture ===")
    culture = window.cultures.get(nom)
    if not culture:
        debug.debug("⛔ Culture introuvable")
        return
 
    reply = QMessageBox.question(
        window, "Confirmation",
        f"Voulez-vous vraiment supprimer la culture « {nom} » ?",
        QMessageBox.Yes | QMessageBox.No)
    if reply != QMessageBox.Yes:
        return
 
    supprimer_culture_db(window, nom)
    debug.debug(f"[culture] '{nom}' supprimée de la BDD")
# ----------------------

# Ne pas autoriser sans validations de l'utilisateur le changement de culture sans enregistrement
# ----------------------
def culture_selectionnee_changed(window, row, column):
    debug.debug("\n=== culture_selectionnee_changed ===")

    row = window.table_cultures.currentRow()
    debug.debug("Ligne sélectionnée :", row)

    if row < 0:
        debug.debug("⛔ Aucune ligne sélectionnée")
        return

    item = window.table_cultures.item(row, 0)
    if not item:
        debug.debug("⛔ Item culture inexistant")
        return

    nom_culture = item.text()
    debug.debug("Culture cliquée :", nom_culture)
    debug.debug("Culture active actuelle :", window.culture_active)

    if window.culture_active == nom_culture:
        debug.debug("↩️ Même culture → aucun changement")
        return

    # --- Vérification modifications non enregistrées ---
    if window.culture_active and window.table_modifiees:
        debug.debug("⚠️ Doses modifiées détectées pour :", window.culture_active)

        reply = QMessageBox.question(
            window,
            "Changement de culture",
            "Voulez-vous quitter sans enregistrer ?",
            QMessageBox.Yes | QMessageBox.Save | QMessageBox.Cancel
        )

        debug.debug(
            "Choix utilisateur :",
            "Cancel" if reply == QMessageBox.Cancel else
            "Save" if reply == QMessageBox.Save else
            "Yes"
        )

        if reply == QMessageBox.Cancel:
            debug.debug("❌ Changement de culture annulé")
            return

        if reply == QMessageBox.Save:
            debug.debug("💾 Enregistrement des doses avant changement")
            enregistrer_doses_culture(window)
            window.table_modifiees = False

    # --- Reset style lignes ---
    for r in range(window.table_cultures.rowCount()):
        it = window.table_cultures.item(r, 0)
        if it:
            font = it.font()
            font.setBold(False)
            it.setFont(font)

    # --- Mise en gras sélection ---
    font = item.font()
    font.setBold(True)
    item.setFont(font)

    window.culture_active = nom_culture
    debug.debug("✅ Nouvelle culture active :", window.culture_active)

    culture = window.cultures.get(nom_culture, {})
    surface = culture.get("surface", 0)
    debug.debug("Surface culture :", surface)

    window.lbl_culture_active.setText(nom_culture)
    window.lbl_dose_surface.setText(f"Doses pour la surface ({surface} m²)")
    window.table_cultures.selectRow(row)

    # --- Chargement fertilisants utilisés ---
    window.table_utiliser.setRowCount(0)
    ferts_utilises = culture.get("fertilisants_utilises", [])
    debug.debug("Fertilisants utilisés enregistrés :", ferts_utilises)

    if ferts_utilises:
        has_doses = any(f.get("doses_ha") is not None for f in ferts_utilises)
        
        if has_doses:
            resultats = []
            for fert in ferts_utilises:
                fert_base = next((f for f in window.fert_base if f["nom"] == fert["nom"]), {})
                doses_ha = fert.get("doses_ha", 0)

                N = doses_ha * fert_base.get("N", 0) / 100
                P = doses_ha * fert_base.get("P", 0) / 100
                K = doses_ha * fert_base.get("K", 0) / 100

                resultats.append({
                    "nom": fert["nom"],
                    "doses_ha": doses_ha,
                    "N": N,
                    "P": P,
                    "K": K
                })

                debug.debug(f"🧮 {fert['nom']} → N:{N} P:{P} K:{K}")

            window.table_doses_ha.setRowCount(0)
            window.table_doses_surface.setRowCount(0)

            remplir_table_doses_ha(window, resultats)
            calculer_doses_surface(window, resultats, culture)

            window.table_modifiees = False
            debug.debug("🔁 Flag table_modifiees réinitialisé")
            
            debug.debug("Suppression de l'affiche de lbl_modifie")
            mark_doses_modifiees(window, False)
            
        else:
            window.table_doses_ha.setRowCount(0)
            window.table_doses_surface.setRowCount(0)

            for fert in ferts_utilises:
                fert_base = next((f for f in window.fert_base if f["nom"] == fert["nom"]), None)
                if not fert_base:
                    debug.debug("⛔ Fertilisant introuvable dans base :", fert["nom"])
                    continue

                row_util = window.table_utiliser.rowCount()
                window.table_utiliser.insertRow(row_util)

                window.table_utiliser.setItem(row_util, 0, QTableWidgetItem(fert["nom"]))
                window.table_utiliser.setItem(row_util, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
                window.table_utiliser.setItem(row_util, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
                window.table_utiliser.setItem(row_util, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
                window.table_utiliser.setItem(row_util, 4, QTableWidgetItem(str(fert.get("doses_ha", 0))))

                debug.debug(f"➕ Fertilisant chargé : {fert['nom']} (ligne {row_util})")

            aligner_table(window.table_utiliser, "table_utiliser")
            
            debug.debug("Suppression de l'affiche de lbl_modifie")
            mark_doses_modifiees(window, False)
            
    else:
        debug.debug("ℹ️ Aucun fertilisant enregistré → chargement par défaut")
        charger_ferts_pour_culture(window, nom_culture)

    

    remplir_tableaux(window)

    # --- Calcul doses ---
# ----------------------