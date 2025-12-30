from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class CalculDose(QWidget):
    def __init__(self, culture_nom):
        super().__init__()
        self.setWindowTitle(f"Calcul des doses – {culture_nom}")

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Calcul des doses pour : {culture_nom}"))

        