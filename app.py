# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import sys
import signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from paths import ensure_user_data, ICON_FILE
from views.main_window import MainWindow
from logic.solver_fix import fix_cbc_permissions


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    fix_cbc_permissions()
    ensure_user_data()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_FILE)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
