import json
from pathlib import Path

from paths import FERT_FILE

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QComboBox, QTableWidgetItem,
    QTableWidget, QLabel
)
from PySide6.QtGui import QDoubleValidator

# DATA_DIR = Path("data")
# FERT_FILE = DATA_DIR / "fertilisants.json"


class AjouterFertilisantWindow(QWidget):
    fertilisant_ajoute = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ajouter un fertilisant")
        self.resize(300, 200)

        # validateur nombre
        validator_pos = QDoubleValidator(0.0, 999999.0, 1, self)
        validator_pos.setNotation(QDoubleValidator.StandardNotation)

        # Layout principale
        layout = QVBoxLayout(self)

        # Formulaire
        form = QFormLayout()

        self.nom_input = QLineEdit()
        self.n_input = QLineEdit()
        self.p_input = QLineEdit()
        self.k_input = QLineEdit()
        self.k_input.setPlaceholderText("test")

        # Conditionnement + liste unité cote à cote
        hbox = QHBoxLayout()

        self.condi_input = QLineEdit()

        self.liste = QComboBox()
        self.liste.setPlaceholderText("Unité")
        self.liste.setStyleSheet("""
            QComboBox::PlaceholderText {
                color: #CC0000
            }
            """)
        self.liste.setEditable(False)
        self.liste.addItems(["kg", "L"])

        hbox.addWidget(self.condi_input, 3)
        hbox.addWidget(self.liste, 1)

        self.prix_input = QLineEdit()

        form.addRow("Nom :", self.nom_input)
        form.addRow("N :", self.n_input)
        form.addRow("P :", self.p_input)
        form.addRow("K :", self.k_input)
        form.addRow("Condit unitaire :", hbox)
        form.addRow("Prix unitaire :", self.prix_input)

        self.n_input.setValidator(validator_pos)
        self.p_input.setValidator(validator_pos)
        self.k_input.setValidator(validator_pos)
        self.condi_input.setValidator(validator_pos)
        self.prix_input.setValidator(validator_pos)


        layout.addLayout(form)

        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self.enregistrer)
        layout.addWidget(self.btn_save)

    def enregistrer(self):
        nom = self.nom_input.text().strip()

        try:
            n = float(self.n_input.text())
            p = float(self.p_input.text())
            k = float(self.k_input.text())
            condi = float(self.condi_input.text())
            prix = float(self.prix_input.text())
        except ValueError:
            QMessageBox.warning(self, "Erreur", "NPK, conditionnement et prix doivent être numériques.")
            return

        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        fertilisants = []
        if FERT_FILE.exists():
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                fertilisants = json.load(f)

        # éviter doublon de nom
        for f in fertilisants:
            if f["nom"].lower() == nom.lower():
                QMessageBox.warning(self, "Erreur", "Ce fertilisant existe déjà.")
                return

        fertilisants.append({
            "nom": nom,
            "N": n,
            "P": p,
            "K": k,
            "conditionnement": condi,
            "prix": prix
        })

        with open(FERT_FILE, "w", encoding="utf-8") as f:
            json.dump(fertilisants, f, indent=2, ensure_ascii=False)

        self.fertilisant_ajoute.emit()
        self.close()
