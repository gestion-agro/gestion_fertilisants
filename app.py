# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import sys
import signal
import json
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from paths import ensure_user_data, ICON_FILE
from views.main_window import MainWindow
from logic.solver_fix import fix_cbc_permissions
from db import init_db, DB_FILE
from ui.login_window import LoginWindow
from views.login import authenticate
from wizard import SetupWizard

CONFIG_FILE = os.path.join(os.path.dirname(DB_FILE), "config.json")


def lire_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    fix_cbc_permissions()
    ensure_user_data()

    app = QApplication(sys.argv)
    from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale
    translator = QTranslator()
    path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    translator.load("qt_fr", path)
    app.installTranslator(translator)
    app.setWindowIcon(QIcon(str(ICON_FILE)))

    try:    
        init_db()
    except Exception as e:
        QMessageBox.critical(
            None, "Erreur base de données",
            f"Impossible d'initialiser la base :\n{e}")
        sys.exit(1)

    # ── Premier lancement : setup wizard ───────────────
    from db import is_first_launch
    if is_first_launch():
        wizard = SetupWizard()
        if wizard.exec() != SetupWizard.Accepted:
            sys.exit(0)

    # ── Connexion automatique ─────────────────
    current_user = None
    cfg = lire_config()
    auto_username = cfg.get("auto_login_username")

    if auto_username:
        # Récupérer l'utilisateur sans vérifier le mot de passe
        try:
            from db import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM users WHERE username = ? AND actif = 1",
                (auto_username,))
            row = cur.fetchone()
            cur.close()
            if row:
                current_user = dict(row)
        except Exception:
            pass

    # ── Écran de connexion si pas d'auto-login ─
    if not current_user:
        login = LoginWindow()
        if login.exec() != LoginWindow.Accepted or not login.current_user:
            sys.exit(0)
        current_user = login.current_user

    window = MainWindow(current_user=current_user)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()