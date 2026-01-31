# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from utils.debug import debug

from paths import FERT_FILE

from ui.ajouter_fertilisant import AjouterFertilisantWindow

from logic.chargement import recharger_fertilisants

from tables.remplissages import remplir_tableaux

from views.fertilisants_utilises import ajouter_fert_utiliser, mark_doses_modifiees

import json

""" 
ajout_fert
modifier_fert
supprimer_fert
double_clic_fertilisant
"""

# ----------------------
# Ajouter un fertiliant
def ajout_fert(window, fert=None, clavier=False):
    debug("=== ajout_fert ===")

    if clavier:
        debug("Depuis raccourcis clavier")
    else:
        debug("Depuis bouton")
        
    debug("Fertilisant passée :", fert)

    window.ajout_window = AjouterFertilisantWindow(fert)

    # Connecter le signal pour recharger les fertiliants
    window.ajout_window.fertilisant_ajoute.connect(
        lambda : recharger_fertilisants(window)
    )
    debug("Signal fertilisant_ajoute connecté → recharger_fertilisant")

    window.ajout_window.show()
    debug("Fenêtre AjouterFertilisantWindow affichée")
# ----------------------

# ----------------------
# Modifier un fertilisant
def modifier_fert(window, nom):
    debug("=== modifier_fert ===")
    debug("Fertilisant demandé :", nom)

    fert = next((f for f in window.fert_base if f["nom"] == nom), None)
    if not fert:
        debug("⛔ Fertilisant introuvable")
        return

    debug("Ouverture fenêtre modification fertilisant")
    ajout_fert(window, fert)
# ----------------------

# ----------------------
# Supprimer un fertiliant
def supprimer_fert(window, nom):
    debug("=== supprimer_fert ===")
    debug("Fertilisant demandé :", nom)

    fert = next((f for f in window.fert_base if f["nom"] == nom), None)
    if not fert:
        debug("⛔ Fertilisant introuvable")
        return

    reply = QMessageBox.question(
        window,
        "Confirmation",
        f"Voulez-vous vraiment supprimer le fertilisant « {nom} » ?",
        QMessageBox.Yes | QMessageBox.No
    )

    debug("Réponse utilisateur :", "Oui" if reply == QMessageBox.Yes else "Non")

    if reply != QMessageBox.Yes:
        debug("Suppression annulée")
        return

    window.fert_base = [f for f in window.fert_base if f["nom"] != nom]
    debug("Fertilisant supprimé de la mémoire")

    with open(FERT_FILE, "w", encoding="utf-8") as f:
        json.dump(window.fert_base, f, indent=2, ensure_ascii=False)
        debug("Fichier fertilisants réécrit")

    remplir_tableaux(window)
    debug("Tableaux rafraîchis après suppression fertilisant")
# ----------------------

# Au double clique d'un fertilisant dans table_fertilisants -> ajout dans table_utilise
# ----------------------
def double_clic_fertilisant(window, row, column):
    item = window.table_fertilisants.item(row, 0)
    if not item:
        debug(f"⚠️ Double-clic fertilisant invalide sur la ligne {row}")
        return
    
    nom_fert = item.text()
    if not window.culture_active:
        QMessageBox.warning(
            window,
            "Aucune culture sélectionnée",
            "Veuillez d'abord sélectionner une culture"
        )
        debug(f"⚠️ Tentative d'ajout de fertilisant '{nom_fert}' sans culture active")
        return
    
    debug(f"Double-clic fertilisant '{nom_fert}' → ajout à la culture '{window.culture_active}'")
    ajouter_fert_utiliser(window, nom_fert)
    
    mark_doses_modifiees(window, True)
    debug("Ajout de l'affichage de lbl_modifie")

    debug("Ajout fertilisant utiliser -> table_modifier = True")
    window.table_modifiees = True
# ----------------------