# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

import utils.debug as debug
from utils.constantes import VERSION_URL

from views.dialogs import ouvrir_parametres, redemarrer_debug, afficher_aide, afficher_apropos

from logic.update import check_update, run_update, update_if_available

import subprocess
import sys

"""
init_menu
"""

def init_menu(window):
    menu_bar = window.menuBar()
    window.setMenuBar(menu_bar)

    # Fichier
    # ======================
    menu_fichier = menu_bar.addMenu("Fichiers")

    action_parametres = QAction("Paramètres", window)
    action_parametres.triggered.connect(
        lambda : ouvrir_parametres(window)
    )
    menu_fichier.addAction(action_parametres)

    menu_fichier.addSeparator()

    action_quitter = QAction("Quitter", window)
    action_quitter.setShortcut(QKeySequence.Quit)
    action_quitter.triggered.connect(window.close)
    menu_fichier.addAction(action_quitter)
    # ======================

    # Outils
    # ======================
    menu_outils = menu_bar.addMenu("Outils")

    action_debug = QAction("Redémarrer en mode debug", window)
    action_debug.triggered.connect(
        lambda : redemarrer_debug(window)
    )
    menu_outils.addAction(action_debug)
    # ======================

    # Aide
    # ======================
    menu_aide = menu_bar.addMenu("Aide")

    action_aide = QAction("Aide", window)
    action_aide.triggered.connect(
        lambda : afficher_aide(window)
    )
    menu_aide.addAction(action_aide)

    menu_aide.addSeparator()

    action_maj = QAction("Vérifier les mises à jour", window)
    action_maj.triggered.connect(
        lambda : check_updates_ui()
    )
    menu_aide.addAction(action_maj)

    menu_aide.addSeparator()

    action_aporpos = QAction("À propos", window)
    action_aporpos.triggered.connect(
        lambda : afficher_apropos(window)
    )
    menu_aide.addAction(action_aporpos)
    # ======================

    debug.debug("Menu initialisé")

def check_updates_ui():
    try:
        available, data = check_update()
    except ConnectionError as e:
        QMessageBox.warning(None, "Pas de connexion", str(e))
        return
    except Exception as e:
        QMessageBox.warning(None, "Erreur", str(e))
        return

    if not available:
        QMessageBox.information(None, "Info", "Déjà à jour !")
        return

    import sys
    plateforme = "Windows" if sys.platform == "win32" \
                 else "Linux" if sys.platform.startswith("linux") \
                 else "macOS"

    reply = QMessageBox.question(
        None,
        "Mise à jour disponible",
        f"Nouvelle version disponible.\nInstaller pour {plateforme} ?"
    )
    if reply == QMessageBox.Yes:
        try:
            run_update(data)
        except Exception as e:
            QMessageBox.critical(None, "Erreur mise à jour", str(e))