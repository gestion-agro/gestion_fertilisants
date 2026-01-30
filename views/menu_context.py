from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from utils.debug import debug

from views.culture import ajout_culture, modifier_culture, supprimer_culture
from views.fertilisants import ajout_fert, modifier_fert, supprimer_fert
from views.fertilisants_utilises import ajouter_fert_utiliser, enlever_fert_utiliser

# ----------------------
# Menu contextuel culture
def menu_context_culture(window, pos):
    debug("=== menu_context_culture ===")

    row = window.table_cultures.currentRow()
    debug("Position clic :", pos, "| Ligne sélectionnée :", row)

    if row < 0:
        debug("⛔ Aucune ligne sélectionnée → menu annulé")
        return

    menu = QMenu()

    action_modifier = menu.addAction("Modifier la culture")
    menu.addSeparator()
    action_ajouter = menu.addAction("Ajouter la culture")
    action_supprimer = menu.addAction("Supprimer la culture")

    action = menu.exec(window.table_cultures.mapToGlobal(pos))
    debug("Action sélectionnée :", action.text() if action else None)

    if action == action_modifier:
        nom = window.table_cultures.item(row, 0).text()
        debug("→ Modifier culture :", nom)
        modifier_culture(window, nom)

    elif action == action_supprimer:
        nom = window.table_cultures.item(row, 0).text()
        debug("→ Supprimer culture :", nom)
        supprimer_culture(window, nom)

    elif action == action_ajouter:
        debug("→ Ajouter culture")
        ajout_culture(window)
# ----------------------

# ----------------------
# Menu contextuel fertilisant liste (droite)
def menu_context_fert_droite(window, pos):
    debug("=== menu context_fert_droite ===")

    row = window.table_fertilisants.currentRow()
    debug("Position clic :", pos, "| Ligne sélectionnée :", row)

    if row < 0:
        debug("⛔ Aucune ligne sélectionnée → menu annulé")
        return

    menu = QMenu()

    action_utiliser = menu.addAction("Utiliser ce fertilisant")
    if not window.culture_active:
        action_utiliser.setEnabled(False)
        debug("Action 'Utiliser' désactivée (pas de culture active)")

    menu.addSeparator()
    action_modifier = menu.addAction("Modifier le fertilisant")
    menu.addSeparator()
    action_ajouter = menu.addAction("Ajouter un fertilisant")
    action_supprimer = menu.addAction("Supprimer le fertilisant")

    action = menu.exec(window.table_fertilisants.mapToGlobal(pos))
    nom = window.table_fertilisants.item(row, 0).text()

    debug("Action sélectionnée :", action.text() if action else None)
    debug("Fertilisant concerné :", nom)

    if action == action_utiliser:
        debug("→ Utiliser fertilisant :", nom)
        ajouter_fert_utiliser(window,nom)

    elif action == action_modifier:
        debug("→ Modifier fertilisant :", nom)
        modifier_fert(window, nom)

    elif action == action_supprimer:
        debug("→ Supprimer fertilisant :", nom)
        supprimer_fert(window, nom)

    elif action == action_ajouter:
        debug("→ Ajouter fertilisant")
        ajout_fert(window)
# ----------------------

# ----------------------
# Menu contextuel fertilisant milieu
def menu_context_fert_milieu(window, pos):
    debug("=== menu_context_fert_milieu ===")

    row = window.table_utiliser.currentRow()
    debug("Position clic :", pos, "| Ligne sélectionnée :", row)

    if row < 0:
        debug("⛔ Aucune ligne sélectionnée → menu annulé")
        return

    menu = QMenu()
    action_enlever = menu.addAction("Enlever ce fertilisant")

    action = menu.exec(window.table_utiliser.mapToGlobal(pos))
    debug("Action sélectionnée :", action.text() if action else None)

    if action == action_enlever:
        nom = window.table_utiliser.item(row, 0).text()
        debug("→ Enlever fertilisant :", nom)
        enlever_fert_utiliser(window, nom)
# ----------------------