# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import sys
import signal
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from paths import ensure_user_data, ICON_FILE
from views.main_window import MainWindow
from logic.solver_fix import fix_cbc_permissions
from db import init_db
from ui.login_window import LoginWindow


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    fix_cbc_permissions()
    ensure_user_data()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_FILE)))

    # ── Initialisation de la base de données ──
    try:
        init_db()
    except Exception as e:
        QMessageBox.critical(
            None,
            "Erreur base de données",
            f"Impossible de se connecter à MySQL :\n{e}\n\n"
            "Vérifiez que MySQL est bien démarré et que les paramètres "
            "de connexion dans db.py sont corrects."
        )
        sys.exit(1)

    # ── Écran de connexion ────────────────────
    login = LoginWindow()
    if login.exec() != LoginWindow.Accepted or not login.current_user:
        sys.exit(0)

    current_user = login.current_user

    # ── Fenêtre principale ────────────────────
    window = MainWindow(current_user=current_user)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()