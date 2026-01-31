# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import json
from pathlib import Path

from paths import FERT_FILE

from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
import sys

from utils.debug import debug

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
            fertilisants = [f for f in fertilisants if f['nom'].lower() != self.editing['nom'].lower()]
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

    # Fermeture
    def quitter(self):
        #ferme la fenetre
        self.close()
    # =====================


        
        
