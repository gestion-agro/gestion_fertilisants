import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

import signal
import sys

from paths import ensure_user_data, FERT_FILE, CULTURE_FILE, ICON_FILE
from views.main_window import MainWindow

def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    ensure_user_data()
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_FILE)))


    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()








