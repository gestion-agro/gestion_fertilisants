# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

import utils.debug as debug
from utils.constantes import VERSION_URL

from views.culture import ajout_culture
from views.fertilisants import ajout_fert
from views.dialogs import ouvrir_parametres, redemarrer_debug, afficher_aide, afficher_apropos

from tables.remplissages import vider_table_calcul, vider_table_milieux


from updater import check_update, run_update

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
    
    action_vider_table_milieux = QAction("Vider tableaux", window)
    action_vider_table_milieux.triggered.connect(
        lambda : vider_table_milieux(window)
    )
    menu_fichier.addAction(action_vider_table_milieux)
    
    action_vider_table_calcul = QAction("Vider calculs", window)
    action_vider_table_calcul.triggered.connect(
        lambda : vider_table_calcul(window)
    )
    menu_fichier.addAction(action_vider_table_calcul)

    menu_fichier.addSeparator()

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

    # Édition
    # ======================
    menu_edition = menu_bar.addMenu("Édition")

    action_nouvelle_culture = QAction("Nouvelle culture", window)
    action_nouvelle_culture.triggered.connect(
        lambda : ajout_culture(window)
    )
    menu_edition.addAction(action_nouvelle_culture)

    action_nouveau_fertiisant = QAction("Nouveau fertilisant", window)
    action_nouveau_fertiisant.triggered.connect(
        lambda : ajout_fert(window)
    )
    menu_edition.addAction(action_nouveau_fertiisant)     
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
        version, url = check_update()
    except ConnectionError as e:
        QMessageBox.warning(None, "Pas de connexion", str(e))
        return
 
    if not version:
        QMessageBox.information(None, "Info", "Déjà à jour")
        return
 
    reply = QMessageBox.question(
        None,
        "Mise à jour",
        f"Nouvelle version {version} disponible. Installer ?"
    )
    if reply == QMessageBox.Yes:
        run_update(url)
 

