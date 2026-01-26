from PySide6.QtWidgets import (
    QMainWindow, QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QVBoxLayout, QHBoxLayout,  QSplitter, QHeaderView, QAbstractItemView,
    QMenu, QMessageBox, QDialog,
    QCheckBox,
    QMenuBar, QMenu # Menu 
)
from PySide6.QtCore import Qt

from PySide6.QtGui import (
    QFont, QBrush, QColor,
    QAction, QKeySequence # Menu
)

import numpy as np
import math
import pulp
import cvxpy as cp
import sys

import json

from paths import CULTURE_FILE, FERT_FILE, TOTAL_LABEL

from ui.ajouter_fertilisant import AjouterFertilisantWindow
from ui.ajouter_culture import AjouterCultureWindow
from ui.dialog_mode_calcul import ChoixModeCalcul

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des cultures et fertilisants")
        self.showMaximized()

        self.MIN_doses_ha = 15      # kg/ha minimum affichable
        self.TOLERANCE_DEPASS = 0.02  # +5 % max autorisé
        self.culture_active = None
        self.cultures_selectionne = None
        self.table_modifiees = False
        self.DEBUG = False

        self.creer_menu()

        # Label badge
        self.lbl_modifie = QLabel("Modification non enregistrées")
        self.lbl_modifie.setStyleSheet("color: red; font-weight:bold;")
        self.set_doses_modifiees = False
        self.lbl_modifie.setVisible(False) # Caché par défault

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
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(self.menu_context_culture)

        # Setup header via fonction
        self.setup_table_header(self.table_cultures, stretch_col=0)
        left_layout.addWidget(self.table_cultures)

        splitter.addWidget(left_container)
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
        center_layout.addWidget(self.lbl_modifie)

        lbl_utiliser = QLabel("Fertilisants à utiliser")
        center_layout.addWidget(lbl_utiliser)

        self.table_utiliser = QTableWidget(0, 4)
        self.table_utiliser.setHorizontalHeaderLabels(["Nom", "N", "P", "K"])
        self.table_utiliser.cellDoubleClicked.connect(self.double_clic_fertilisant_enlever)
        self.table_utiliser.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_utiliser.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_utiliser.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_utiliser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_utiliser.customContextMenuRequested.connect(self.menu_context_fert_milieu)

        self.debug("Affichage de lbl_modifie")
        self.table_utiliser.itemChanged.connect(lambda item: self.mark_doses_modifiees(True))

        self.setup_table_header(self.table_utiliser, stretch_col=0)
        center_layout.addWidget(self.table_utiliser)

        lbl_doses_ha = QLabel("Doses pour 1 ha")
        center_layout.addWidget(lbl_doses_ha)

        self.table_doses_ha = QTableWidget(0, 5)
        self.table_doses_ha.setHorizontalHeaderLabels(["Fertilisant", "N", "P", "K", "Dose (kg/ha)"])
        self.table_doses_ha.cellChanged.connect(self.table_doses_ha_modifiee)
        self.table_doses_ha.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_ha.setSelectionMode(QAbstractItemView.SingleSelection)

        self.debug("Affichage de lbl_modifie")
        self.table_doses_ha.itemChanged.connect(lambda item: self.mark_doses_modifiees(True))

        self.setup_table_header(self.table_doses_ha, stretch_col=0)
        center_layout.addWidget(self.table_doses_ha)

        self.lbl_dose_surface = QLabel("Doses pour la surface")
        center_layout.addWidget(self.lbl_dose_surface)

        self.table_dose_surface = QTableWidget(0, 7)
        self.table_dose_surface.setHorizontalHeaderLabels(
            ["Fertilisant", "Dose", "Prix (dose)", "Conditionnement", "Prix unitaire", "Quantité", "Prix HT"]
        )
        self.table_dose_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_dose_surface.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_dose_surface.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setup_table_header(self.table_dose_surface, stretch_col=0)
        center_layout.addWidget(self.table_dose_surface)

        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(self.calculer_doses)
        btn_enregistrer = QPushButton("Enregistrer")
        btn_enregistrer.clicked.connect(self.enregistrer_doses_culture)
        center_layout.addWidget(btn_calcul)
        center_layout.addWidget(btn_enregistrer)

        splitter.addWidget(center_container)
        # ----------------------

        # ----------------------
        # Côté droit : fertilisants disponibles
        right_layout = QVBoxLayout()
        right_container = QWidget()
        right_container.setLayout(right_layout)

        btn_add_fert = QPushButton("Ajouter fertilisant")
        btn_add_fert.clicked.connect(self.ajout_fert)
        right_layout.addWidget(btn_add_fert)

        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(["Nom", "N", "P", "K", "Conditionnement", "Prix", "Utilisable"])
        self.table_fertilisants.cellDoubleClicked.connect(self.double_clic_fertilisant)
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_fertilisants.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_fertilisants.setWordWrap(False)
        self.table_fertilisants.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_fertilisants.customContextMenuRequested.connect(self.menu_context_fert_droite)

        self.setup_table_header(self.table_fertilisants, stretch_col=0)
        right_layout.addWidget(self.table_fertilisants)

        splitter.addWidget(right_container)
        # ----------------------

        # ----------------------
        # Mettre le splitter comme layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(splitter)
        splitter.setSizes([300, 700, 400])
        # ----------------------

        # Charger les données
        self.fert_base = self.charger_fertilisants()
        self.debug(f"Fertilisants chargés : {len(self.fert_base)}")
        self.cultures = self.charger_cultures()
        self.debug(f"Cultures chargées : {len(self.cultures)}")

        # Remplir les tableaux
        self.remplir_tableaux()

        self.cultures_selectionnee = None

    # ----------------------
    # Charger les fertilisants
    def charger_fertilisants(self):
        self.debug("=== charger_fertilisants ===")
        self.debug("=== Fichier :", FERT_FILE)
        
        try:
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                if not isinstance(data, list):
                    self.debug("⚠️ Données invalides : pas une liste → reset []")
                    data = []

                self.debug(f"{len(data)} fertiliant(s) chergé(s) depuis le fichiers")

                # S'assurer que chaque élément est bien un dict avec les champs nécessaire
                for i, fert in enumerate(data):
                    if not isinstance(fert, dict):
                        self.debug(f"⛔ Élément {i} ignoré (pas un dict)")
                        continue # Ignorer si ce n'est pas le cas

                    fert.setdefault("stock", 0)
                    fert.setdefault("unite", "kg")
                    fert.setdefault("N", 0)
                    fert.setdefault("P", 0)
                    fert.setdefault("K", 0)
                    fert.setdefault("conditionnement", 1)
                    fert.setdefault("prix", 0)

                    self.debug(
                        f"✔ Fertilisant {i} :",
                        fert.get("nom", "<sans nom>"),
                        f"NPK=({fert['N']},{fert['P']},{fert['K']})",
                        f"prix={fert['prix']}",
                        f"cond={fert['conditionnement']}"
                    )

                return data
        except FileNotFoundError:
            self.debug("❌ Fichier fertilisants introuvable")
            return []
        
        except json.JSONDecodeError as e:
            self.debug("❌ Erreur JSON :", e)
            return
    # ----------------------

    # ----------------------
    # Charger les cultures
    def charger_cultures(self):
        self.debug("=== charger_cultures ===")
        self.debug("Fichiers :", CULTURE_FILE)

        try:
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                if not isinstance(data, dict):
                    self.debug("⚠️ Données invalides : pas un dict → reset {}")
                    data = {}

                self.debug(f"{len(data)} culture(s) chargée(s)")

                for nom, culture in data.items():
                    self.debug(
                        f"✔ Culture : {nom}",
                        f"N={culture.get('N', 0)}",
                        f"P={culture.get('P', 0)}",
                        f"K={culture.get('K', 0)}",
                        f"surface={culture.get('surface', '?')}"
                    )

                return data
            
        except FileNotFoundError:
            self.debug("❌ Fichier fertilisants introuvable")
            return {}
        
        except json.JSONDecodeError as e:
            self.debug("❌ Erreur JSON :", e)
            return {}
    # ----------------------

    # ----------------------
    # Remplissage des tableaux
    def remplir_tableaux(self):
        self.debug("=== remplir_tableaux ===")

        # --------- Fertilisants ----------
        self.debug("→ Remplissage tableau fertiliants")
        self.table_fertilisants.setRowCount(0)

        # trier la liste des fertilisants par nom
        ferts_tries = sorted(self.fert_base, key=lambda x: x.get("nom", "").lower())
        self.debug(f"{len(ferts_tries)} fertiliant(s) à afficher")

        for i, fert in enumerate(ferts_tries):
            row = self.table_fertilisants.rowCount()
            self.table_fertilisants.insertRow(row)

            nom = fert.get("nom", "")
            self.table_fertilisants.setItem(row, 0, QTableWidgetItem(nom))
            self.table_fertilisants.setItem(row, 1, QTableWidgetItem(str(fert.get("N", 0))))
            self.table_fertilisants.setItem(row, 2, QTableWidgetItem(str(fert.get("P", 0))))
            self.table_fertilisants.setItem(row, 3, QTableWidgetItem(str(fert.get("K", 0))))
            self.table_fertilisants.setItem(
                row, 4,
                QTableWidgetItem(f"{fert.get('conditionnement', 1)} {fert.get('unite', 'kg')}")
            )
            self.table_fertilisants.setItem(row, 5, QTableWidgetItem(str(fert.get("prix", 0.0))))
            
            chk = QCheckBox()
            chk.setChecked(True)

            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.addWidget(chk)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(layout)

            self.table_fertilisants.setCellWidget(row, 6, cell_widget)

            self.debug(
                f" [{row}] Fertilisant affiché :",
                nom,
                f"NPK=({fert.get('N')},{fert.get('P')},{fert.get('K')})",
                f"prix={fert.get('prix')}"
            )

        # --------- Cultures ----------
        self.debug("→ Remplissage tableau cultures")
        self.table_cultures.setRowCount(0)

        cultures_tries = sorted(self.cultures.items(), key=lambda x: x[0].lower())
        self.debug(f"{len(cultures_tries)} culture(s) à afficher")

        # trier les cultures par nom
        for i, (nom, culture) in enumerate(cultures_tries):
            row = self.table_cultures.rowCount()
            self.table_cultures.insertRow(row)

            self.table_cultures.setItem(row, 0, QTableWidgetItem(nom))
            self.table_cultures.setItem(row, 1, QTableWidgetItem(str(culture.get("N", 0))))
            self.table_cultures.setItem(row, 2, QTableWidgetItem(str(culture.get("P", 0))))
            self.table_cultures.setItem(row, 3, QTableWidgetItem(str(culture.get("K", 0))))
            self.table_cultures.setItem(row, 4, QTableWidgetItem(str(culture.get("surface", 10000))))

            self.debug(
                f"  [{row}] Culture affichée :",
                nom,
                f"NPK=({culture.get('N')},{culture.get('P')},{culture.get('K')})",
                f"surface={culture.get('surface', 10000)}"
            )
        
        # --------- Alignements ---------
        self.aligner_table_culture()
        self.aligner_table_doses_ha()
        self.aligner_table_dose_surface()
        self.aligner_table_utiliser()
        self.aligner_table_fertilisants()

        self.debug("=== Fin remplir_tableaux ===")
    # ----------------------
    
    # ----------------------
    # Ajouter un fertiliant
    def ajout_fert(self, culture=None):
        self.debug("=== ajout_fert ===")
        self.debug("Culture passée :", culture)

        self.ajout_window = AjouterFertilisantWindow(culture)

        # Connecter le signal pour recharger les fertiliants
        self.ajout_window.fertilisant_ajoute.connect(self.recharger_fertilisants)
        self.debug("Signal fertilisant_ajoute connecté → recharger_fertilisant")

        self.ajout_window.show()
        self.debug("Fenêtre AjouterFertilisantWindow affichée")
    # ----------------------

    # ----------------------
    # Recharger les fertilisants
    def recharger_fertilisants(self):
        self.debug("=== recharger_fertilisants ===")

        self.fert_base = self.charger_fertilisants()
        self.debug(f"{len(self.fert_base)} fertilisant(s) après rechargement")

        self.remplir_tableaux()
        self.debug("Tableau rafraîchis (fertilisants)")
    # ----------------------

    # ----------------------
    # Ajouter une culture
    def ajout_culture(self, culture=None):
        self.debug("=== ajout_culture ===")
        self.debug("Culture passée :", culture)

        self.ajout_window = AjouterCultureWindow(culture)

        # Connecter le signal pour recharger les fertiliants
        self.ajout_window.culture_ajoute.connect(self.recharger_cultures)
        self.debug("Signel culture_ajoute connecté → recharger_cultures")

        self.ajout_window.show()
        self.debug("Fenêtre AjouterCultureWindow affiché")
    # ----------------------

    # ----------------------
    # Recharger les cultures
    def recharger_cultures(self):
        self.debug("=== recharger_cultures ===")

        self.cultures = self.charger_cultures()
        self.debug(f"{len(self.cultures)} culture(s) apres rechargement")

        self.remplir_tableaux()
        self.debug("Tableaux rafraîchis (cultures)")
    # ----------------------

    # ----------------------
    # Menu contextuel culture
    def menu_context_culture(self, pos):
        self.debug("=== menu_context_culture ===")

        row = self.table_cultures.currentRow()
        self.debug("Position clic :", pos, "| Ligne sélectionnée :", row)

        if row < 0:
            self.debug("⛔ Aucune ligne sélectionnée → menu annulé")
            return

        menu = QMenu()

        action_modifier = menu.addAction("Modifier la culture")
        menu.addSeparator()
        action_ajouter = menu.addAction("Ajouter la culture")
        action_supprimer = menu.addAction("Supprimer la culture")

        action = menu.exec(self.table_cultures.mapToGlobal(pos))
        self.debug("Action sélectionnée :", action.text() if action else None)

        if action == action_modifier:
            nom = self.table_cultures.item(row, 0).text()
            self.debug("→ Modifier culture :", nom)
            self.modifier_culture(nom)

        elif action == action_supprimer:
            nom = self.table_cultures.item(row, 0).text()
            self.debug("→ Supprimer culture :", nom)
            self.supprimer_culture(nom)

        elif action == action_ajouter:
            self.debug("→ Ajouter culture")
            self.ajout_culture()
    # ----------------------

    # ----------------------
    # Menu contextuel fertilisant liste (droite)
    def menu_context_fert_droite(self, pos):
        self.debug("=== menu_context_fert_droite ===")

        row = self.table_fertilisants.currentRow()
        self.debug("Position clic :", pos, "| Ligne sélectionnée :", row)

        if row < 0:
            self.debug("⛔ Aucune ligne sélectionnée → menu annulé")
            return

        menu = QMenu()

        action_utiliser = menu.addAction("Utiliser ce fertilisant")
        if not self.culture_active:
            action_utiliser.setEnabled(False)
            self.debug("Action 'Utiliser' désactivée (pas de culture active)")

        menu.addSeparator()
        action_modifier = menu.addAction("Modifier le fertilisant")
        menu.addSeparator()
        action_ajouter = menu.addAction("Ajouter un fertilisant")
        action_supprimer = menu.addAction("Supprimer le fertilisant")

        action = menu.exec(self.table_fertilisants.mapToGlobal(pos))
        nom = self.table_fertilisants.item(row, 0).text()

        self.debug("Action sélectionnée :", action.text() if action else None)
        self.debug("Fertilisant concerné :", nom)

        if action == action_utiliser:
            self.debug("→ Utiliser fertilisant :", nom)
            self.ajouter_fert_utiliser(nom)

        elif action == action_modifier:
            self.debug("→ Modifier fertilisant :", nom)
            self.modifier_fert(nom)

        elif action == action_supprimer:
            self.debug("→ Supprimer fertilisant :", nom)
            self.supprimer_fert(nom)

        elif action == action_ajouter:
            self.debug("→ Ajouter fertilisant")
            self.ajout_fert()
    # ----------------------

    # ----------------------
    # Menu contextuel fertilisant milieu
    def menu_context_fert_milieu(self, pos):
        self.debug("=== menu_context_fert_milieu ===")

        row = self.table_utiliser.currentRow()
        self.debug("Position clic :", pos, "| Ligne sélectionnée :", row)

        if row < 0:
            self.debug("⛔ Aucune ligne sélectionnée → menu annulé")
            return

        menu = QMenu()
        action_enlever = menu.addAction("Enlever ce fertilisant")

        action = menu.exec(self.table_utiliser.mapToGlobal(pos))
        self.debug("Action sélectionnée :", action.text() if action else None)

        if action == action_enlever:
            nom = self.table_utiliser.item(row, 0).text()
            self.debug("→ Enlever fertilisant :", nom)
            self.enlever_fert_utiliser(nom)
    # ----------------------

    # ----------------------
    # Modifier une culture
    def modifier_culture(self, nom):
        culture = self.cultures.get(nom)
        if not culture:
            return
        culture_complet = culture.copy()
        culture_complet["nom"] = nom
        self.ajout_culture(culture_complet)
    # ----------------------

    # ----------------------
    # Supprmier une culture
    def supprimer_culture(self, nom):
        self.debug("=== supprimer_culture ===")
        self.debug("Culture demandée :", nom)

        if nom not in self.cultures:
            self.debug("⛔ Culture introuvable")
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer la culture « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No
        )

        self.debug("Réponse utilisateur :", "Oui" if reply == QMessageBox.Yes else "Non")

        if reply != QMessageBox.Yes:
            self.debug("Suppression annulée")
            return

        del self.cultures[nom]
        self.debug("Culture supprimée de la mémoire")

        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cultures, f, indent=2, ensure_ascii=False)
            self.debug("Fichier cultures réécrit")

        self.remplir_tableaux()
        self.debug("Tableaux rafraîchis après suppression culture")
    # ----------------------

    # ----------------------
    # Modifier un fertilisant
    def modifier_fert(self, nom):
        self.debug("=== modifier_fert ===")
        self.debug("Fertilisant demandé :", nom)

        fert = next((f for f in self.fert_base if f["nom"] == nom), None)
        if not fert:
            self.debug("⛔ Fertilisant introuvable")
            return

        self.debug("Ouverture fenêtre modification fertilisant")
        self.ajout_fert(fert)
    # ----------------------

    # ----------------------
    # Supprimer un fertiliant
    def supprimer_fert(self, nom):
        self.debug("=== supprimer_fert ===")
        self.debug("Fertilisant demandé :", nom)

        fert = next((f for f in self.fert_base if f["nom"] == nom), None)
        if not fert:
            self.debug("⛔ Fertilisant introuvable")
            return

        reply = QMessageBox.question(
            self,
            "Confirmation",
            f"Voulez-vous vraiment supprimer le fertilisant « {nom} » ?",
            QMessageBox.Yes | QMessageBox.No
        )

        self.debug("Réponse utilisateur :", "Oui" if reply == QMessageBox.Yes else "Non")

        if reply != QMessageBox.Yes:
            self.debug("Suppression annulée")
            return

        self.fert_base = [f for f in self.fert_base if f["nom"] != nom]
        self.debug("Fertilisant supprimé de la mémoire")

        with open(FERT_FILE, "w", encoding="utf-8") as f:
            json.dump(self.fert_base, f, indent=2, ensure_ascii=False)
            self.debug("Fichier fertilisants réécrit")

        self.remplir_tableaux()
        self.debug("Tableaux rafraîchis après suppression fertilisant")
    # ----------------------

    # ----------------------
    # Ajouter un fertilisant dans la table du milieu
    def ajouter_fert_utiliser(self, nom):
        self.debug("=== ajouter_fert_utiliser ===")
        self.debug("Fertilisant demandé :", nom)

        fert = next((f for f in self.fert_base if f["nom"] == nom), None)
        if not fert:
            self.debug("⛔ Fertilisant introuvable")
            return

        for row in range(self.table_utiliser.rowCount()):
            if self.table_utiliser.item(row, 0).text() == nom:
                self.debug("⚠️ Fertilisant déjà présent dans table_utiliser")
                return

        row = self.table_utiliser.rowCount()
        self.table_utiliser.insertRow(row)

        self.table_utiliser.setItem(row, 0, QTableWidgetItem(fert["nom"]))
        self.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert.get("N"))))
        self.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert.get("P"))))
        self.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert.get("K"))))
        self.table_utiliser.setItem(row, 4, QTableWidgetItem("0"))

        self.debug(f"Fertilisant ajouté à table_utiliser ligne {row}")

        self.aligner_table_utiliser()
        self.debug("Alignement table_utiliser effectué")

        self.debug("Affichage de lbl_modifie")
        self.mark_doses_modifiees(True)
    # ----------------------

    # ----------------------
    # Enlever un fertilisant
    def enlever_fert_utiliser(self, nom):
        self.debug("=== enlever_fert_utiliser ===")
        self.debug("Fertilisant demandé :", nom)

        for row in range(self.table_utiliser.rowCount()):
            if self.table_utiliser.item(row, 0).text() == nom:
                self.table_utiliser.removeRow(row)
                self.debug(f"Fertilisant retiré de table_utiliser ligne {row}")
                return

        self.debug("⚠️ Fertilisant non trouvé dans table_utiliser")

        self.debug("Affichage de lbl_modifie")
        self.mark_doses_modifiees(True)
    # ----------------------

    # Ne pas autoriser sans validations de l'utilisateur le changement de culture sans enregistrement
    # ----------------------
    def culture_selectionnee_changed(self, row, column):
        self.debug("\n=== culture_selectionnee_changed ===")

        row = self.table_cultures.currentRow()
        self.debug("Ligne sélectionnée :", row)

        if row < 0:
            self.debug("⛔ Aucune ligne sélectionnée")
            return

        item = self.table_cultures.item(row, 0)
        if not item:
            self.debug("⛔ Item culture inexistant")
            return

        nom_culture = item.text()
        self.debug("Culture cliquée :", nom_culture)
        self.debug("Culture active actuelle :", self.culture_active)

        if self.culture_active == nom_culture:
            self.debug("↩️ Même culture → aucun changement")
            return

        # --- Vérification modifications non enregistrées ---
        if self.culture_active and self.table_modifiees:
            self.debug("⚠️ Doses modifiées détectées pour :", self.culture_active)

            reply = QMessageBox.question(
                self,
                "Changement de culture",
                "Voulez-vous quitter sans enregistrer ?",
                QMessageBox.Yes | QMessageBox.Save | QMessageBox.Cancel
            )

            self.debug(
                "Choix utilisateur :",
                "Cancel" if reply == QMessageBox.Cancel else
                "Save" if reply == QMessageBox.Save else
                "Yes"
            )

            if reply == QMessageBox.Cancel:
                self.debug("❌ Changement de culture annulé")
                return

            if reply == QMessageBox.Save:
                self.debug("💾 Enregistrement des doses avant changement")
                self.enregistrer_doses_culture()
                self.table_modifiees = False

        # --- Reset style lignes ---
        for r in range(self.table_cultures.rowCount()):
            it = self.table_cultures.item(r, 0)
            if it:
                font = it.font()
                font.setBold(False)
                it.setFont(font)

        # --- Mise en gras sélection ---
        font = item.font()
        font.setBold(True)
        item.setFont(font)

        self.culture_active = nom_culture
        self.debug("✅ Nouvelle culture active :", self.culture_active)

        culture = self.cultures.get(nom_culture, {})
        surface = culture.get("surface", 0)
        self.debug("Surface culture :", surface)

        self.lbl_culture_active.setText(nom_culture)
        self.lbl_dose_surface.setText(f"Doses pour la surface ({surface} m²)")
        self.table_cultures.selectRow(row)

        # --- Chargement fertilisants utilisés ---
        self.table_utiliser.setRowCount(0)
        ferts_utilises = culture.get("fertilisants_utilises", [])
        self.debug("Fertilisants utilisés enregistrés :", ferts_utilises)

        if ferts_utilises:
            has_doses = any(f.get("dose_ha") is not None for f in ferts_utilises)
            
            if has_doses:
                resultats = []
                for fert in ferts_utilises:
                    fert_base = next((f for f in self.fert_base if f["nom"] == fert["nom"]), {})
                    doses_ha = fert.get("doses_ha", 0)

                    N = doses_ha * fert_base.get("N", 0) / 100
                    P = doses_ha * fert_base.get("P", 0) / 100
                    K = doses_ha * fert_base.get("K", 0) / 100

                    resultats.append({
                        "nom": fert["nom"],
                        "doses_ha": doses_ha,
                        "N": N,
                        "P": P,
                        "K": K
                    })

                    self.debug(f"🧮 {fert['nom']} → N:{N} P:{P} K:{K}")

                self.table_doses_ha.setRowCount(0)
                self.table_dose_surface.setRowCount(0)

                self.remplir_table_doses_ha(resultats)
                self.calculer_doses_surface(resultats, culture)

                self.table_modifiees = False
                self.debug("🔁 Flag table_modifiees réinitialisé")
                
                self.debug("Suppression de l'affiche de lbl_modifie")
                self.mark_doses_modifiees(False)
                
            else:

                for fert in ferts_utilises:
                    fert_base = next((f for f in self.fert_base if f["nom"] == fert["nom"]), None)
                    if not fert_base:
                        self.debug("⛔ Fertilisant introuvable dans base :", fert["nom"])
                        continue

                    row_util = self.table_utiliser.rowCount()
                    self.table_utiliser.insertRow(row_util)

                    self.table_utiliser.setItem(row_util, 0, QTableWidgetItem(fert["nom"]))
                    self.table_utiliser.setItem(row_util, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
                    self.table_utiliser.setItem(row_util, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
                    self.table_utiliser.setItem(row_util, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
                    self.table_utiliser.setItem(row_util, 4, QTableWidgetItem(str(fert.get("doses_ha", 0))))

                    self.debug(f"➕ Fertilisant chargé : {fert['nom']} (ligne {row_util})")

                self.aligner_table_utiliser()
                
                self.debug("Suppression de l'affiche de lbl_modifie")
                self.mark_doses_modifiees(False)
        else:
            self.debug("ℹ️ Aucun fertilisant enregistré → chargement par défaut")
            self.charger_ferts_pour_culture(nom_culture)

        # --- Calcul doses ---
        
    # ----------------------

    # ----------------------
    # Charger les fertilisants de la culture selectionnée
    def charger_ferts_pour_culture(self, nom_culture):
        self.debug("\n=== charger_ferts_pour_culture ===")
        self.debug("Culture demandée :", nom_culture)

        culture = self.cultures.get(nom_culture)
        if not culture:
            self.debug("⛔ Culture introuvable")
            self.table_utiliser.setRowCount(0)
            return

        self.table_utiliser.setRowCount(0)
        self.table_doses_ha.setRowCount(0)
        self.table_dose_surface.setRowCount(0)

        ferts_utilises = culture.get("fertilisants_utilises", [])
        self.debug("Fertilisants culture :", ferts_utilises)

        for f in ferts_utilises:
            nom = f["nom"]
            fert_base = next((fb for fb in self.fert_base if fb["nom"] == nom), None)
            if not fert_base:
                self.debug("⛔ Fertilisant manquant dans base :", nom)
                continue

            row = self.table_utiliser.rowCount()
            self.table_utiliser.insertRow(row)

            self.table_utiliser.setItem(row, 0, QTableWidgetItem(nom))
            self.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert_base.get("N", 0))))
            self.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert_base.get("P", 0))))
            self.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert_base.get("K", 0))))
            self.table_utiliser.setItem(row, 4, QTableWidgetItem(str(f.get("doses_ha", 0))))

            self.debug(f"➕ table_utiliser ← {nom}")

        for f in ferts_utilises:
            nom = f["nom"]
            doses_ha = f.get("doses_ha", 0)
            fert_base = next((fb for fb in self.fert_base if fb["nom"] == nom), None)
            if not fert_base:
                continue

            N = doses_ha * fert_base.get("N", 0) / 100
            P = doses_ha * fert_base.get("P", 0) / 100
            K = doses_ha * fert_base.get("K", 0) / 100

            row = self.table_doses_ha.rowCount()
            self.table_doses_ha.insertRow(row)

            self.table_doses_ha.setItem(row, 0, QTableWidgetItem(nom))
            self.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{N:.1f}"))
            self.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{P:.1f}"))
            self.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{K:.1f}"))
            self.table_doses_ha.setItem(row, 4, QTableWidgetItem(f"{doses_ha:.1f}"))

            self.debug(f"📊 table_doses_ha ← {nom}")

        self.calculer_doses_surface(
            [
                {
                    "nom": f["nom"],
                    "doses_ha": f.get("doses_ha", 0),
                    "N": self.table_doses_ha.item(i, 1).text(),
                    "P": self.table_doses_ha.item(i, 2).text(),
                    "K": self.table_doses_ha.item(i, 3).text(),
                }
                for i, f in enumerate(ferts_utilises)
            ],
            culture
        )

        self.debug("📐 Doses surface recalculées")
    # ----------------------
    
    # Base pour envoyer vers calcul auto ou strict
    # ----------------------
    def calculer_doses(self):
        self.debug("\n=== calculer_doses ===")

        # Vérifier culture
        if not hasattr(self, "culture_active") or not self.culture_active:
            self.debug("⛔ Aucune culture active")
            QMessageBox.warning(self, "Erreur", "Aucune culture sélectionnée")
            return

        culture = self.cultures[self.culture_active]
        Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

        self.debug(
            f"Culture active : {self.culture_active}",
            f"Besoins → N={Nb} P={Pb} K={Kb}"
        )

        # --- Fertilisants table milieu ---
        ferts = []
        for row in range(self.table_utiliser.rowCount()):
            fert = {
                "nom": self.table_utiliser.item(row, 0).text(),
                "N": float(self.table_utiliser.item(row, 1).text()),
                "P": float(self.table_utiliser.item(row, 2).text()),
                "K": float(self.table_utiliser.item(row, 3).text())
            }
            ferts.append(fert)

        self.debug(f"Fertilisants table_utiliser ({len(ferts)}) :", ferts)

        self.table_doses_ha.setRowCount(0)
        self.table_dose_surface.setRowCount(0)

        # --- Choix du mode ---
        if not ferts:
            self.debug("➡️ Aucun fertilisant manuel → mode AUTO forcé")
            resultats = self.calcul_auto(Nb, Pb, Kb)
        else:
            from ui.dialog_mode_calcul import ChoixModeCalcul
            dlg = ChoixModeCalcul(self)
            if dlg.exec() != QDialog.Accepted:
                self.debug("❌ Choix du mode annulé")
                return

            mode = dlg.mode
            self.debug("Mode choisi :", mode)

            if mode == "auto":
                resultats = self.calcul_auto(Nb, Pb, Kb)
            else:
                resultats = self.calcul_strict(Nb, Pb, Kb, ferts)

        self.debug("Résultats calcul :", resultats)

        self.remplir_table_doses_ha(resultats["fertilisants"])
        self.calculer_doses_surface(resultats["fertilisants"], culture)
    # ----------------------

    # Calcul auto
    # ----------------------
    def calcul_auto(self, Nb, Pb, Kb):
        self.debug("\n=== calcul_auto ===")

        self.fertilisants_autorises = []

        for row in range(self.table_fertilisants.rowCount()):
            cell_widget = self.table_fertilisants.cellWidget(row, 6)
            if not cell_widget:
                self.debug(f"⛔ Pas de widget checkbox ligne {row}")
                continue

            chk = cell_widget.layout().itemAt(0).widget()
            nom = self.table_fertilisants.item(row, 0).text()

            self.debug(f"Ligne {row} → {nom} | checked={chk.isChecked()}")

            if chk.isChecked():
                fert = next((f for f in self.fert_base if f["nom"] == nom), None)
                if not fert:
                    self.debug("⛔ Fertilisant absent de fert_base :", nom)
                    continue
                self.fertilisants_autorises.append(fert)

        self.debug(
            f"Fertilisants autorisés ({len(self.fertilisants_autorises)}) :",
            [f["nom"] for f in self.fertilisants_autorises]
        )

        if not self.fertilisants_autorises:
            self.debug("❌ Aucun fertilisant autorisé → abandon")
            return {"fertilisants": []}

        prob = pulp.LpProblem("Optimisation_Fertilisants", pulp.LpMinimize)

        noms = [f["nom"] for f in self.fertilisants_autorises]
        x = {nom: pulp.LpVariable(f"x_{nom}", cat="Binary") for nom in noms}
        y = {nom: pulp.LpVariable(f"y_{nom}", lowBound=0) for nom in noms}

        self.debug("Variables x :", list(x.keys()))
        self.debug("Variables y :", list(y.keys()))

        max_fertilisants = 4
        penalite_nb_fertilisants = 5
        M = 10000

        prob += (
            pulp.lpSum((y[f["nom"]] / f["conditionnement"]) * f["prix"]
                    for f in self.fertilisants_autorises)
            + penalite_nb_fertilisants
            * pulp.lpSum(x[f["nom"]] for f in self.fertilisants_autorises)
        )

        self.debug("Objectif OK")

        prob += pulp.lpSum(y[f["nom"]] * f["N"] / 100 for f in self.fertilisants_autorises) == Nb
        prob += pulp.lpSum(y[f["nom"]] * f["P"] / 100 for f in self.fertilisants_autorises) == Pb
        prob += pulp.lpSum(y[f["nom"]] * f["K"] / 100 for f in self.fertilisants_autorises) == Kb

        self.debug("Contraintes NPK posées")

        for f in self.fertilisants_autorises:
            prob += y[f["nom"]] <= M * x[f["nom"]]
            self.debug(f"Lien x/y :", f["nom"])

        prob += pulp.lpSum(x[f["nom"]] for f in self.fertilisants_autorises) <= max_fertilisants
        self.debug("Limite nb fertilisants =", max_fertilisants)

        self.debug("=== Solveur CBC ===")
        prob.solve(pulp.PULP_CBC_CMD(msg=self.DEBUG))

        self.debug("Status solveur :", pulp.LpStatus[prob.status])

        fertilisants = []
        for f in self.fertilisants_autorises:
            dose = y[f["nom"]].value()
            self.debug(f"Résultat {f['nom']} → dose = {dose}")

            if dose and dose > 0.01:
                fertilisants.append({
                    "nom": f["nom"],
                    "doses_ha": round(dose, 1),
                    "N": round(dose * f["N"] / 100, 1),
                    "P": round(dose * f["P"] / 100, 1),
                    "K": round(dose * f["K"] / 100, 1),
                })

        self.debug("Fertilisants FINALS :", [f["nom"] for f in fertilisants])
        return {"fertilisants": fertilisants}
    # ----------------------

    # Calcul strict
    # ----------------------
    def calcul_strict(self, Nb, Pb, Kb, ferts):
        self.debug("\n=== calcul_strict ===")
        self.debug("Besoins :", Nb, Pb, Kb)
        self.debug("Fertilisants :", ferts)

        if len(ferts) < 3:
            self.debug("⛔ Strict impossible (<3 fertilisants)")
            QMessageBox.warning(
                self, "Erreur",
                "Le mode strict nécessite au moins 3 fertilisants"
            )
            return {"fertilisants": []}

        A = np.array([
            [f["N"] / 100 for f in ferts],
            [f["P"] / 100 for f in ferts],
            [f["K"] / 100 for f in ferts],
        ])
        B = np.array([Nb, Pb, Kb])

        self.debug("Matrice A :", A)
        self.debug("Vecteur B :", B)

        doses, *_ = np.linalg.lstsq(A, B, rcond=None)
        self.debug("Doses brutes :", doses)

        resultats = []
        for dose, fert in zip(doses, ferts):
            dose = max(dose, 0)
            self.debug(f"{fert['nom']} → dose corrigée = {dose}")

            resultats.append({
                "nom": fert["nom"],
                "doses_ha": dose,
                "N": dose * fert["N"] / 100,
                "P": dose * fert["P"] / 100,
                "K": dose * fert["K"] / 100,
            })

        return {"fertilisants": resultats}
    # ----------------------

    # Remplissage des doses par ha dans table_doses_ha
    # ----------------------
    def remplir_table_doses_ha(self, resultats):
        self.debug("\n=== remplir_table_doses_ha ===")
        total_N = total_P = total_K = 0

        for r in resultats:
            self.debug(f"Fertil. {r['nom']} → N={r['N']} P={r['P']} K={r['K']} doses_ha={r['doses_ha']}")
            row = self.table_doses_ha.rowCount()
            self.table_doses_ha.insertRow(row)

            self.table_doses_ha.setItem(row, 0, QTableWidgetItem(r["nom"]))
            self.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{r['N']:.1f}"))
            self.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{r['P']:.1f}"))
            self.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{r['K']:.1f}"))
            self.table_doses_ha.setItem(row, 4, QTableWidgetItem(f"{r['doses_ha']:.1f}"))

            total_N += r["N"]
            total_P += r["P"]
            total_K += r["K"]

        # Ligne TOTAL
        row = self.table_doses_ha.rowCount()
        self.table_doses_ha.insertRow(row)
        self.debug(f"Ligne TOTAL → N={total_N} P={total_P} K={total_K}")

        self.table_doses_ha.setItem(row, 0, QTableWidgetItem("TOTAL"))
        self.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{total_N:.1f}"))
        self.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{total_P:.1f}"))
        self.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{total_K:.1f}"))
        self.table_doses_ha.setItem(row, 4, QTableWidgetItem(""))

        font = QFont()
        font.setBold(True)

        for col in range(self.table_doses_ha.columnCount()):
            item = self.table_doses_ha.item(row, col)
            if item:
                item.setFont(font)
                item.setBackground(QBrush(QColor("#e6e6e6")))

        self.table_doses_ha.setRowHeight(row, 32)
        self.aligner_table_doses_ha()
    # ----------------------

    # Remplissage des doses pour la surface dans table_doses_surface
    # ----------------------
    def calculer_doses_surface(self, resultats, culture):
        self.debug("\n=== calculer_doses_surface ===")
        surface = culture.get("surface", 1)
        self.debug(f"Surface culture = {surface} m²")

        self.table_dose_surface.setRowCount(0)
        total_prix = total_dose = 0        

        for r in resultats:
            dose_surface = r["doses_ha"] * surface / 10000
            fert = next((f for f in self.fert_base if f["nom"] == r["nom"]), None)

            if not fert:
                self.debug(f"⚠️ Fertilisant {r['nom']} introuvable dans fert_base")
                continue

            conditionnement = fert.get("conditionnement", 1)
            unite = fert.get("unite", "kg")
            prix_unitaire = fert.get("prix", 0)
            prix_kg = prix_unitaire / conditionnement
            prix_dose = prix_kg * dose_surface
            quantite = math.ceil(dose_surface / conditionnement) if conditionnement > 0 else 0
            prix_ht = quantite * prix_unitaire

            total_prix += prix_ht
            total_dose += prix_dose

            self.debug(f"{r['nom']} → dose_surface={dose_surface:.2f} {unite}, prix_dose={prix_dose:.2f}€, quantite={quantite}, prix_ht={prix_ht:.2f}€")

            row = self.table_dose_surface.rowCount()
            self.table_dose_surface.insertRow(row)
            self.table_dose_surface.setItem(row, 0, QTableWidgetItem(r["nom"]))
            self.table_dose_surface.setItem(row, 1, QTableWidgetItem(f"{dose_surface:.1f} {unite}"))
            self.table_dose_surface.setItem(row, 2, QTableWidgetItem(f"{prix_dose:.2f} €"))
            self.table_dose_surface.setItem(row, 3, QTableWidgetItem(f"{conditionnement} {unite}"))
            self.table_dose_surface.setItem(row, 4, QTableWidgetItem(f"{prix_unitaire:.2f} €"))
            self.table_dose_surface.setItem(row, 5, QTableWidgetItem(str(quantite)))
            self.table_dose_surface.setItem(row, 6, QTableWidgetItem(f"{prix_ht:.2f} €"))

        # Ligne TOTAL
        row = self.table_dose_surface.rowCount()
        self.table_dose_surface.insertRow(row)
        self.debug(f"Ligne TOTAL → total_dose={total_dose:.2f}€, total_prix={total_prix:.2f}€")

        self.table_dose_surface.setItem(row, 0, QTableWidgetItem("TOTAL"))
        self.table_dose_surface.setItem(row, 1, QTableWidgetItem())
        self.table_dose_surface.setItem(row, 2, QTableWidgetItem(f"{total_dose:.2f} €"))
        self.table_dose_surface.setItem(row, 3, QTableWidgetItem())
        self.table_dose_surface.setItem(row, 4, QTableWidgetItem())
        self.table_dose_surface.setItem(row, 5, QTableWidgetItem())
        self.table_dose_surface.setItem(row, 6, QTableWidgetItem(f"{total_prix:.2f} €"))

        font = QFont()
        font.setBold(True)
        for col in range(self.table_dose_surface.columnCount()):
            item = self.table_dose_surface.item(row, col)
            if item:
                item.setFont(font)
                item.setBackground(QBrush(QColor("#e6e6e6")))

        self.table_dose_surface.setRowHeight(row, 32)
        self.aligner_table_dose_surface()
    # ----------------------

    # ----------------------
    def table_doses_ha_modifiee(self, row, column):
        self.table_modifiees = True
        item = self.table_doses_ha.item(row, column)
        text = item.text() if item else "None"
        self.debug(f"⚠️ Modification détectée à la cellule ({row}, {column}) → {text}")
    # ----------------------

    # Au double clique d'un fertilisant dans table_fertilisants -> ajout dans table_utilise
    # ----------------------
    def double_clic_fertilisant(self, row, column):
        item = self.table_fertilisants.item(row, 0)
        if not item:
            self.debug(f"⚠️ Double-clic fertilisant invalide sur la ligne {row}")
            return
        
        nom_fert = item.text()
        if not self.culture_active:
            QMessageBox.warning(
                self,
                "Aucune culture sélectionnée",
                "Veuillez d'abord sélectionner une culture"
            )
            self.debug(f"⚠️ Tentative d'ajout de fertilisant '{nom_fert}' sans culture active")
            return
        
        self.debug(f"Double-clic fertilisant '{nom_fert}' → ajout à la culture '{self.culture_active}'")
        self.ajouter_fert_utiliser(nom_fert)
        
        self.table_modifiees = True
        self.debug("Ajout fertilisant utiliser -> table_modifier = True")
    # ----------------------

    # au double clique sur un fertilisant dans table_utiliser -> retirer de cette table
    # ----------------------
    def double_clic_fertilisant_enlever(self, row, column):
        item = self.table_utiliser.item(row, 0)
        if not item:
            self.debug(f"⚠️ Double-clic fertilisant à enlever invalide sur la ligne {row}")
            return
        
        nom_fert = item.text()
        self.debug(f"Double-clic fertilisant '{nom_fert}' → suppression de la table 'utiliser'")
        self.enlever_fert_utiliser(nom_fert)
        
        self.table_modifiees = True
        self.debug("Suppression fertilisant utiliser -> table_modifier = True")
    # ----------------------

    # Aligne toutes les colonnes de table_dose_surface à droite sauf la colonne nom
    # ----------------------
    def aligner_table_dose_surface(self):
        for row in range(self.table_dose_surface.rowCount()):
            for col in range(self.table_dose_surface.columnCount()):
                item = self.table_dose_surface.item(row, col)
                if not item:
                    continue

                if col == 0:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.debug("✅ Table 'dose_surface' alignée")
    # ----------------------

    # Aligne toutes les colonnes de table_culture à droite sauf la colonne nom
    # ----------------------
    def aligner_table_culture(self):
        for row in range(self.table_cultures.rowCount()):
            for col in range(self.table_cultures.columnCount()):
                item = self.table_cultures.item(row, col)
                if not item:
                    continue

                if col == 0:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.debug("✅ Table 'cultures' alignée")
    # ----------------------

    # Aligne toutes les colonnes de table_doses_ha à droite sauf la colonne nom
    # ----------------------
    def aligner_table_doses_ha(self):
        for row in range(self.table_doses_ha.rowCount()):
            for col in range(self.table_doses_ha.columnCount()):
                item = self.table_doses_ha.item(row, col)
                if not item:
                    continue

                if col == 0:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.debug("✅ Table 'doses_ha' alignée")
    # ----------------------

    # Aligne toutes les colonnes de table_fertilisants à droite sauf la colonne nom
    # ----------------------
    def aligner_table_fertilisants(self):
        for row in range(self.table_fertilisants.rowCount()):
            for col in range(self.table_fertilisants.columnCount()):
                item = self.table_fertilisants.item(row, col)
                if not item:
                    continue

                if col == 0:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.debug("✅ Table 'fertilisants' alignée")
    # ----------------------

    # Aligne toutes les colonnes de table_utilise à droite sauf la colonne nom
    # ----------------------
    def aligner_table_utiliser(self):
        for row in range(self.table_utiliser.rowCount()):
            for col in range(self.table_utiliser.columnCount()):
                item = self.table_utiliser.item(row, col)
                if not item:
                    continue

                if col == 0:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.debug("✅ Table 'utiliser' alignée")
    # ----------------------

    # fonction qui centralise l'ajustement des colonnes
    # ----------------------
    def setup_table_header(self, table, stretch_col=0):
        """
        Configure le header d'une table : 
        - La colonne stretch_col prend tout l'espace restant
        - Les autres colonnes s'ajustent automatiquement au contenu
        """
        header = table.horizontalHeader()
        for col in range(table.columnCount()):
            if col == stretch_col:
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
    # ----------------------

    # Fonction de debug
    # ----------------------
    def debug(self, *args):
        if getattr(self, "DEBUG", False):
            print("[DEBUG]", *args)
    # ----------------------

    # Bar de menu
    # ----------------------
    def creer_menu(self):
        menu_bar = self.menuBar()

        # Fichier
        # ======================
        menu_fichier = menu_bar.addMenu("Fichiers")
        
        action_vider_table_milieux = QAction("Vider tableaux", self)
        action_vider_table_milieux.triggered.connect(self.vider_table_milieux)
        menu_fichier.addAction(action_vider_table_milieux)
        
        action_vider_table_calcul = QAction("Vider calculs", self)
        action_vider_table_calcul.triggered.connect(self.vider_table_calcul)
        menu_fichier.addAction(action_vider_table_calcul)

        menu_fichier.addSeparator()

        action_parametres = QAction("Paramètres", self)
        action_parametres.triggered.connect(self.ouvrir_parametres)
        menu_fichier.addAction(action_parametres)

        menu_fichier.addSeparator()

        action_quitter = QAction("Quitter", self)
        action_quitter.setShortcut(QKeySequence.Quit)
        action_quitter.triggered.connect(self.close)
        menu_fichier.addAction(action_quitter)        
        # ======================

        # Édition
        # ======================
        menu_edition = menu_bar.addMenu("Édition")

        action_nouvelle_culture = QAction("Nouvelle culture", self)
        action_nouvelle_culture.triggered.connect(self.ajout_culture)
        menu_edition.addAction(action_nouvelle_culture)

        action_nouveau_fertiisant = QAction("Nouveau fertilisant", self)
        action_nouveau_fertiisant.triggered.connect(self.ajout_fert)
        menu_edition.addAction(action_nouveau_fertiisant)     
        # ======================

        # Outils
        # ======================
        menu_outils = menu_bar.addMenu("Outils")

        action_debug = QAction("Redémarrer en mode debug", self)
        action_debug.triggered.connect(self.redemarrer_debug)
        menu_outils.addAction(action_debug)     
        # ======================

        # Aide
        # ======================
        menu_aide = menu_bar.addMenu("Aide")

        action_aide = QAction("Aide", self)
        action_aide.triggered.connect(self.afficher_aide)
        menu_aide.addAction(action_aide)

        menu_aide.addSeparator()

        action_maj = QAction("Vérifier les mises à jour", self)
        action_maj.setEnabled(False)
        menu_aide.addAction(action_maj)

        menu_aide.addSeparator()

        action_aporpos = QAction("À propos", self)
        action_aporpos.triggered.connect(self.afficher_apropos)
        menu_aide.addAction(action_aporpos)
        # ======================

    # ----------------------

    # Actions ouvrir paramètres
    # ----------------------
    def ouvrir_parametres(self):
        QMessageBox.information(self, "Paramètres", "À venir")
    # ----------------------

    # Redemarrer en mode DEBUG
    def redemarrer_debug(self):
        self.DEBUG = not self.DEBUG
        etat = "Activé" if self.DEBUG else "Désactivé"
        QMessageBox.information(
            self,
            "Mode debug",
            f"Mode debug {etat}"
        )
        self.debug("DEBUG =", self.DEBUG)
    # ----------------------

    # Aide
    # ----------------------
    def afficher_aide(self):
        QMessageBox.information(self, "Aide", "Aide à la gestion de fertilisants")
    # ----------------------

    # A propos
    # ----------------------
    def afficher_apropos(self):
        QMessageBox.information(
            self,
            "À propos",
            "Gestion Fertiliant\nVersion 2.1.1\n©Clément THIEULEUX"
        )
    # ----------------------

    # Vider tableau calculs
    # ----------------------
    def vider_table_calcul(self):
        self.debug("Action : Vider calculs (résultats)")

        # Table dose ha
        self._clear_table(self.table_doses_ha)

        # Table dose surface
        self._clear_table(self.table_dose_surface)

        QMessageBox.information(
            self,
            "Tableaux vidés",
            "Les tableaux intermédiaires ont été vidés"
            )
        
        self.table_modifiees = True
        self.debug("Tableaux calculs supprimé -> table_modifier = True")
    # ----------------------

    # Vider tableau fertilisant (tableu_utilise, table_doses_ha, table_doses_surface)
    # ----------------------
    def vider_table_milieux(self):
        self.debug("Action : Vider tableaux (millieux)")

        # Table fertiliants utilisés
        self._clear_table(self.table_utiliser)

        # Table dose ha
        self._clear_table(self.table_doses_ha)

        # Table dose surface
        self._clear_table(self.table_dose_surface)

        QMessageBox.information(
            self,
            "Tableaux vidés",
            "Les tableaux intermédiaires ont été vidés"
            )
        
        self.table_modifiees = True
        self.debug("Tableaux intermédiaires supprimé -> table_modifier = True")
    # ----------------------

    # Fonction de vidage de tableaux
    # ----------------------
    def _clear_table(self, table):
        if table is not None:
            table.setRowCount(0)
    # ----------------------

    # Enregistrement cultures au changements de la culture
    # ----------------------
    def enregistrer_doses_culture(self):
        if not self.culture_active:
            self.debug("⚠️ Aucune culture active, rien à enregistrer")
            return

        culture = self.cultures.get(self.culture_active)
        if not culture:
            self.debug(f"⚠️ Culture '{self.culture_active}' introuvable")
            return

        fertilisants = []
        self.debug(f"=== Enregistrement des doses pour '{self.culture_active}' ===")

        # ======================
        # Cas 1 : doses ha calculées
        # ======================
        doses_trouvees = False
        for row in range(self.table_doses_ha.rowCount()):
            nom_item = self.table_doses_ha.item(row, 0)

            if nom_item is None:
                continue

            nom = nom_item.text()
            if nom == TOTAL_LABEL:
                continue

            dose_item = self.table_doses_ha.item(row, 4)
            if dose_item is None:
                continue

            try:
                doses_ha = float(dose_item.text())
            except ValueError:
                doses_ha = 0
            
            fertilisants.append({
                "nom": nom,
                "doses_ha": doses_ha
            })

            doses_trouvees = True
            self.debug(f" Dose calculée : {nom} = {doses_ha} kg/ha")

        # ======================
        # Cas 2 : pas de doses mais fertilisant
        # ======================
        if not doses_trouvees:
            self.debug("Aucune dose calculés, vérification des fertilisants utilisés")

            for row in range(self.table_utiliser.rowCount()):
                nom_item = self.table_utiliser.item(row, 0)
                if nom_item is None:
                    continue
                
                nom = nom_item.text()
                fertilisants.append({
                    "nom": nom,
                    "doses_ha": None
                })

                self.debug(f" Fertilisants enregistré sans dose : {nom}")

        # ======================
        # Cas 3 : rien à enregistrer -> suppression des fertilisant dans CULTURE_FILES
        # ======================
        if not fertilisants:
            self.debug("Aucun fertilisants à enregistrer → culture vidée")
            culture["fertilisants_utilises"] = fertilisants
            return
        
        # ======================
        # Sauvegarde JSON
        # ======================
        culture["fertilisants_utilises"] = fertilisants
        self.debug(f"→ {len(fertilisants)} fertilisants affectés à '{self.culture_active}'")

        try:
            with open(CULTURE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cultures, f, indent=2, ensure_ascii=False)

                self.debug(f" Enregistrement OK ({len(fertilisants)} fertilisants)")

        except Exception as e:
            self.debug(f"Erreur sauvegarde : {e}")
        
        self.mark_doses_modifiees(False)
        self.debug("Suppression de l'affiche de lbl_modifie")
    # ----------------------

    # Mettre a jour le badge de modification à chaque modifications des tableaux
    # ----------------------
    def mark_doses_modifiees(self, modifie=True):
        self.set_doses_modifiees = modifie
        self.lbl_modifie.setVisible(modifie)
    # ----------------------