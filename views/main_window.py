from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QVBoxLayout, QSplitter, QHeaderView, QAbstractItemView,
    QMenu, QWidgetAction, QMessageBox, QDialog
)
from PySide6.QtCore import Qt

from PySide6.QtGui import QFont, QBrush, QColor

import json
from paths import CULTURE_FILE, FERT_FILE, TOTAL_LABEL

import math
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des cultures et fertilisants")
        self.showMaximized()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # ======================
        # Splitter horizontal
        # ======================
        splitter = QSplitter(Qt.Horizontal)

        # ----------------------
        # Côté gauche : cultures
        left_layout = QVBoxLayout()
        left_container = QWidget()
        left_container.setLayout(left_layout)

        btn_add_culture = QPushButton("Ajouter culture")
        btn_add_culture.clicked.connect(self.ajout_culture)
        left_layout.addWidget(btn_add_culture)

        self.table_cultures = QTableWidget(0, 5)
        self.table_cultures.setHorizontalHeaderLabels(["Nom", "N", "P", "K", "Surface"])

        self.table_cultures.cellDoubleClicked.connect(self.culture_selectionnee_changed)

        header = self.table_cultures.horizontalHeader()

        # Colonne 0 (Nom) prend tout l'espace restant
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # les autres colonnes s'ajuste automatiquement au contenu
        for col in range(1, self.table_cultures.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Cultures : non éditable et sélection par ligne
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setSelectionMode(QAbstractItemView.SingleSelection)

        # Ajout menu contextuel
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(self.menu_context_culture)

        left_layout.addWidget(self.table_cultures)

        splitter.addWidget(left_container)  # ajouté au splitter
        # ----------------------

        # ----------------------
        # Zone centrale : utilisation + doses
        center_layout = QVBoxLayout()
        center_container = QWidget()
        center_container.setLayout(center_layout)

        self.lbl_culture_active = QLabel("Aucune culture sélectionnée")
        self.lbl_culture_active.setAlignment(Qt.AlignCenter)

        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.lbl_culture_active.setFont(font)

        center_layout.addWidget(self.lbl_culture_active)

        lbl_utiliser = QLabel("Fertilisants à utiliser")
        center_layout.addWidget(lbl_utiliser)

        self.table_utiliser = QTableWidget(0, 4)
        self.table_utiliser.setHorizontalHeaderLabels(["Nom", "N", "P", "K"])
        self.table_utiliser.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        header = self.table_utiliser.horizontalHeader()

        # Colonne 0 (Nom) prend tout l'espace restant
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # les autres colonnes s'ajuste automatiquement au contenu
        for col in range(1, self.table_utiliser.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Cultures : non éditable et sélection par ligne
        self.table_utiliser.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_utiliser.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_utiliser.setSelectionMode(QAbstractItemView.SingleSelection)

        center_layout.addWidget(self.table_utiliser)




        lbl_dose_ha = QLabel("Doses pour 1 ha")
        center_layout.addWidget(lbl_dose_ha)

        self.table_dose_ha = QTableWidget(0, 5)
        self.table_dose_ha.setHorizontalHeaderLabels(
            ["Fertilisant", "N", "P", "K", "Dose (kg/ha)"]
        )

        self.doses_modifiees = False
        self.table_dose_ha.cellChanged.connect(self.table_dose_ha_modifiee)

        self.table_dose_ha.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        center_layout.addWidget(self.table_dose_ha)


        header = self.table_dose_ha.horizontalHeader()

        # Colonne 0 (Nom) prend tout l'espace restant
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # les autres colonnes s'ajuste automatiquement au contenu
        for col in range(1, self.table_dose_ha.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Cultures : non éditable et sélection par ligne
        self.table_dose_ha.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_dose_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_dose_ha.setSelectionMode(QAbstractItemView.SingleSelection)



        self.lbl_dose_surface = QLabel("Doses pour la surface")
        center_layout.addWidget(self.lbl_dose_surface)

        self.table_dose_surface = QTableWidget(0, 7)
        self.table_dose_surface.setHorizontalHeaderLabels(
            ["Fertilisant", "Dose (kg)", "Condit unitaire", "Prix unitaire HT", "Quantité", "Prix HT", "Prix TTC"]
        )
        self.table_dose_surface.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        header = self.table_dose_surface.horizontalHeader()

        # Colonne 0 (Nom) prend tout l'espace restant
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # les autres colonnes s'ajuste automatiquement au contenu
        for col in range(1, self.table_dose_surface.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Cultures : non éditable et sélection par ligne
        self.table_dose_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_dose_surface.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_dose_surface.setSelectionMode(QAbstractItemView.SingleSelection)


        self.culture_active = None
        center_layout.addWidget(self.table_dose_surface)




        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(self.calculer_doses)

        btn_valider = QPushButton("Valider et retirer du stock")

        center_layout.addWidget(btn_calcul)
        center_layout.addWidget(btn_valider)

        # Ajout menu contextuel
        self.table_utiliser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_utiliser.customContextMenuRequested.connect(self.menu_context_fert_milieu)

        splitter.addWidget(center_container)
        # ----------------------

        # ----------------------
        # Côté droit : fertilisants disponibles
        right_layout = QVBoxLayout()
        right_container = QWidget()
        right_container.setLayout(right_layout)

        # Bouton ajouter fertilisant
        btn_add_fert = QPushButton("Ajouter fertilisant")
        btn_add_fert.clicked.connect(self.ajout_fert)
        right_layout.addWidget(btn_add_fert)

        # Tableau des fertilisants
        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(
            ["Nom", "Stock", "N", "P", "K", "Conditionnement", "Prix"]
        )

        # Fertilisants : non éditable et sélection par ligne
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_fertilisants.setSelectionMode(QAbstractItemView.SingleSelection)  # une seule ligne sélectionnable

        header = self.table_fertilisants.horizontalHeader()
        # Colonne 0 (Nom) prend tout l'espace restant
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        # Les autres colonnes s'ajustent automatiquement au contenu
        for col in range(1, self.table_fertilisants.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        # Permettre le wrap si le texte est trop long
        self.table_fertilisants.setWordWrap(False)

        # Ajout menu contextuel
        self.table_fertilisants.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_fertilisants.customContextMenuRequested.connect(self.menu_context_fert_droite)

        # Ajouter au Layout
        right_layout.addWidget(self.table_fertilisants)

        # Ajouter au splitter
        splitter.addWidget(right_container)
        # ----------------------

        # ----------------------
        # Mettre le splitter comme layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(splitter)
        # ----------------------

        # Optionnel : définir la taille initiale des panels (ratios)
        splitter.setSizes([300, 700, 400])  # gauche, centre, droite

        # Charger les données
        self.fert_base = self.charger_fertilisants()
        self.cultures = self.charger_cultures()

        # Remplir les tableaux
        self.remplir_tableaux()

        self.cultures_selectionnee = None


    # ----------------------
    # Charger les fertilisants
    def charger_fertilisants(self):
        try:
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
                # S'assurer que chaque élément est bien un dict avec les champs nécessaire
                for fert in data:
                    if not isinstance(fert, dict):
                        continue # Ignorer si ce n'est pas le cas
                    fert.setdefault("stock", 0)
                    fert.setdefault("unite", "kg")
                    fert.setdefault("N", 0)
                    fert.setdefault("P", 0)
                    fert.setdefault("K", 0)
                    fert.setdefault("conditionnement", 1)
                    fert.setdefault("prix", 0)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    # ----------------------


    # ----------------------
    # Charger les cultures
    def charger_cultures(self):
        try:
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    # ----------------------

    # ----------------------
    # Remplissage des tableaux
    def remplir_tableaux(self):
        # --------- Fertilisants ----------
        self.table_fertilisants.setRowCount(0)
        # trier la liste des fertilisants par nom
        for fert in sorted(self.fert_base, key=lambda x: x.get("nom", "").lower()):
            row = self.table_fertilisants.rowCount()
            self.table_fertilisants.insertRow(row)
            self.table_fertilisants.setItem(row, 0, QTableWidgetItem(fert.get("nom", "")))
            self.table_fertilisants.setItem(row, 1, QTableWidgetItem(str(fert.get("stock", 0))))
            self.table_fertilisants.setItem(row, 2, QTableWidgetItem(str(fert.get("N", 0))))
            self.table_fertilisants.setItem(row, 3, QTableWidgetItem(str(fert.get("P", 0))))
            self.table_fertilisants.setItem(row, 4, QTableWidgetItem(str(fert.get("K", 0))))
            self.table_fertilisants.setItem(row, 5, QTableWidgetItem(f"{fert.get('conditionnement', 1)} {fert.get('unite', 'kg')}"))
            self.table_fertilisants.setItem(row, 6, QTableWidgetItem(str(fert.get("prix", 0.0))))

        # --------- Cultures ----------
        self.table_cultures.setRowCount(0)
        # trier les cultures par nom
        for nom, culture in sorted(self.cultures.items(), key=lambda x: x[0].lower()):
            row = self.table_cultures.rowCount()
            self.table_cultures.insertRow(row)
            self.table_cultures.setItem(row, 0, QTableWidgetItem(nom))
            self.table_cultures.setItem(row, 1, QTableWidgetItem(str(culture.get("N", 0))))
            self.table_cultures.setItem(row, 2, QTableWidgetItem(str(culture.get("P", 0))))
            self.table_cultures.setItem(row, 3, QTableWidgetItem(str(culture.get("K", 0))))
            self.table_cultures.setItem(row, 4, QTableWidgetItem(str(culture.get("surface", 10000))))


    def ajout_fert(self, culture=None):
        from ui.ajouter_fertilisant import AjouterFertilisantWindow
        self.ajout_window = AjouterFertilisantWindow(culture)

        # Connecter le signal pour recharger les fertiliants
        self.ajout_window.fertilisant_ajoute.connect(self.recharger_fertilisants)

        self.ajout_window.show()

    def recharger_fertilisants(self):
        self.fert_base = self.charger_fertilisants()
        self.remplir_tableaux()

    def ajout_culture(self, culture=None):
        from ui.ajouter_culture import AjouterCultureWindow
        self.ajout_window = AjouterCultureWindow(culture)

        # Connecter le signal pour recharger les fertiliants
        self.ajout_window.culture_ajoute.connect(self.recharger_cultures)

        self.ajout_window.show()

    def recharger_cultures(self):
        self.cultures = self.charger_cultures()
        self.remplir_tableaux()

    # ----------------------
    # Menu contextuel culture
    def menu_context_culture(self, pos):
        row = self.table_cultures.currentRow()
        if row < 0:
            return
        
        menu = QMenu()

        # Actions
        action_modifier = menu.addAction("Modifier la culture")
        menu.addSeparator()
        action_ajouter = menu.addAction("Ajouter la culture")
        action_supprimer = menu.addAction("Supprimer la culture")

        # Obtenir l'action cliqué
        action = menu.exec(self.table_cultures.mapToGlobal(pos))
        if action == action_modifier:
            nom = self.table_cultures.item(row, 0).text()
            self.modifier_culture(nom)
        elif action == action_supprimer:
            nom = self.table_cultures.item(row, 0).text()
            self.supprimer_culture(nom)
        elif action == action_ajouter:
            self.ajout_culture()
    # ----------------------

    # ----------------------
    # Menu contextuel fertilisant liste
    def menu_context_fert_droite(self, pos):
        row = self.table_fertilisants.currentRow()
        if row < 0:
            return
        
        menu = QMenu()

        action_utiliser = menu.addAction("Utiliser ce fertilisant")

        if not self.culture_active:
            action_utiliser.setEnabled(False)
        
        # Actions
        menu.addSeparator()
        action_modifier = menu.addAction("Modifier le fertilisant")
        menu.addSeparator()
        action_ajouter = menu.addAction("Ajouter le fertilisant")
        action_supprimer = menu.addAction("Supprimer le fertilisant")

        action = menu.exec(self.table_fertilisants.mapToGlobal(pos))
        nom = self.table_fertilisants.item(row, 0).text()

        # Obtenir l'action cliqué
        if action == action_utiliser:
            self.ajouter_fert_utiliser(nom)
        elif action == action_modifier:
            self.modifier_fert(nom)
        elif action == action_supprimer:
            self.supprimer_fert(nom)
        elif action == action_ajouter:
            self.ajout_fert()
    # ----------------------

    # ----------------------
    # Menu contextuel fertilisant milieu
    def menu_context_fert_milieu(self, pos):
        row = self.table_utiliser.currentRow()
        if row < 0:
            return
        
        menu = QMenu()

        # Actions
        action_enlever = menu.addAction("Enlever ce fertilisant")

        action = menu.exec(self.table_utiliser.mapToGlobal(pos))

        # Obtenir l'action cliqué
        if action == action_enlever:
            nom = self.table_utiliser.item(row, 0).text()
            self.enlever_fert_utiliser(nom)
    # ----------------------

    # Modifier une culture
    def modifier_culture(self, nom):
        culture = self.cultures.get(nom)
        if not culture:
            return
        culture_complet = culture.copy()
        culture_complet["nom"] = nom
        self.ajout_culture(culture_complet)

    # Supprmier une culture
    def supprimer_culture(self, nom):
        if nom not in self.cultures:
            return
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer la culture « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        # Supprimer de la liste
        del self.cultures[nom]
        # Réécrire le fichier
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cultures, f, indent=2, ensure_ascii=False)
        self.remplir_tableaux()

    # Modifier un fertilisant
    def modifier_fert(self, nom):
        fert = next((f for f in self.fert_base if f["nom"] == nom), None)
        if not fert:
            return
        self.ajout_fert(fert)

    # Supprimer un fertiliant
    def supprimer_fert(self, nom):
        fert = next((f for f in self.fert_base if f["nom"] == nom), None)
        if not fert:
            return
        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer le fertilisant « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        # Supprimer de la liste
        self.fert_base = [f for f in self.fert_base if f["nom"] != nom]
        # Réécrire le fichier
        with open(FERT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fert_base, f, indent=2, ensure_ascii=False)
        self.remplir_tableaux()

    # Ajouter un fertilisant dans la table du milieu
    def ajouter_fert_utiliser(self, nom):
        fert = next((f for f in self.fert_base if f["nom"] ==nom), None)
        if not fert:
            return
        # Vérifier si déjà dans table_utiliser
        for row in range(self.table_utiliser.rowCount()):
            if self.table_utiliser.item(row, 0).text() == nom:
                return
        # Ajouter une ligne
        row = self.table_utiliser.rowCount()
        self.table_utiliser.insertRow(row)
        self.table_utiliser.setItem(row, 0, QTableWidgetItem(fert["nom"]))
        self.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert.get("N"))))
        self.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert.get("P"))))
        self.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert.get("K"))))
        self.table_utiliser.setItem(row, 4, QTableWidgetItem("0"))

    # Enlever un fertilisant
    def enlever_fert_utiliser(self, nom):
        for row in range(self.table_utiliser.rowCount()):
            if self.table_utiliser.item(row, 0).text() == nom:
                self.table_utiliser.removeRow(row)
                break

    def culture_selectionnee_changed(self, row, column):
        # --- Si aucune ligne sélectionnée ---
        row = self.table_cultures.currentRow()
        if row < 0:
            return

        item = self.table_cultures.item(row, 0)
        if not item:
            return

        nom_culture = item.text()

        # --- Si on reclique sur la même culture, ne rien faire ---
        if self.culture_active == nom_culture:
            return

        # --- Vérifier si des doses ont été modifiées pour la culture active ---
        if self.culture_active and self.doses_modifiees:
            reply = QMessageBox.question(
                self,
                "Changement de culture",
                "Voulez-vous quitter sans enregistrer ?",
                QMessageBox.Yes | QMessageBox.Save | QMessageBox.Cancel
            )

            if reply == QMessageBox.Cancel:
                return  # Annuler le changement

            if reply == QMessageBox.Save:
                self.enregistrer_doses_culture()  # sauvegarde dans cultures.json
                self.doses_modifiees = False  # réinitialiser le flag

        # --- Mettre toutes les lignes en normal (non gras) ---
        for r in range(self.table_cultures.rowCount()):
            it = self.table_cultures.item(r, 0)
            if it:
                font = it.font()
                font.setBold(False)
                it.setFont(font)

        # --- Mettre en gras la culture sélectionnée ---
        font = item.font()
        font.setBold(True)
        item.setFont(font)

        # --- Mettre à jour la culture active ---
        self.culture_active = nom_culture

        culture = self.cultures[nom_culture]
        surface = culture.get("surface", 0)

        # --- Nom culture et doses pour surface ---
        self.lbl_culture_active.setText(f"{nom_culture}")
        self.lbl_dose_surface.setText(f"Doses pour la surface ({surface} m²)")

        # --- Marquer visuellement la ligne sélectionnée ---
        self.table_cultures.selectRow(row)

        # --- Charger fertilisants utilisés ---
        self.table_utiliser.setRowCount(0)
        ferts_utilises = culture.get("fertilisants_utilises", [])
        if ferts_utilises:
            for fert in ferts_utilises:
                fert_base = next((f for f in self.fert_base if f["nom"] == fert["nom"]), {})
                row_util = self.table_utiliser.rowCount()
                self.table_utiliser.insertRow(row_util)
                self.table_utiliser.setItem(row_util, 0, QTableWidgetItem(fert["nom"]))
                self.table_utiliser.setItem(row_util, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
                self.table_utiliser.setItem(row_util, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
                self.table_utiliser.setItem(row_util, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
                self.table_utiliser.setItem(row_util, 4, QTableWidgetItem(str(fert.get("doses_ha", 0))))
        else:
            # Si pas de fertilisants utilisés enregistrés
            self.charger_ferts_pour_culture(nom_culture)

        # --- Calculer doses pour 1ha et pour la surface réelle ---
        resultats = []
        for fert in ferts_utilises:
            fert_base = next((f for f in self.fert_base if f["nom"] == fert["nom"]), {})
            dose_ha = fert.get("doses_ha", 0)
            N = dose_ha * fert_base.get("N", 0) / 100
            P = dose_ha * fert_base.get("P", 0) / 100
            K = dose_ha * fert_base.get("K", 0) / 100
            resultats.append({
                "nom": fert["nom"],
                "dose_ha": dose_ha,
                "N": N,
                "P": P,
                "K": K
            })

        # --- Vider tableaux et remplir ---
        self.table_dose_ha.setRowCount(0)
        self.table_dose_surface.setRowCount(0)
        self.remplir_table_dose_ha(resultats)
        self.calculer_doses_surface(resultats, culture)

        # --- Réinitialiser le flag modification après chargement ---
        self.doses_modifiees = False




    # Charger fertilisants culture
    def charger_ferts_pour_culture(self, nom_culture):
        culture = self.cultures.get(nom_culture)
        if not culture:
            self.table_utiliser.setRowCount(0)
            return

        # --- Vider les tableaux ---
        self.table_utiliser.setRowCount(0)
        self.table_dose_ha.setRowCount(0)
        self.table_dose_surface.setRowCount(0)

        # --- Remplir table_utiliser ---
        # Priorité : prendre les fertilisants utilisés s'ils existent
        ferts_utilises = culture.get("fertilisants_utilises", [])

        for f in ferts_utilises:
            nom = f["nom"]
            fert_base = next((fb for fb in self.fert_base if fb["nom"] == nom), None)
            if not fert_base:
                continue

            row = self.table_utiliser.rowCount()
            self.table_utiliser.insertRow(row)
            self.table_utiliser.setItem(row, 0, QTableWidgetItem(fert_base["nom"]))
            self.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
            self.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
            self.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
            self.table_utiliser.setItem(row, 4, QTableWidgetItem(str(f.get("doses_ha", 0))))

        # --- Remplir table_dose_ha ---
        for f in ferts_utilises:
            nom = f["nom"]
            dose_ha = f.get("doses_ha", 0)
            fert_base = next((fb for fb in self.fert_base if fb["nom"] == nom), None)
            if not fert_base:
                continue

            N = dose_ha * fert_base.get("N", 0) / 100
            P = dose_ha * fert_base.get("P", 0) / 100
            K = dose_ha * fert_base.get("K", 0) / 100

            row = self.table_dose_ha.rowCount()
            self.table_dose_ha.insertRow(row)
            self.table_dose_ha.setItem(row, 0, QTableWidgetItem(nom))
            self.table_dose_ha.setItem(row, 1, QTableWidgetItem(f"{N:.1f}"))
            self.table_dose_ha.setItem(row, 2, QTableWidgetItem(f"{P:.1f}"))
            self.table_dose_ha.setItem(row, 3, QTableWidgetItem(f"{K:.1f}"))
            self.table_dose_ha.setItem(row, 4, QTableWidgetItem(f"{dose_ha:.1f}"))

        # --- Recalculer doses pour la surface ---
        self.calculer_doses_surface(
            [
                {
                    "nom": f["nom"],
                    "dose_ha": f.get("doses_ha", 0),
                    "N": self.table_dose_ha.item(i, 1).text(),
                    "P": self.table_dose_ha.item(i, 2).text(),
                    "K": self.table_dose_ha.item(i, 3).text(),
                }
                for i, f in enumerate(ferts_utilises)
            ],
            culture
        )


    def calculer_doses(self):
        # Vérifier qu'une culture est sélectionnée
        if not hasattr(self, "culture_active") or not self.culture_active:
            QMessageBox.warning(self, "Erreur", "Aucune culture sélectionnée")
            return

        culture = self.cultures[self.culture_active]
        Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

        ferts = []
        for row in range(self.table_utiliser.rowCount()):
            ferts.append({
                "nom": self.table_utiliser.item(row, 0).text(),
                "N": float(self.table_utiliser.item(row, 1).text()),
                "P": float(self.table_utiliser.item(row, 2).text()),
                "K": float(self.table_utiliser.item(row, 3).text())
            })

        # vider les tableaux résultats
        self.table_dose_ha.setRowCount(0)
        self.table_dose_surface.setRowCount(0)

        # --- Si aucun fertilisant sélectionné, mode auto directement ---
        if not ferts:
            resultats = self.calcul_auto(Nb, Pb, Kb)
        else:
            # Sinon demander le mode (auto ou strict)
            from ui.dialog_mode_calcul import ChoixModeCalcul
            dlg = ChoixModeCalcul(self)
            if dlg.exec() != QDialog.Accepted:
                return
            mode = dlg.mode
            if mode == "auto":
                resultats = self.calcul_auto(Nb, Pb, Kb)
            else:
                resultats = self.calcul_strict(Nb, Pb, Kb, ferts)

        # remplir les tableaux
        self.remplir_table_dose_ha(resultats)
        self.calculer_doses_surface(resultats, culture)


    def calcul_auto(self, Nb, Pb, Kb):
        """
        Mode AUTO :
        - utilise TOUS les fertilisants de la base
        - triés par prix/kg
        - on remplit au maximum sans dépasser les besoins
        """

        resultats = []

        # besoins restants
        N_rest, P_rest, K_rest = Nb, Pb, Kb

        # préparer la liste avec prix/kg
        ferts = []
        for fert in self.fert_base:
            condi = float(fert.get("conditionnement", 1))
            prix = float(fert.get("prix", 0))
            prix_kg = prix / condi if condi > 0 else float("inf")

            ferts.append({
                "nom": fert["nom"],
                "N": fert["N"],
                "P": fert["P"],
                "K": fert["K"],
                "prix_kg": prix_kg
            })

        # tri par fertilisant le moins cher
        ferts.sort(key=lambda f: f["prix_kg"])

        for fert in ferts:
            doses = []

            if fert["N"] > 0 and N_rest > 0:
                doses.append(N_rest / (fert["N"] / 100))
            if fert["P"] > 0 and P_rest > 0:
                doses.append(P_rest / (fert["P"] / 100))
            if fert["K"] > 0 and K_rest > 0:
                doses.append(K_rest / (fert["K"] / 100))

            if not doses:
                continue

            dose = min(doses)
            if dose <= 0:
                continue

            N = dose * fert["N"] / 100
            P = dose * fert["P"] / 100
            K = dose * fert["K"] / 100

            N_rest -= N
            P_rest -= P
            K_rest -= K

            resultats.append({
                "nom": fert["nom"],
                "dose_ha": round(dose, 2),
                "N": round(N, 2),
                "P": round(P, 2),
                "K": round(K, 2)
            })

            # arrêt si tout est couvert
            if N_rest <= 0 and P_rest <= 0 and K_rest <= 0:
                break

        return resultats

    def calcul_strict(self, Nb, Pb, Kb, ferts):
        if len(ferts) < 3:
            QMessageBox.warning(
                self, "Erreur",
                "Le mode strict nécessite au moins 3 fertilisants"
            )
            return []

        # Matrice des pourcentages
        A = np.array([
            [f["N"] / 100 for f in ferts],
            [f["P"] / 100 for f in ferts],
            [f["K"] / 100 for f in ferts],
        ])

        B = np.array([Nb, Pb, Kb])

        # Résolution
        doses, *_ = np.linalg.lstsq(A, B, rcond=None)

        resultats = []
        for dose, fert in zip(doses, ferts):
            if dose < 0:
                dose = 0

            resultats.append({
                "nom": fert["nom"],
                "dose_ha": dose,
                "N": dose * fert["N"] / 100,
                "P": dose * fert["P"] / 100,
                "K": dose * fert["K"] / 100,
            })

        return resultats

    def remplir_table_dose_ha(self, resultats):
        total_N = total_P = total_K  = 0

        for r in resultats:
            row = self.table_dose_ha.rowCount()
            self.table_dose_ha.insertRow(row)

            self.table_dose_ha.setItem(row, 0, QTableWidgetItem(r["nom"]))
            self.table_dose_ha.setItem(row, 1, QTableWidgetItem(f"{r['N']:.1f}"))
            self.table_dose_ha.setItem(row, 2, QTableWidgetItem(f"{r['P']:.1f}"))
            self.table_dose_ha.setItem(row, 3, QTableWidgetItem(f"{r['K']:.1f}"))
            self.table_dose_ha.setItem(row, 4, QTableWidgetItem(f"{r['dose_ha']:.1f}"))

            total_N += r["N"]
            total_P += r["P"]
            total_K += r["K"]

        # Ligne TOTAL
        row = self.table_dose_ha.rowCount()
        self.table_dose_ha.insertRow(row)

        self.table_dose_ha.setItem(row, 0, QTableWidgetItem("TOTAL"))
        self.table_dose_ha.setItem(row, 1, QTableWidgetItem(f"{total_N:.1f}"))
        self.table_dose_ha.setItem(row, 2, QTableWidgetItem(f"{total_P:.1f}"))
        self.table_dose_ha.setItem(row, 3, QTableWidgetItem(f"{total_K:.1f}"))
        self.table_dose_ha.setItem(row, 4, QTableWidgetItem(""))

        font = QFont()
        font.setBold(True)

        for col in range(self.table_dose_ha.columnCount()):
            item = self.table_dose_ha.item(row, col)
            if item:
                item.setFont(font)
                item.setBackground(QBrush(QColor("#e6e6e6")))

        self.table_dose_ha.setRowHeight(row, 32)

    # Fait le produit en croix de 1ha -> surface donnée de la culture
    def calculer_doses_surface(self, resultats, culture):
        surface = culture.get("surface", 1)

        self.table_dose_surface.setRowCount(0)

        total_prix = 0

        for r in resultats:
            dose_surface = r["dose_ha"] * surface / 10000

            # retrouver le fertilisant pour le prix
            fert = next(
                (f for f in self.fert_base if f["nom"] == r["nom"]),
                None
            )

            prix = 0
            if fert:
                condi = fert.get("conditionnement", 1)
                prix_sac = fert.get("prix", 0)
                prix_kg = prix_sac / condi if condi > 0 else 0
                prix = dose_surface * prix_kg

            row = self.table_dose_surface.rowCount()
            self.table_dose_surface.insertRow(row)

            self.table_dose_surface.setItem(row, 0, QTableWidgetItem(r["nom"]))
            self.table_dose_surface.setItem(row, 1, QTableWidgetItem(f"{dose_surface:.1f}"))
            self.table_dose_surface.setItem(row, 2, QTableWidgetItem(f"{prix:.2f} €"))

            total_prix += prix

        # Ligne TOTAL
        row = self.table_dose_surface.rowCount()
        self.table_dose_surface.insertRow(row)

        self.table_dose_surface.setItem(row, 0, QTableWidgetItem("TOTAL"))
        self.table_dose_surface.setItem(row, 1, QTableWidgetItem(""))
        self.table_dose_surface.setItem(row, 2, QTableWidgetItem(f"{total_prix:.1f} €"))
        self.table_dose_surface.setItem(row, 3, QTableWidgetItem(""))
        self.table_dose_surface.setItem(row, 4, QTableWidgetItem(f"{total_prix:.1f} €"))
        self.table_dose_surface.setItem(row, 5, QTableWidgetItem(""))
        self.table_dose_surface.setItem(row, 6, QTableWidgetItem(""))

        font = QFont()
        font.setBold(True)

        for col in range(self.table_dose_surface.columnCount()):
            item = self.table_dose_surface.item(row, col)
            if item:
                item.setFont(font)
                item.setBackground(QBrush(QColor("#e6e6e6")))

        self.table_dose_surface.setRowHeight(row, 32)

    def enregistrer_doses_culture(self):
        if not self.culture_active:
            return

        culture = self.cultures.get(self.culture_active)
        if not culture:
            return

        fertilisants = []
        for row in range(self.table_dose_ha.rowCount()):
            # Ignorer la ligne TOTAL
            nom_item = self.table_dose_ha.item(row, 0)
            if nom_item is None:
                continue
            nom = nom_item.text()
            if nom == TOTAL_LABEL:
                continue

            dose_ha_item = self.table_dose_ha.item(row, 4)
            if dose_ha_item is None:
                continue
            try:
                dose_ha = float(dose_ha_item.text())
            except ValueError:
                dose_ha = 0

            fertilisants.append({
                "nom": nom,
                "doses_ha": dose_ha
            })

        culture["fertilisants_utilises"] = fertilisants

        # Sauvegarder dans le fichier JSON
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cultures, f, indent=2, ensure_ascii=False)

    def table_dose_ha_modifiee(self, row, column):
        self.doses_modifiees = True