from pathlib import Path
import sys
from paths import FERT_FILE, CULTURE_FILE, TOTAL_LABEL

if getattr(sys, 'frozen', False):
    # Exécutable PyInstaller
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Développement normal
    BASE_DIR = Path(__file__).parent

import json
# from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem
)

from PySide6.QtCore import Qt

from PySide6.QtGui import QIcon

from scipy.optimize import minimize
import numpy as np

class GestionFertilisants(QWidget):
    def __init__(self):
        super().__init__()
        self.fert_base = self.charger_fertilisant()
        self.setWindowTitle("Gestion des fertilisants")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(420, 280)

        # Fenetre principale
        layout = QVBoxLayout(self)

        # Tableau
        self.table = QTableWidget(0,7)
        self.table.setHorizontalHeaderLabels(
            [
                "Nom", "N", "P", "K", "Condit unitaire", "Prix unitaire", "Action"
            ]
        )

        self.table.setColumnWidth(0, 260)
        layout.addWidget(self.table)
        # ======================

        # Bouton ajouter
        btn_add = QPushButton("Ajouter")
        btn_add.clicked.connect(self.ajout)
        layout.addWidget(btn_add)
        # ======================

        # Bouton enregistrer
        btn_save = QPushButton("Fermer et enregistrer")
        btn_save.clicked.connect(self.enregistrer)
        layout.addWidget(btn_save)
        # ======================

        # Données
        self.fert_base = self.charger_fertilisant()
        self.remplir_table()
        # =======================

    # Enregistrer liste fertilisant
    def enregistrer(self):
        # with open(CULTURE_FILE, "w", encoding="utf-8") as f:
        #     json.dump(self.cultures, f, indent=2, ensure_ascii=False)
        self.close()
    # ======================

    # Ajout fertilisant
    def ajout(self):
        from ui.ajouter_fertilisant import AjouterFertilisantWindow
        self.ajout = AjouterFertilisantWindow()
        self.ajout.show()
    # ======================

    # Charger la base des fertilisant
    def charger_fertilisant(self):
        if not FERT_FILE.exists():
            with open(FERT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            return []

        with open(FERT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    # =======================

    # Remplissage du tableau
    def remplir_table(self):
        self.table.setRowCount(0)

        for fert in self.fert_base:
            self.ajouter_ligne(fert)

        self.table.resizeColumnsToContents()
        self.charger_fertilisant()
    # ======================

    # Ajouter ligne
    def ajouter_ligne(self, fert):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(fert.get("nom", "")))
        self.table.setItem(row, 1, QTableWidgetItem(str(fert.get("N", ""))))
        self.table.setItem(row, 2, QTableWidgetItem(str(fert.get("P", ""))))
        self.table.setItem(row, 3, QTableWidgetItem(str(fert.get("K", ""))))

        condi = f'{fert.get("conditionnement", "")} {fert.get("unite", "")}'
        self.table.setItem(row, 4, QTableWidgetItem(condi))

        self.table.setItem(row, 5, QTableWidgetItem(str(fert.get("prix", ""))))

        # Actions
        btn_modif = QPushButton("Modifier")
        btn_suppr = QPushButton("Supprimer")

        btn_modif.setProperty("fert", fert)
        btn_suppr.setProperty("fert", fert)

        btn_modif.clicked.connect(self.modifier_fert)
        btn_suppr.clicked.connect(self.supprimer_fert)

        action_layout = QHBoxLayout()
        action_layout.addWidget(btn_modif)
        action_layout.addWidget(btn_suppr)
        action_layout.setContentsMargins(0, 0, 0, 0)

        action_widget = QWidget()
        action_widget.setLayout(action_layout)

        self.table.setCellWidget(row, 6, action_widget)
    # ======================

    # Supression fertilisant
    def supprimer_fert(self):
        btn = self.sender()
        fert = btn.property("fert")

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer le fertilisant « {fert['nom']} » ?",
            QMessageBox.Yes | QMessageBox.No
            )

        if reply != QMessageBox.Yes:
            return

        self.fert_base = [f for f in self.fert_base if f != fert]

        with open(FERT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fert_base, f, indent=2, ensure_ascii=False)

        self.remplir_table
    # ====================

    # Modifications fertilisant
    def modifier_fert(self):
        btn = self.sender()
        fert = btn.property("fert")

        from ui.ajouter_fertilisant import AjouterFertilisantWindow
        self.edit = AjouterFertilisantWindow(fert)
        self.edit.show() 