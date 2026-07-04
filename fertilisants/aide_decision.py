# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import pulp
import numpy as np
import math
import os
import stat
import tempfile

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, peut_action
import utils.debug as debug
import traceback


def make_cbc_executable():
    """Localise et rend exécutable le binaire CBC, que l'app tourne
    en script Python normal (venv) ou packagée en exécutable PyInstaller
    (les fichiers sont alors extraits dans sys._MEIPASS)."""
    import sys

    # Mode PyInstaller : les fichiers collectés sont dans _MEIPASS
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(pulp.__file__)

    solverdir = os.path.join(base_dir, "solverdir")

    if sys.platform.startswith("linux"):
        cbc_path = os.path.join(solverdir, "cbc", "linux", "i64", "cbc")
    elif sys.platform == "win32":
        cbc_path = os.path.join(solverdir, "cbc", "win", "i64", "cbc.exe")
    elif sys.platform == "darwin":
        cbc_path = os.path.join(solverdir, "cbc", "osx", "i64", "cbc")
    else:
        cbc_path = os.path.join(solverdir, "cbc", "linux", "i64", "cbc")

    if os.path.exists(cbc_path):
        if sys.platform != "win32":
            st = os.stat(cbc_path)
            os.chmod(cbc_path, st.st_mode | stat.S_IEXEC)
        debug.debug(f"[ferti] CBC rendu exécutable : {cbc_path}")
        return cbc_path

    debug.debug(f"[ferti] ⚠ CBC non trouvé (cherché : {cbc_path})")
    return None


