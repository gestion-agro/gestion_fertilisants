from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from utils.debug import debug

from tables.tables import aligner_table
""" 
ajouter_fert_utiliser
enlever_fert_utiliser
table_doses_ha_modifiee
double_clic_fertilisant_enlever
mark_doses_modifiee
"""

# ----------------------
# Ajouter un fertilisant dans la table du milieu
def ajouter_fert_utiliser(window, nom):
    debug("=== ajouter_fert_utiliser ===")
    debug("Fertilisant demandé :", nom)
    
    fertilisant_double = True

    fert = next((f for f in window.fert_base if f["nom"] == nom), None)
    if not fert:
        debug("⛔ Fertilisant introuvable")
        return

    for row in range(window.table_utiliser.rowCount()):
        if window.table_utiliser.item(row, 0).text() == nom:
            debug("⚠️ Fertilisant déjà présent dans table_utiliser")
            QMessageBox.warning(window, "Fertilisant déjà présent", f"Le fertilisant : {nom} est déjà utiliser")
            fertilisant_double = False
            return

    if fertilisant_double:
        debug("fertilisant pas en double donc ajout")
        row = window.table_utiliser.rowCount()
        window.table_utiliser.insertRow(row)

        window.table_utiliser.setItem(row, 0, QTableWidgetItem(fert["nom"]))
        window.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert.get("N"))))
        window.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert.get("P"))))
        window.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert.get("K"))))
        window.table_utiliser.setItem(row, 4, QTableWidgetItem("0"))

        debug(f"Fertilisant ajouté à table_utiliser ligne {row}")

        aligner_table(window.table_utiliser, "table_utiliser")
        debug("Alignement table_utiliser effectué")
    
        mark_doses_modifiees(window, True)
        debug("Ajout de l'affichage de lbl_modifie")

        debug("Ajout fertilisant utiliser -> table_modifier = True")
        window.table_modifiees = True
# ----------------------

# ----------------------
# Enlever un fertilisant
def enlever_fert_utiliser(window, nom):
    debug("=== enlever_fert_utiliser ===")
    debug("Fertilisant demandé :", nom)

    for row in range(window.table_utiliser.rowCount()):
        if window.table_utiliser.item(row, 0).text() == nom:
            window.table_utiliser.removeRow(row)
            debug(f"Fertilisant retiré de table_utiliser ligne {row}")
    
            mark_doses_modifiees(window, True)
            debug("Ajout de l'affichage de lbl_modifie")

            debug("Ajout fertilisant utiliser -> table_modifier = True")
            window.table_modifiees = True
            return

    debug("⚠️ Fertilisant non trouvé dans table_utiliser")
# ----------------------

# ----------------------
def table_doses_ha_modifiee(window, row, column):
    window.table_modifiees = True
    item = window.table_doses_ha.item(row, column)
    text = item.text() if item else "None"
    debug(f"⚠️ Modification détectée à la cellule ({row}, {column}) → {text}")
# ----------------------

# au double clique sur un fertilisant dans table_utiliser -> retirer de cette table
# ----------------------
def double_clic_fertilisant_enlever(window, row, column):
    item = window.table_utiliser.item(row, 0)
    if not item:
        debug(f"⚠️ Double-clic fertilisant à enlever invalide sur la ligne {row}")
        return
    
    nom_fert = item.text()
    debug(f"Double-clic fertilisant '{nom_fert}' → suppression de la table 'utiliser'")
    enlever_fert_utiliser(window, nom_fert)
    
    mark_doses_modifiees(window, True)
    debug("Ajout de l'affichage de lbl_modifie")

    debug("Enlever fertilisant utiliser -> table_modifier = True")
    window.table_modifiees = True
# ----------------------

# Mettre a jour le badge de modification à chaque modifications des tableaux
# ----------------------
def mark_doses_modifiees(window, modifie=True):
    window.set_doses_modifiees = modifie

    if modifie:
        window.lbl_modifie.setText("Modification non enregistrées")
        window.lbl_modifie.setStyleSheet("color: red;")
    else:
        window.lbl_modifie.setText("Modification enregistré")
        window.lbl_modifie.setStyleSheet("color: green;")
# ----------------------