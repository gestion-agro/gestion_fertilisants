import json
from pathlib import Path

from paths import CULTURE_FILE

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QMessageBox
)

from PySide6.QtGui import QIcon

class BesoinsForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Données culture")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(420, 280)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        # =====================
        # Culture (combo)
        # =====================
        self.culture_combo = QComboBox()
        self.culture_combo.setEditable(False)
        self.culture_combo.currentIndexChanged.connect(self.on_culture_change)

        form.addRow("Culture :", self.culture_combo)

        # =====================
        # Besoins
        # =====================
        self.n_input = QLineEdit()
        self.p_input = QLineEdit()
        self.k_input = QLineEdit()
        self.surface_input = QLineEdit()

        form.addRow("Besoin N (U) :", self.n_input)
        form.addRow("Besoin P (U) :", self.p_input)
        form.addRow("Besoin K (U) :", self.k_input)
        form.addRow("Surface (m²) :", self.surface_input)

        layout.addLayout(form)

        # =====================
        # Valider
        # =====================
        btn_valider = QPushButton("Valider et choisir les fertilisants")
        btn_valider.clicked.connect(self.valider)
        layout.addWidget(btn_valider)

        self.cultures = {}
        self.charger_cultures()

        # =====================
        # Gestion fertilisant
        # =====================
        btn_ferti = QPushButton("Gérer mes fertilisants")
        btn_ferti.clicked.connect(self.ferti)
        layout.addWidget(btn_ferti)

        self.cultures = {}
        self.charger_cultures()

        # =====================
        # Quiter
        # =====================
        btn_quitter = QPushButton("Fermer et enregistrer")
        btn_quitter.clicked.connect(self.quitter)
        layout.addWidget(btn_quitter)

    # =====================
    # Chargement
    # =====================
    def charger_cultures(self):
        self.culture_combo.clear()
        self.cultures = {}

        if CULTURE_FILE.exists():
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                self.cultures = json.load(f)

            for nom in self.cultures:
                self.culture_combo.addItem(nom, nom)

        # entrée spéciale
        self.culture_combo.addItem("➕ Nouvelle culture", "__NEW__")

    # =====================
    # Sélection culture
    # =====================
    def on_culture_change(self):
        data = self.culture_combo.currentData()

        # ---- Nouvelle culture ----
        if data == "__NEW__":
            self.culture_combo.setEditable(True)
            self.culture_combo.setCurrentText("")
            self.culture_combo.lineEdit().setPlaceholderText(
                "Saisir le nom de la culture"
            )

            self.n_input.clear()
            self.p_input.clear()
            self.k_input.clear()
            self.surface_input.clear()
            return

        # ---- Culture existante ----
        self.culture_combo.setEditable(False)

        culture = self.cultures.get(data)
        if not culture:
            return

        self.n_input.setText(str(culture.get("N", "")))
        self.p_input.setText(str(culture.get("P", "")))
        self.k_input.setText(str(culture.get("K", "")))
        self.surface_input.setText(str(culture.get("surface", "")))

    # =====================
    # Validation
    # =====================
    def valider(self):
        nom = self.culture_combo.currentText().strip()

        if not nom:
            QMessageBox.warning(self, "Erreur", "Nom de culture obligatoire.")
            return

        try:
            N = float(self.n_input.text())
            P = float(self.p_input.text())
            K = float(self.k_input.text())
            surface = float(self.surface_input.text())
        except ValueError:
            QMessageBox.warning(self, "Erreur", "Valeurs numériques requises.")
            return

        # Charger le fichier existant pour ne jamais écraser fertilisants
        cultures_file = {}
        if CULTURE_FILE.exists():
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                cultures_file = json.load(f)

        if nom in cultures_file:
            # Mettre à jour uniquement N, P, K, surface
            cultures_file[nom]["N"] = N
            cultures_file[nom]["P"] = P
            cultures_file[nom]["K"] = K
            cultures_file[nom]["surface"] = surface
            # NE PAS TOUCHER aux fertilisants
        else:
            # Nouvelle culture
            cultures_file[nom] = {
                "N": N,
                "P": P,
                "K": K,
                "surface": surface,
                "fertilisants": []
            }

        # Écrire seulement N, P, K, surface (fertilisants restent intacts)
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(cultures_file, f, indent=2, ensure_ascii=False)

        # Ouvrir la fenêtre fertilisants
        from ui.choix_fertilisants import ChoixFertilisants

        self.fert_window = ChoixFertilisants(nom,N,P,K)
        self.fert_window.show()

    # =====================
    # Gestion fertilisation
    # =====================
    def ferti(self):
        # Enregistrer
        self.enregistrer()
        # Ouvrir la fenêtre gestion ferti
        from ui.gestion_fertilisants import GestionFertilisants

        self.gestion_fert_window = GestionFertilisants()
        self.gestion_fert_window.show() 

    # =====================
    # Enregistrement
    # =====================
    def enregistrer(self):
                # recup nom culture
        nom = self.culture_combo.currentText().strip()
        if not nom or nom == "__NEW__":
            #si aucune culture valide ou vide -> fermer
            self.close()
            return

        # recup valeurs champs
        try:
            N = float(self.n_input.text())
            P = float(self.p_input.text())
            K = float(self.k_input.text())
            surface = float(self.surface_input.text())
        except ValueError:
            #ignore si non numérique
            N = P = K = 0
            surface = 10000 # par défaut 1ha

        #charger le fichier existant
        cultures_file = {}
        if CULTURE_FILE.exists():
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                cultures_file = json.load(f)

        # MaJ ou créer la culture
        if nom in cultures_file:
            cultures_file[nom]["N"] = N
            cultures_file[nom]["P"] = P
            cultures_file[nom]["K"] = K
            cultures_file[nom]["surface"] = surface
        else:
            cultures_file[nom] = {
            "N": N,
            "P": P,
            "K": K,
            "surface": surface,
            "fertilisants": []
            }

        # ecrire le fichier
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(cultures_file, f, indent=2, ensure_ascii=False)

    # =====================
    # Fermeture
    # =====================
    def quitter(self):
        # on enregistre
        self.enregistrer()
        #ferme la fenetre
        self.close()