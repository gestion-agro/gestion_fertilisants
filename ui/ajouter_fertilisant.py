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


class AjouterFertilisantWindow(QWidget):
    fertilisant_ajoute = Signal()

    def __init__(self, fertilisant=None):
        super().__init__()
        self.setWindowTitle("Ajouter un fertilisant" if fertilisant is None else "Modifier un fertilisant")
        self.resize(300, 200)

        self.editing = fertilisant  # stocker le fertilisant à modifier (ou None)

        # validateurs
        validateur_NPK = QDoubleValidator(0.0, 100.0, 1, self)
        validateur_condi = QIntValidator(0, 100000, self)
        validateur_prix = QDoubleValidator(0.0, 10000.0, 2, self)

        # layout principal
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # champs
        self.nom_input = QLineEdit()
        self.n_input = QLineEdit()
        self.p_input = QLineEdit()
        self.k_input = QLineEdit()
        self.condi_input = QLineEdit()
        self.liste = QComboBox()
        self.liste.addItems(["kg", "L"])
        self.prix_input = QLineEdit()

        # validateurs
        self.n_input.setValidator(validateur_NPK)
        self.p_input.setValidator(validateur_NPK)
        self.k_input.setValidator(validateur_NPK)
        self.condi_input.setValidator(validateur_condi)
        self.prix_input.setValidator(validateur_prix)

        # Conditionnement avec unité
        hbox = QHBoxLayout()
        hbox.addWidget(self.condi_input, 3)
        hbox.addWidget(self.liste, 1)

        form.addRow("Nom :", self.nom_input)
        form.addRow("N :", self.n_input)
        form.addRow("P :", self.p_input)
        form.addRow("K :", self.k_input)
        form.addRow("Condit unitaire :", hbox)
        form.addRow("Prix unitaire :", self.prix_input)

        layout.addLayout(form)

        # préremplissage si on modifie
        if fertilisant:
            self.nom_input.setText(fertilisant.get("nom", ""))
            self.n_input.setText(str(fertilisant.get("N", "")))
            self.p_input.setText(str(fertilisant.get("P", "")))
            self.k_input.setText(str(fertilisant.get("K", "")))
            self.condi_input.setText(str(fertilisant.get("conditionnement", "")))
            unite = fertilisant.get("unite", "kg")
            index = self.liste.findText(unite)
            if index >= 0:
                self.liste.setCurrentIndex(index)
            self.prix_input.setText(str(fertilisant.get("prix", "")))

        # bouton enregistrer
        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.clicked.connect(self.enregistrer)
        layout.addWidget(self.btn_save)

        # Quiter
        btn_quitter = QPushButton("Annuler")
        btn_quitter.clicked.connect(self.quitter)
        layout.addWidget(btn_quitter)
        # =====================

    def enregistrer(self):
        nom = self.nom_input.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        try:
            n = round(float(self.n_input.text().replace(",", ".")), 1)
            p = round(float(self.p_input.text().replace(",", ".")), 1)
            k = round(float(self.k_input.text().replace(",", ".")), 1)
            condi = int(float(self.condi_input.text().replace(",", ".")))
            prix = round(float(self.prix_input.text().replace(",", ".")), 2)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Tous les champs doivent être des nombres valides.")
            return

        # lecture du fichier
        fertilisants = []
        if FERT_FILE.exists():
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                fertilisants = json.load(f)

        # si on modifie, demander confirmation
        if self.editing:
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Voulez-vous modifier le fertilisant « {self.editing['nom']} » ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            # remplacer l'ancien fertilisant
            fertilisants = [f for f in fertilisants if f != self.editing]

        # Vérification doublon pour l'ajout
        else:
            for f in fertilisants:
                if f["nom"].lower() == nom.lower():
                    QMessageBox.warning(self, "Erreur", "Ce fertilisant existe déjà.")
                    return

        # ajouter/modifier
        fertilisants.append({
            "nom": nom,
            "N": n,
            "P": p,
            "K": k,
            "conditionnement": condi,
            "unite": self.liste.currentText(),
            "prix": prix
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

    # Fermeture
    def quitter(self):
        #ferme la fenetre
        self.close()
    # =====================


        
        
