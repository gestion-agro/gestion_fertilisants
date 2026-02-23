# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX
import os
import sys

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug
""" 
ouvrir_parametres
redemarrer_debug
afficher_aide
get_version
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

# Get version
# ----------------------
def get_version():
    try:
        if getattr(sys, 'frozen', False):
            # PyInstaller
            base_path = sys._MEIPASS
        else:
            # Script Python normal
            base_path = os.path.abspath(".")

        version_file = os.path.join(base_path, "version.txt")

        with open(version_file, "r") as f:
            return f.read().strip()

    except Exception as e:
        print("Erreur lecture version:", e)
        return "Version inconnue"


# A propos
# ----------------------
def afficher_apropos(window):
    QMessageBox.information(
        window,
        "À propos",
        f"Gestion Fertiliant\nVersion {get_version()}\n©Clément THIEULEUX"
    )
# ----------------------