# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug

from views.dialogs import redemarrer_debug

"""
init_raccourcis
"""

def init_raccourcis(window):
    """
    Initialise tous les raccourcis clavier de l'application.
    window = instance de MainWindow
    """

    debug.debug("Initialisation des raccourcis clavier")

    # Debug
    QShortcut(
        QKeySequence("Ctrl+D"),
        window
    ).activated.connect(
        lambda: redemarrer_debug(window, clavier=True)
    )