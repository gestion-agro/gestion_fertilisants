from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QRadioButton, QPushButton, QHBoxLayout
)
class ChoixModeCalcul(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mode de calcul")
        self.setFixedSize(300, 150)
        
        self.mode = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Choisir un mode de calcul :"))

        self.radio_auto = QRadioButton("Auto (Coût le plus minime tout en )")
        self.radio_strict = QRadioButton("Strict (Uniquement fertilisant ±5%)")



        self.radio_strict.setChecked(True)

        layout.addWidget(self.radio_auto)
        layout.addWidget(self.radio_strict)

        btns = QHBoxLayout()

        btn_ok = QPushButton("Valider")
        btn_cancel = QPushButton("Annuler")

        btn_ok.clicked.connect(self.valider)
        btn_cancel.clicked.connect(self.reject)

        btns.addWidget(btn_ok)
        btns.addWidget(btn_cancel)

        layout.addLayout(btns)

    def valider(self):
        if self.radio_strict.isChecked():
            self.mode = "strict"
        else:
            self.mode = "auto"
        self.accept()
    
    