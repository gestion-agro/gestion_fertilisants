# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug
""" 
ouvrir_parametres
redemarrer_debug
afficher_aide
afficher_apropos
"""

# Actions ouvrir paramètres
# ----------------------
def ouvrir_parametres(window):
    QMessageBox.information(window, "Paramètres", "À venir")
# ----------------------

# Redemarrer en mode DEBUG
def redemarrer_debug(window, clavier=False):
    nouvel_etat = debug.toggle_debug()

    if clavier:
        debug.debug("Depuis raccourci clavier")

    etat = "Activé" if nouvel_etat else "Désactivé"

    QMessageBox.information(
        window,
        "Mode DEBUG",
        f"Mode DEBUG {etat}"
    )

    debug.debug("DEBUG =", nouvel_etat)
# ----------------------

# Aide
# ----------------------
def afficher_aide(window):
    QMessageBox.information(window, "Aide", "Aide à la gestion de fertilisants")
# ----------------------

# A propos
# ----------------------
def afficher_apropos(window):
    QMessageBox.information(
        window,
        "À propos",
        "Gestion Fertiliant\nVersion 2.1.1\n©Clément THIEULEUX"
    )
# ----------------------