class AideDecisionFerti(QWidget):
    """Calcul des doses optimales de fertilisants, soit pour une culture
    liée à une parcelle réelle, soit en mode NPK libre (saisie directe)."""

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_ecrire = peut_action(current_user, "fertilisants", "ecriture")
        self._fert_base = []
        self._culture_active = None  # dict {nom, n, p, k, surface_m2, culture_parcelle_id, parcelle_id}
        self._build_ui()
        self._charger_fertilisants()
        self._charger_cultures_parcelle()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Aide à la décision — Fertilisation")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        splitter = QSplitter(Qt.Horizontal)

        # ── Colonne gauche : choix culture ────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(4, 4, 4, 4)

        choix_group = QGroupBox("Culture cible")
        ch_lay = QVBoxLayout(choix_group)

        self.radio_parcelle = QRadioButton("Culture d'une parcelle")
        self.radio_parcelle.setChecked(True)
        self.radio_libre = QRadioButton("NPK libre (saisie directe)")
        self.radio_parcelle.toggled.connect(self._on_mode_changed)
        ch_lay.addWidget(self.radio_parcelle)
        ch_lay.addWidget(self.radio_libre)

        self.combo_culture_parcelle = QComboBox()
        self.combo_culture_parcelle.currentIndexChanged.connect(
            self._on_culture_parcelle_selected)
        ch_lay.addWidget(self.combo_culture_parcelle)

        # Mode NPK libre
        self.w_libre = QWidget()
        g_lay = QFormLayout(self.w_libre)
        g_lay.setContentsMargins(0, 8, 0, 0)

        npk_w = QWidget()
        npk_lay = QHBoxLayout(npk_w)
        npk_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_n_libre = QDoubleSpinBox()
        self.inp_n_libre.setRange(0, 99999)
        self.inp_n_libre.setPrefix("N: ")
        self.inp_n_libre.setSuffix(" kg/ha")
        self.inp_n_libre.valueChanged.connect(self._on_npk_libre_changed)
        self.inp_p_libre = QDoubleSpinBox()
        self.inp_p_libre.setRange(0, 99999)
        self.inp_p_libre.setPrefix("P: ")
        self.inp_p_libre.setSuffix(" kg/ha")
        self.inp_p_libre.valueChanged.connect(self._on_npk_libre_changed)
        self.inp_k_libre = QDoubleSpinBox()
        self.inp_k_libre.setRange(0, 99999)
        self.inp_k_libre.setPrefix("K: ")
        self.inp_k_libre.setSuffix(" kg/ha")
        self.inp_k_libre.valueChanged.connect(self._on_npk_libre_changed)
        npk_lay.addWidget(self.inp_n_libre)
        npk_lay.addWidget(self.inp_p_libre)
        npk_lay.addWidget(self.inp_k_libre)
        g_lay.addRow("Besoins (kg/ha)", npk_w)

        info_libre = QLabel(
            "Saisissez les besoins agronomiques standards (kg/ha) sans "
            "lien à une parcelle existante. Le calcul restera ramené à "
            "l'hectare de référence (1 ha).")
        info_libre.setStyleSheet("color:palette(mid); font-size:11px;")
        info_libre.setWordWrap(True)
        g_lay.addRow(info_libre)

        self.w_libre.setVisible(False)
        ch_lay.addWidget(self.w_libre)

        ll.addWidget(choix_group)

        besoins_group = QGroupBox("Besoins totaux pour la surface")
        b_lay = QFormLayout(besoins_group)
        self.lbl_surface_ref = QLabel("—")
        self.lbl_surface_ref.setStyleSheet("font-size:12px; color:palette(mid);")
        b_lay.addRow("Surface :", self.lbl_surface_ref)
        self.lbl_n = QLabel("—")
        self.lbl_p = QLabel("—")
        self.lbl_k = QLabel("—")
        for lbl in (self.lbl_n, self.lbl_p, self.lbl_k):
            lbl.setStyleSheet("font-size:14px; font-weight:bold;")
        b_lay.addRow("N :", self.lbl_n)
        b_lay.addRow("P :", self.lbl_p)
        b_lay.addRow("K :", self.lbl_k)
        ll.addWidget(besoins_group)

        ll.addStretch()
        splitter.addWidget(left)

        # ── Colonne centrale : sélection fertilisants ──
        center = QWidget()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.addWidget(QLabel("Fertilisants disponibles (catalogue)"))

        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(
            ["Nom", "N", "P", "K", "Cdtmt", "Prix", "Utilisable"])
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        hh = self.table_fertilisants.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        cl.addWidget(self.table_fertilisants)

        info_mode = QLabel(
            "Mode AUTO : ne cochez rien → optimisation automatique du stock.\n"
            "Mode STRICT : cochez 3+ fertilisants précis → répartition exacte sur ceux-ci.")
        info_mode.setStyleSheet("color:palette(mid); font-size:11px;")
        info_mode.setWordWrap(True)
        cl.addWidget(info_mode)

        self.btn_calculer = QPushButton("Calculer les doses")
        self.btn_calculer.setFixedHeight(36)
        self.btn_calculer.clicked.connect(self._calculer)
        cl.addWidget(self.btn_calculer)

        splitter.addWidget(center)

        # ── Colonne droite : résultats (focus surface réelle) ──
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(4, 4, 4, 4)

        lbl_principal = QLabel("Doses à apporter (pour la surface choisie)")
        f2 = QFont(); f2.setBold(True)
        lbl_principal.setFont(f2)
        rl.addWidget(lbl_principal)

        self.table_doses_surface = QTableWidget(0, 7)
        self.table_doses_surface.setHorizontalHeaderLabels(
            ["Fertilisant", "Dose à apporter", "Prix", "Cdtmt",
             "Prix unitaire", "Quantité (sacs)", "Prix HT"])
        self.table_doses_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hh3 = self.table_doses_surface.horizontalHeader()
        hh3.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            hh3.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        rl.addWidget(self.table_doses_surface)

        # Détail kg/ha en repli, secondaire
        detail_group = QGroupBox("Détail (référence agronomique kg/ha)")
        detail_group.setCheckable(True)
        detail_group.setChecked(False)
        d_lay = QVBoxLayout(detail_group)
        self.table_doses_ha = QTableWidget(0, 5)
        self.table_doses_ha.setHorizontalHeaderLabels(
            ["Fertilisant", "N", "P", "K", "Dose (kg/ha)"])
        self.table_doses_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        hh2 = self.table_doses_ha.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            hh2.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table_doses_ha.setMaximumHeight(160)
        self.table_doses_ha.setVisible(False)
        detail_group.toggled.connect(self.table_doses_ha.setVisible)
        d_lay.addWidget(self.table_doses_ha)
        rl.addWidget(detail_group)

        self.btn_aller_carnet = QPushButton("→ Enregistrer cet apport au carnet")
        self.btn_aller_carnet.setEnabled(False)
        self.btn_aller_carnet.clicked.connect(self._envoyer_au_carnet)
        rl.addWidget(self.btn_aller_carnet)

        splitter.addWidget(right)
        splitter.setSizes([280, 350, 450])
        root.addWidget(splitter, 1)

    # ──────────────────────────────────────────
    # Chargement
    # ──────────────────────────────────────────
    def _charger_fertilisants(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM fertilisants ORDER BY nom")
            self._fert_base = [dict(r) for r in cur.fetchall()]
            cur.close()

            self.table_fertilisants.setRowCount(0)
            for f in self._fert_base:
                r = self.table_fertilisants.rowCount()
                self.table_fertilisants.insertRow(r)
                self.table_fertilisants.setItem(r, 0, QTableWidgetItem(f["nom"]))
                self.table_fertilisants.setItem(r, 1, QTableWidgetItem(f"{f['n']}"))
                self.table_fertilisants.setItem(r, 2, QTableWidgetItem(f"{f['p']}"))
                self.table_fertilisants.setItem(r, 3, QTableWidgetItem(f"{f['k']}"))
                self.table_fertilisants.setItem(r, 4,
                    QTableWidgetItem(f"{f['conditionnement']} {f['unite']}"))
                self.table_fertilisants.setItem(r, 5,
                    QTableWidgetItem(f"{f['prix']:.2f} €"))

                cell = QWidget()
                cl = QHBoxLayout(cell)
                cl.setContentsMargins(0, 0, 0, 0)
                cl.setAlignment(Qt.AlignCenter)
                chk = QCheckBox()
                cl.addWidget(chk)
                self.table_fertilisants.setCellWidget(r, 6, cell)
        except Exception:
            traceback.print_exc()

    def _charger_cultures_parcelle(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT cp.id, cp.espece, cp.variete, cp.surface_occupee_m2,
                       p.nom AS parcelle_nom, p.id AS parcelle_id
                FROM cultures_parcelle cp
                JOIN parcelles p ON p.id = cp.parcelle_id
                WHERE cp.actif=1 AND cp.categorie IN ('maraichage', 'arbo')
                ORDER BY p.nom, cp.espece
            """)
            self.combo_culture_parcelle.clear()
            self.combo_culture_parcelle.addItem("— Sélectionnez —", None)
            for row in cur.fetchall():
                label = f"{row['parcelle_nom']} — {row['espece']}"
                if row["variete"]:
                    label += f" ({row['variete']})"
                self.combo_culture_parcelle.addItem(label, dict(row))
            cur.close()
        except Exception:
            traceback.print_exc()

    def recharger(self):
        self._charger_fertilisants()
        self._charger_cultures_parcelle()

    # ──────────────────────────────────────────
    def _on_mode_changed(self, checked: bool):
        self.combo_culture_parcelle.setVisible(checked)
        self.w_libre.setVisible(not checked)
        if checked:
            self._culture_active = None
            self._reset_besoins()
        else:
            self._on_npk_libre_changed()

    def _reset_besoins(self):
        self.lbl_n.setText("—")
        self.lbl_p.setText("—")
        self.lbl_k.setText("—")
        self.lbl_surface_ref.setText("—")

    def _on_culture_parcelle_selected(self):
        data = self.combo_culture_parcelle.currentData()
        if not data:
            self._culture_active = None
            self._reset_besoins()
            return
        npk = self._get_npk_espece(data["espece"])
        surface_m2 = data.get("surface_occupee_m2") or 10000
        self._culture_active = {
            "nom": data["espece"],
            "n_ha": npk["n"], "p_ha": npk["p"], "k_ha": npk["k"],
            "surface_m2": surface_m2,
            "mode": "parcelle",
        }
        self._afficher_besoins()

    def _on_npk_libre_changed(self):
        n = self.inp_n_libre.value()
        p = self.inp_p_libre.value()
        k = self.inp_k_libre.value()
        if n == 0 and p == 0 and k == 0:
            self._culture_active = None
            self._reset_besoins()
            return
        # Mode libre : N/P/K saisis sont des kg/ha, surface de référence = 1 ha
        self._culture_active = {
            "nom": "NPK libre",
            "n_total": n, "p_total": p, "k_total": k,
            "surface_m2": 10000,
            "mode": "libre",
        }
        self._afficher_besoins()

    def _get_npk_espece(self, espece: str) -> dict:
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT besoin_n, besoin_p, besoin_k FROM cultures "
                "WHERE LOWER(nom) = LOWER(?)", (espece,))
            row = cur.fetchone()
            cur.close()
            if row:
                return {"n": row[0], "p": row[1], "k": row[2]}
        except Exception:
            pass
        return {"n": 0, "p": 0, "k": 0}

    def _afficher_besoins(self):
        c = self._culture_active
        if c["mode"] == "parcelle":
            surface_ha = c["surface_m2"] / 10000
            self.lbl_surface_ref.setText(
                f"{c['surface_m2']:.0f} m² ({surface_ha:.4f} ha)")
            self.lbl_n.setText(f"{c['n_ha']} kg/ha")
            self.lbl_p.setText(f"{c['p_ha']} kg/ha")
            self.lbl_k.setText(f"{c['k_ha']} kg/ha")
        else:
            self.lbl_surface_ref.setText("— (référence 1 ha)")
            self.lbl_n.setText(f"{c['n_total']} kg/ha")
            self.lbl_p.setText(f"{c['p_total']} kg/ha")
            self.lbl_k.setText(f"{c['k_total']} kg/ha")

    # ──────────────────────────────────────────
    # Calcul (toujours à l'échelle de l'hectare, conversion
    # vers la surface réelle uniquement à la toute fin)
    # ──────────────────────────────────────────
    def _calculer(self):
        if not self._culture_active:
            QMessageBox.warning(self, "Aucun besoin",
                "Sélectionnez une culture ou saisissez un NPK libre.")
            return

        c = self._culture_active
        if c["mode"] == "parcelle":
            Nb, Pb, Kb = c["n_ha"], c["p_ha"], c["k_ha"]
        else:
            # Mode libre : les valeurs saisies sont déjà des unités kg/ha
            Nb, Pb, Kb = c["n_total"], c["p_total"], c["k_total"]

        if Nb == 0 and Pb == 0 and Kb == 0:
            QMessageBox.warning(self, "NPK non renseigné",
                "Aucun besoin NPK défini.")
            return

        ferts_coches = []
        for row in range(self.table_fertilisants.rowCount()):
            cell = self.table_fertilisants.cellWidget(row, 6)
            chk = cell.layout().itemAt(0).widget()
            if chk.isChecked():
                nom = self.table_fertilisants.item(row, 0).text()
                fert = next((f for f in self._fert_base if f["nom"] == nom), None)
                if fert:
                    ferts_coches.append(fert)

        self.table_doses_ha.blockSignals(True)
        self.table_doses_ha.setRowCount(0)
        self.table_doses_surface.setRowCount(0)

        # Résolution TOUJOURS à l'échelle de l'hectare (Nb/Pb/Kb en kg/ha)
        if not ferts_coches:
            resultats = self._calcul_auto(Nb, Pb, Kb)
        else:
            if len(ferts_coches) < 3:
                QMessageBox.warning(self, "Mode strict",
                    "Le mode strict nécessite au moins 3 fertilisants cochés.")
                self.table_doses_ha.blockSignals(False)
                return
            resultats = self._calcul_strict(Nb, Pb, Kb, ferts_coches)

        if not resultats:
            self.table_doses_ha.blockSignals(False)
            return

        self._remplir_resultats(resultats)
        self.table_doses_ha.blockSignals(False)
        self.btn_aller_carnet.setEnabled(len(resultats) > 0)

    def _calcul_auto(self, Nb, Pb, Kb):
        os.environ["TMPDIR"] = tempfile.gettempdir()

        fertilisants_autorises = list(self._fert_base)
        if not fertilisants_autorises:
            return []

        from db import get_parametres_app
        tolerance_pct = get_parametres_app().get("tolerance_npk_pct", 2.0) / 100

        prob = pulp.LpProblem("Optimisation_Fertilisants", pulp.LpMinimize)
        noms = [f["nom"] for f in fertilisants_autorises]
        x = {nom: pulp.LpVariable(f"x_{nom}", cat="Binary") for nom in noms}
        y = {nom: pulp.LpVariable(f"y_{nom}", lowBound=0) for nom in noms}

        max_fertilisants = 4
        penalite_nb_fertilisants = 5
        M = 1_000_000

        prob += (
            pulp.lpSum((y[f["nom"]] / f["conditionnement"]) * f["prix"]
                       for f in fertilisants_autorises)
            + penalite_nb_fertilisants
            * pulp.lpSum(x[f["nom"]] for f in fertilisants_autorises)
        )

        # Contraintes avec tolérance (bornes min/max) plutôt qu'égalité stricte
        somme_n = pulp.lpSum(y[f["nom"]] * f["n"] / 100 for f in fertilisants_autorises)
        somme_p = pulp.lpSum(y[f["nom"]] * f["p"] / 100 for f in fertilisants_autorises)
        somme_k = pulp.lpSum(y[f["nom"]] * f["k"] / 100 for f in fertilisants_autorises)

        if Nb > 0:
            prob += somme_n >= Nb * (1 - tolerance_pct)
            prob += somme_n <= Nb * (1 + tolerance_pct)
        else:
            prob += somme_n == 0
        if Pb > 0:
            prob += somme_p >= Pb * (1 - tolerance_pct)
            prob += somme_p <= Pb * (1 + tolerance_pct)
        else:
            prob += somme_p == 0
        if Kb > 0:
            prob += somme_k >= Kb * (1 - tolerance_pct)
            prob += somme_k <= Kb * (1 + tolerance_pct)
        else:
            prob += somme_k == 0

        for f in fertilisants_autorises:
            prob += y[f["nom"]] <= M * x[f["nom"]]

        prob += pulp.lpSum(x[f["nom"]] for f in fertilisants_autorises) <= max_fertilisants

        cbc_path = make_cbc_executable()
        try:
            prob.solve(pulp.COIN_CMD(path=cbc_path, msg=False))
        except Exception as e:
            debug.debug(f"[ferti] Erreur solveur : {e}")

        if pulp.LpStatus[prob.status] != "Optimal":
            QMessageBox.warning(self, "Calcul impossible",
                f"Aucune combinaison trouvée avec le stock disponible "
                f"(tolérance ±{tolerance_pct*100:.0f}%).\n"
                "Le stock actuel ne permet probablement pas d'approcher "
                "ces besoins NPK. Essayez le mode strict, augmentez la "
                "tolérance dans les Paramètres, ou complétez le catalogue.")
            return []

        resultats = []
        for f in fertilisants_autorises:
            dose = y[f["nom"]].value()
            if dose and dose > 0.01:
                resultats.append({
                    "nom": f["nom"], "dose_totale": round(dose, 2),
                    "n": round(dose * f["n"] / 100, 2),
                    "p": round(dose * f["p"] / 100, 2),
                    "k": round(dose * f["k"] / 100, 2),
                })
        return resultats

    def _calcul_strict(self, Nb, Pb, Kb, ferts):
        A = np.array([
            [f["n"] / 100 for f in ferts],
            [f["p"] / 100 for f in ferts],
            [f["k"] / 100 for f in ferts],
        ])
        B = np.array([Nb, Pb, Kb])
        doses, *_ = np.linalg.lstsq(A, B, rcond=None)

        resultats = []
        for dose, fert in zip(doses, ferts):
            dose = max(dose, 0)
            resultats.append({
                "nom": fert["nom"], "dose_totale": round(dose, 2),
                "n": round(dose * fert["n"] / 100, 2),
                "p": round(dose * fert["p"] / 100, 2),
                "k": round(dose * fert["k"] / 100, 2),
            })
        return resultats

    def _remplir_resultats(self, resultats):
        c = self._culture_active
        surface_ha = (c["surface_m2"] / 10000) if c.get("surface_m2") else 1.0

        total_prix = total_dose_eur = 0
        total_n_ha = total_p_ha = total_k_ha = 0
        self._dernier_calcul = []

        for r in resultats:
            fert = next((f for f in self._fert_base if f["nom"] == r["nom"]), None)
            if not fert:
                continue

            # r contient déjà la dose en kg/ha (résolution faite à l'échelle ha)
            dose_ha = r["dose_totale"]
            total_n_ha += r["n"]
            total_p_ha += r["p"]
            total_k_ha += r["k"]

            row_ha = self.table_doses_ha.rowCount()
            self.table_doses_ha.insertRow(row_ha)
            self.table_doses_ha.setItem(row_ha, 0, QTableWidgetItem(r["nom"]))
            self.table_doses_ha.setItem(row_ha, 1, QTableWidgetItem(f"{r['n']}"))
            self.table_doses_ha.setItem(row_ha, 2, QTableWidgetItem(f"{r['p']}"))
            self.table_doses_ha.setItem(row_ha, 3, QTableWidgetItem(f"{r['k']}"))
            self.table_doses_ha.setItem(row_ha, 4, QTableWidgetItem(f"{dose_ha:.2f}"))

            # Produit en croix : dose pour la surface réelle = dose_ha × surface_ha
            dose_surface = dose_ha * surface_ha
            n_surface = r["n"] * surface_ha
            p_surface = r["p"] * surface_ha
            k_surface = r["k"] * surface_ha

            conditionnement = fert.get("conditionnement", 1)
            unite = fert.get("unite", "kg")
            prix_unitaire = fert.get("prix", 0)
            prix_kg = prix_unitaire / conditionnement if conditionnement else 0
            prix_dose = prix_kg * dose_surface
            quantite = (math.ceil(dose_surface / conditionnement)
                        if conditionnement > 0 else 0)
            prix_ht = quantite * prix_unitaire

            total_prix += prix_ht
            total_dose_eur += prix_dose

            self._dernier_calcul.append({
                "nom": r["nom"], "fertilisant_id": fert["id"],
                "n": round(n_surface, 2), "p": round(p_surface, 2),
                "k": round(k_surface, 2),
                "dose_surface": round(dose_surface, 2),
                "surface_m2": c.get("surface_m2"),
            })

            row = self.table_doses_surface.rowCount()
            self.table_doses_surface.insertRow(row)
            item_nom = QTableWidgetItem(r["nom"])
            self.table_doses_surface.setItem(row, 0, item_nom)

            item_dose = QTableWidgetItem(f"{dose_surface:.2f} {unite}")
            f_bold = QFont(); f_bold.setBold(True)
            item_dose.setFont(f_bold)
            self.table_doses_surface.setItem(row, 1, item_dose)

            self.table_doses_surface.setItem(row, 2, QTableWidgetItem(f"{prix_dose:.2f} €"))
            self.table_doses_surface.setItem(row, 3,
                QTableWidgetItem(f"{conditionnement} {unite}"))
            self.table_doses_surface.setItem(row, 4,
                QTableWidgetItem(f"{prix_unitaire:.2f} €"))
            self.table_doses_surface.setItem(row, 5, QTableWidgetItem(str(quantite)))
            self.table_doses_surface.setItem(row, 6, QTableWidgetItem(f"{prix_ht:.2f} €"))

        # Ligne TOTAL du détail kg/ha — comparaison avec les besoins de référence
        if c["mode"] == "parcelle":
            n_ref, p_ref, k_ref = c["n_ha"], c["p_ha"], c["k_ha"]
        else:
            n_ref, p_ref, k_ref = c["n_total"], c["p_total"], c["k_total"]

        row_total_ha = self.table_doses_ha.rowCount()
        self.table_doses_ha.insertRow(row_total_ha)
        font_bold = QFont(); font_bold.setBold(True)

        item_total_lbl = QTableWidgetItem(f"TOTAL / Réf. ({n_ref}-{p_ref}-{k_ref})")
        item_total_lbl.setFont(font_bold)
        self.table_doses_ha.setItem(row_total_ha, 0, item_total_lbl)

        for col, total_val, ref_val in (
            (1, total_n_ha, n_ref), (2, total_p_ha, p_ref), (3, total_k_ha, k_ref)):
            item = QTableWidgetItem(f"{total_val:.1f}")
            item.setFont(font_bold)
            if ref_val > 0:
                ecart_pct = abs(total_val - ref_val) / ref_val * 100
                if ecart_pct > 5:
                    item.setForeground(QColor("#DC2626"))
                elif ecart_pct > 2:
                    item.setForeground(QColor("#D97706"))
                else:
                    item.setForeground(QColor("#16a34a"))
            self.table_doses_ha.setItem(row_total_ha, col, item)
        self.table_doses_ha.setItem(row_total_ha, 4, QTableWidgetItem(""))
        for col in range(5):
            item = self.table_doses_ha.item(row_total_ha, col)
            if item:
                item.setBackground(QBrush(QColor("#f3f4f6")))

        row = self.table_doses_surface.rowCount()
        self.table_doses_surface.insertRow(row)
        self.table_doses_surface.setItem(row, 0, QTableWidgetItem("TOTAL"))
        self.table_doses_surface.setItem(row, 2, QTableWidgetItem(f"{total_dose_eur:.2f} €"))
        self.table_doses_surface.setItem(row, 6, QTableWidgetItem(f"{total_prix:.2f} €"))
        font = QFont(); font.setBold(True)
        for col in range(7):
            item = self.table_doses_surface.item(row, col)
            if item:
                item.setFont(font)
                item.setBackground(QBrush(QColor("#e6e6e6")))

    def _envoyer_au_carnet(self):
        if not getattr(self, "_dernier_calcul", None):
            return
        if not self._culture_active:
            return

        from fertilisants.carnet import DialogApportFerti
        dlg = DialogApportFerti(
            current_user=self.current_user,
            parcelle_id=None,
            culture_parcelle_id=None,
            pre_remplissage=self._dernier_calcul,
            parent=self)
        dlg.exec()