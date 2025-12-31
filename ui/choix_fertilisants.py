from pathlib import Path
import sys
from paths import FERT_FILE, CULTURE_FILE, TOTAL_LABEL
import math

if getattr(sys, 'frozen', False):
    # Exécutable PyInstaller
    BASE_DIR = Path(sys._MEIPASS)
else:
    # Développement normal
    BASE_DIR = Path(__file__).parent

import json

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem
)

from PySide6.QtCore import Qt

from PySide6.QtGui import QIcon

from scipy.optimize import minimize
import numpy as np

class ChoixFertilisants(QWidget):
    def __init__(self, culture_nom, n_besoins, p_besoins, k_besoins):
        super().__init__()
        self.setWindowTitle(f"Fertilisants – {culture_nom}")
        self.setWindowIcon(QIcon("icon.ico"))
        self.resize(720, 400)

        self.culture_nom = culture_nom

        self.layout = QVBoxLayout(self)

        # ======================
        # Choix fertilisant
        # ======================
        top = QHBoxLayout()
        top.addWidget(QLabel("Choisir un fertilisant :"))

        self.combo = QComboBox()
        self.combo.setEditable(False)
        top.addWidget(self.combo)

        btn_add = QPushButton("Valider fertilisant")
        btn_add.clicked.connect(self.ajouter_fertilisant)
        top.addWidget(btn_add)

        self.layout.addLayout(top)

        # ======================
        # Tableau
        # ======================
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "Fertilisant", "N", "P", "K",
                "Dose (kg/ha)", "N apporté", "P apporté", "K apporté",
                "Action"
            ]
        )
        self.table.setColumnWidth(0, 260)
        self.layout.addWidget(self.table)



        # juste après l'initialisation du premier tableau
        self.surface_label = QLabel("Doses pour la surface réelle de la culture")
        self.layout.addWidget(self.surface_label)

        self.table_surface = QTableWidget(0, 7)  # 7 colonnes
        self.table_surface.setHorizontalHeaderLabels(
            [
                "Fertilisant",
                "Dose (kg)",
                "Condit unitaire",
                "Prix unitaire HT",
                "Quantité",
                "Prix HT",
                "Prix TTC"
            ]
        )
        self.layout.addWidget(self.table_surface)

        # ======================
        # Bouton calcul
        # ======================
        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(self.calcul_dose)
        self.layout.addWidget(btn_calcul)

        # ======================
        # Bouton enregistrer
        # ======================
        btn_save = QPushButton("Fermer et enregistrer")
        btn_save.clicked.connect(self.enregistrer)
        self.layout.addWidget(btn_save)

        # ======================
        # Données
        # ======================
        self.cultures = self.charger_cultures()
        self.fert_base = self.charger_fertilisants()

        self.init_table()

        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table_surface.setSizeAdjustPolicy(QTableWidget.AdjustToContents)


        self.recharger_combo()
        self.combo.activated.connect(self.on_combo_change)

        self.calculer_doses_surface()


    # ======================
    # Chargements
    # ======================
    def charger_cultures(self):
        """
        Charge les cultures depuis le fichier JSON.
        Si le fichier n'existe pas ou est vide/corrompu, crée un dictionnaire vide.
        """
        if not CULTURE_FILE.exists():
            # créer le fichier avec un dictionnaire vide
            with open(CULTURE_FILE, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
            return {}

        try:
            with open(CULTURE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except json.JSONDecodeError:
            # fichier vide ou JSON invalide → on retourne un dict vide
            return {}


    def charger_fertilisants(self):
        """
        Charge les fertilisants depuis le fichier JSON.
        Si le fichier n'existe pas ou est vide/corrompu, crée une liste vide.
        """
        if not FERT_FILE.exists():
            # créer le fichier avec une liste vide
            with open(FERT_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            return []

        try:
            with open(FERT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return data
        except json.JSONDecodeError:
            # fichier vide ou JSON invalide → on retourne une liste vide
            return []


    # ======================
    # Initialisation
    # ======================
    def init_table(self):
        self.table.setRowCount(0)
        for fert in self.cultures[self.culture_nom].get("fertilisants", []):
            self.ajouter_ligne_table(fert)
        self.ajouter_ligne_total()

    def recharger_combo(self):
        # Vider la combo
        self.combo.clear()

        # Récupérer les noms déjà ajoutés à la culture
        deja = {f["nom"] for f in self.cultures[self.culture_nom]["fertilisants"]}

        # Trier les fertilisants restants et ne garder que ceux non ajoutés
        ferts_trie = sorted([f for f in self.fert_base if f["nom"] not in deja],
                            key=lambda x: x["nom"].lower())

        # Ajouter à la combo
        for fert in ferts_trie:
            txt = f"{fert['nom']} (N:{fert['N']} P:{fert['P']} K:{fert['K']})"
            self.combo.addItem(txt, fert)



    def on_combo_change(self):
        if self.combo.currentData() == "__NEW__":
            # Ouvrir fenêtre ajouter fertilisant
            from .ajouter_fertilisant import AjouterFertilisantWindow
            self.ajout = AjouterFertilisantWindow()
            self.ajout.fertilisant_ajoute.connect(self.on_fert_base_added)
            self.ajout.show()
            self.combo.setCurrentIndex(-1)  # reset sélection

    # ======================
    # Actions
    # ======================
    def ajouter_fertilisant(self):
        fert = self.combo.currentData()
        if not isinstance(fert, dict):
            return

        # ajouter le fertilisant a la culture et au tableau
        self.cultures[self.culture_nom]["fertilisants"].append(fert)
        self.ajouter_ligne_table(fert)

        # recharger la combo tri + nouveau en bas
        self.recharger_combo()

        # selectionner automatiquement le fertiliant a jouter dans la combo
        index = self.combo.findData(fert)
        if index != -1:
            self.combo.setCurrentIndex(index)
        else:
            self.combo.setCurrentIndex(0) # mettre au premier de la liste

        # mettre a jour le total
        self.ajouter_ligne_total()

    def ajouter_ligne_table(self, fert):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(fert["nom"]))
        self.table.setItem(row, 1, QTableWidgetItem(str(fert["N"])))
        self.table.setItem(row, 2, QTableWidgetItem(str(fert["P"])))
        self.table.setItem(row, 3, QTableWidgetItem(str(fert["K"])))

        btn = QPushButton("Supprimer")
        btn.setProperty("fert", fert)
        btn.clicked.connect(self.supprimer_fertilisant)
        self.table.setCellWidget(row, 8, btn)

        self.table.resizeColumnsToContents()

    def supprimer_fertilisant(self):
        btn = self.sender()
        fert = btn.property("fert")

        self.cultures[self.culture_nom]["fertilisants"] = [
            f for f in self.cultures[self.culture_nom]["fertilisants"]
            if f["nom"] != fert["nom"]
        ]

        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, 8) == btn:
                self.table.removeRow(row)
                break

        self.recharger_combo()
        self.combo.setCurrentIndex(0)
        self.mettre_a_jour_total()

        self.ajouter_ligne_total()

    def on_fert_base_added(self):
        self.fert_base = self.charger_fertilisants()
        self.recharger_combo()

    # ======================
    # Enregistrer culture
    # ======================
    def enregistrer(self):
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.cultures, f, indent=2, ensure_ascii=False)
        self.close()

    # ======================
    # Calcul des doses
    # ======================
    def calcul_dose(self):
        self.optimiser_doses()
        self.calculer_doses_surface()
        self.table.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.table_surface.setSizeAdjustPolicy(QTableWidget.AdjustToContents)
        self.adjustSize()

    def mettre_a_jour_total(self):
        total_n = 0.0
        total_p = 0.0
        total_k = 0.0

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == TOTAL_LABEL:
                continue

            try:
                n = float(self.table.item(row, 5).text())
                p = float(self.table.item(row, 6).text())
                k = float(self.table.item(row, 7).text())
            except (ValueError, AttributeError):
                continue

            total_n += n
            total_p += p
            total_k += k

        # écrire dans la ligne TOTAL
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == TOTAL_LABEL:
                self.table.item(row, 5).setText(f"{total_n:.1f}")
                self.table.item(row, 6).setText(f"{total_p:.1f}")
                self.table.item(row, 7).setText(f"{total_k:.1f}")
                break

    def ajouter_ligne_total(self):
        # Supprimer l'ancien TOTAL s'il existe
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == TOTAL_LABEL:
                self.table.removeRow(row)
                break

        row = self.table.rowCount()
        self.table.insertRow(row)

        # Colonne 0 : label TOTAL
        total_item = QTableWidgetItem(TOTAL_LABEL)
        total_item.setFlags(Qt.ItemIsEnabled)
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setData(Qt.UserRole, TOTAL_LABEL)
        self.table.setItem(row, 0, total_item)

        # Colonnes 1 à 4 : vides et non éditables
        for col in range(1, 5):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, col, item)

        # Colonnes 5 à 7 : totaux initialisés à 0.0
        for col in range(5, 8):
            item = QTableWidgetItem("0.0")
            item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, col, item)

        # Colonne 8 : vide
        self.table.setItem(row, 8, QTableWidgetItem(""))

    def optimiser_doses(self):
        culture = self.cultures[self.culture_nom]
        Nb, Pb, Kb = culture["N"], culture["P"], culture["K"]

        fertilisants = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == "TOTAL":
                continue
            fert = {
                "row": row,
                "N": float(self.table.item(row, 1).text()),
                "P": float(self.table.item(row, 2).text()),
                "K": float(self.table.item(row, 3).text()),
            }
            fertilisants.append(fert)

        if not fertilisants:
            return

        # ==========================
        # fonction objectif à minimiser
        # ==========================
        def objectif(doses):
            Na = sum(d * f["N"] / 100 for d, f in zip(doses, fertilisants))
            Pa = sum(d * f["P"] / 100 for d, f in zip(doses, fertilisants))
            Ka = sum(d * f["K"] / 100 for d, f in zip(doses, fertilisants))
            return (Nb - Na)**2 + (Pb - Pa)**2 + (Kb - Ka)**2

        # contraintes : doses >= 0
        n = len(fertilisants)
        bounds = [(0, None)] * n  # aucune dose négative

        # valeur initiale : doses à 0
        x0 = np.zeros(n)

        res = minimize(objectif, x0, bounds=bounds)

        # ==========================
        # mise à jour du tableau
        # ==========================
        if res.success:
            for dose, f in zip(res.x, fertilisants):
                row = f["row"]
                self.table.setItem(row, 4, QTableWidgetItem(f"{dose:.2f}"))
                self.table.setItem(row, 5, QTableWidgetItem(f"{dose*f['N']/100:.2f}"))
                self.table.setItem(row, 6, QTableWidgetItem(f"{dose*f['P']/100:.2f}"))
                self.table.setItem(row, 7, QTableWidgetItem(f"{dose*f['K']/100:.2f}"))

        self.mettre_a_jour_total()


    def calculer_doses_surface(self):
        self.table_surface.setRowCount(0)  # vider le tableau

        culture = self.cultures[self.culture_nom]
        surface_m2 = culture.get("surface", 10000)  # par défaut 1 ha
        self.surface_label.setText(f"Doses pour la surface réelle ({surface_m2} m²)")

        for row in range(self.table.rowCount()):
            item_nom = self.table.item(row, 0)
            item_dose = self.table.item(row, 4)
            if item_nom is None or item_dose is None:
                continue
            if item_nom.text() == TOTAL_LABEL:
                continue

            nom = item_nom.text()
            try:
                dose_ha = float(item_dose.text())
            except ValueError:
                dose_ha = 0.0

            # dose pour la surface réelle
            dose_surface = dose_ha / 10000 * surface_m2

            # retrouver le fertilisant correspondant dans la base pour conditionnement et prix
            fert = next((f for f in self.fert_base if f["nom"] == nom), None)
            if fert is None:
                condi = 1.0
                prix_unit = 0.0
            else:
                condi = fert.get("conditionnement", 1.0)          # conditionnement unitaire (kg ou L)
                condi_unite = f'{fert.get("conditionnement", "")} {fert.get("unite", "")}'

                prix_unit = fert.get("prix", 0.0)    # prix d’un sac
                unite = fert.get("unite") #

            # calcul de la quantité (nombre de sacs) et prix total
            quantite = max(1, math.ceil(dose_surface / condi))   # au moins 1 sac
            prix_HT = quantite * prix_unit
            prix_TTC = prix_HT * 1.20

            # remplir le tableau
            row_surf = self.table_surface.rowCount()
            self.table_surface.insertRow(row_surf)
            self.table_surface.setItem(row_surf, 0, QTableWidgetItem(nom))
            self.table_surface.setItem(row_surf, 1, QTableWidgetItem(f"{dose_surface:.1f}"))
            self.table_surface.setItem(row_surf, 2, QTableWidgetItem(str(condi_unite)))
            self.table_surface.setItem(row_surf, 3, QTableWidgetItem(f"{prix_unit:.2f}"))
            self.table_surface.setItem(row_surf, 4, QTableWidgetItem(str(quantite)))
            self.table_surface.setItem(row_surf, 5, QTableWidgetItem(f"{prix_HT:.2f}"))
            self.table_surface.setItem(row_surf, 6, QTableWidgetItem(f"{prix_TTC:.2f}"))


        self.table_surface.resizeColumnsToContents()
