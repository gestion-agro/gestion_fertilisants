import json
from pathlib import Path

from paths import CULTURE_FILE

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QMessageBox,
    QHBoxLayout, QComboBox, QTableWidgetItem,
    QTableWidget, QLabel
)
from PySide6.QtGui import QDoubleValidator, QIntValidator


class AjouterCultureWindow(QWidget):
    culture_ajoute = Signal()

    def __init__(self, culture=None):
        super().__init__()
        self.setWindowTitle("Ajouter une culture" if culture is None else "Modifier une culture")
        self.resize(300, 200)

        self.editing = culture  # stocker la culture à modifier (ou None)

        # validateurs
        validateur_NPK = QDoubleValidator(0.0, 100.0, 1, self)

        # layout principal
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # champs
        self.nom_input = QLineEdit()
        self.n_input = QLineEdit()
        self.p_input = QLineEdit()
        self.k_input = QLineEdit()
        self.surface = QLineEdit()

        # validateurs
        self.n_input.setValidator(validateur_NPK)
        self.p_input.setValidator(validateur_NPK)
        self.k_input.setValidator(validateur_NPK)

        form.addRow("Nom :", self.nom_input)
        form.addRow("N :", self.n_input)
        form.addRow("P :", self.p_input)
        form.addRow("K :", self.k_input)
        form.addRow("Surface (en m²) :", self.surface)

        layout.addLayout(form)

        # préremplissage si on modifie
        if culture:
            self.nom_input.setText(culture.get("nom", ""))
            self.n_input.setText(str(culture.get("N", "")))
            self.p_input.setText(str(culture.get("P", "")))
            self.k_input.setText(str(culture.get("K", "")))
            self.surface.setText(str(culture.get("surface", "")))

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
            surface = round(float(self.surface.text().replace(",", ".")), 1)
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Tous les champs doivent être des nombres valides.")
            return

        # lecture du fichier
        cultures = {}
        if CULTURE_FILE.exists():
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                cultures = json.load(f)
                if not isinstance(cultures, dict):
                    cultures = {}

        if self.editing:  # modification
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Voulez-vous modifier la culture « {self.editing['nom']} » ?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
            # supprimer l'ancienne culture
            if self.editing['nom'] in cultures:
                del cultures[self.editing['nom']]
        else:  # ajout
            if nom in cultures:
                QMessageBox.warning(self, "Erreur", "Cette culture existe déjà.")
                return

        # ajouter/modifier la culture
        cultures[nom] = {
            "N": n,
            "P": p,
            "K": k,
            "surface": surface
        }

        # sauvegarde
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(cultures, f, indent=2, ensure_ascii=False)

        # signal pour rafraîchir la page principale
        self.culture_ajoute.emit()

        # fermer la fenêtre
        self.close()


    # Fermeture
    def quitter(self):
        #ferme la fenetre
        self.close()
    # =====================


        
        
