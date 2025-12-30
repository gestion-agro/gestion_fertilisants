import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from ui.besoins_form import BesoinsForm
import sys

from paths import ensure_user_data, FERT_FILE, CULTURE_FILE, ICON_FILE

ensure_user_data()

app = QApplication(sys.argv)

app.setWindowIcon(QIcon(str(ICON_FILE)))

window = BesoinsForm()
window.show()
sys.exit(app.exec())
