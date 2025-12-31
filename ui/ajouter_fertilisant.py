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
from PySide6.QtGui import QDoubleValidator, QIntValidator

# DATA_DIR = Path("data")
# FERT_FILE = DATA_DIR / "fertilisants.json"


class AjouterFertilisantWindow(QWidget):
    fertilisant_ajoute = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ajouter un fertilisant")
        self.resize(300, 200)

        # validateur nombre
        validateur_NPK = QDoubleValidator(0.0, 100.0, 1, self)
        validateur_NPK.setNotation(QDoubleValidator.StandardNotation)

        validateur_condi = QIntValidator(0, 100000, self)

        validateur_prix = QDoubleValidator(0.0, 10000.0, 2, self)
        validateur_prix.setNotation(QDoubleValidator.StandardNotation)        

        # Layout principale
        layout = QVBoxLayout(self)

        # Formulaire
        form = QFormLayout()

        self.nom_input = QLineEdit()
        self.n_input = QLineEdit()
        self.p_input = QLineEdit()
        self.k_input = QLineEdit()

        # Conditionnement + liste unité cote à cote
        hbox = QHBoxLayout()

        self.condi_input = QLineEdit()

        self.liste = QComboBox()
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

        self.n_input.setValidator(validateur_NPK)
        self.p_input.setValidator(validateur_NPK)
        self.k_input.setValidator(validateur_NPK)
        self.condi_input.setValidator(validateur_condi)
        self.prix_input.setValidator(validateur_prix)


        layout.addLayout(form)

        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self.enregistrer)
        layout.addWidget(self.btn_save)

    def enregistrer(self):
        nom = self.nom_input.text().strip()

        # Vérification du nom
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        # Conversion NPK
        try:
            n = self.str_to_float(self.n_input.text(), max_value=100.0)
            p = self.str_to_float(self.p_input.text(), max_value=100.0)
            k = self.str_to_float(self.k_input.text(), max_value=100.0)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Les valeurs de N, P et K doivent être numériques.")
            return

        # Vérification individuelle NPK
        if not (0 <= n <= 100):
            QMessageBox.warning(self, "Erreur", "N doit être entre 0 et 100.")
            return
        if not (0 <= p <= 100):
            QMessageBox.warning(self, "Erreur", "P doit être entre 0 et 100.")
            return
        if not (0 <= k <= 100):
            QMessageBox.warning(self, "Erreur", "K doit être entre 0 et 100.")
            return

        # Conversion conditionnement
        try:
            condi = int(float(self.condi_input.text().replace(",", ".")))
            if not (0 <= condi <= 100000):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Le conditionnement doit être un entier entre 0 et 100000.")
            return

        # Conversion prix
        try:
            prix = self.str_to_float(self.prix_input.text(), max_value=10000.0)
            if not (0.0 <= prix <= 10000.0):
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Le prix doit être un nombre entre 0 et 10000.")
            return

        # Vérification doublon
        fertilisants = []
        if FERT_FILE.exists():
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                fertilisants = json.load(f)

        for f in fertilisants:
            if f["nom"].lower() == nom.lower():
                QMessageBox.warning(self, "Erreur", "Ce fertilisant existe déjà.")
                return

        # Ajout dans le fichier
        fertilisants.append({
            "nom": nom,
            "N": round(n, 1),
            "P": round(p, 1),
            "K": round(k, 1),
            "conditionnement": condi,
            "unite": self.liste.currentText(),
            "prix": round(prix, 2),
        })

        with open(FERT_FILE, "w", encoding="utf-8") as f:
            json.dump(fertilisants, f, indent=2, ensure_ascii=False)

        self.fertilisant_ajoute.emit()
        self.close()



    def str_to_float(self, text, max_value=10000.0):
        try:
            text = text.replace(",", ".")
            value = float(text)
            value = max(0.0, min(max_value, value))
            return value
        except ValueError:
            return 0.0


    # Format input
    def get_formatted_values(self):
        result = {}

        # NPK : 0 à 100, 1 décimale
        for elem, line_edit in zip(['N', 'P', 'K'], [self.n_input, self.p_input, self.k_input]):
            value = str_to_float(line_edit.text(), max_value=100.0)
            value = round(value, 1)
            result[elem] = value

        # Conditionnement : entier 0 à 100000
        try:
            condi_value = int(float(self.condi_input.text().replace(",", ".")))
            condi_value = max(0, min(100000, condi_value))
        except ValueError:
            condi_value = 0
        result['Conditionnement'] = condi_value

        # Prix : 0 à 10000, 2 décimales
        prix_value = str_to_float(self.prix_input.text(), max_value=10000.0)
        prix_value = round(prix_value, 2)
        result['Prix'] = prix_value

        return result

    

        
        
