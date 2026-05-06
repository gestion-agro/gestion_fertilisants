# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
from views.login import peut
import utils.debug as debug
import traceback


class AideDecision(QWidget):
    # Signal émis quand l'utilisateur veut créer un traitement
    # (produit_id, usage_id, culture, bio_agresseur)
    creer_traitement = Signal(int, int, str, str)

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._build_ui()
        self._charger_cultures()

    # ──────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Titre ─────────────────────────────
        titre = QLabel("Aide à la décision phytosanitaire")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        # ── Formulaire de recherche ────────────
        form_group = QGroupBox("Critères de recherche")
        form = QGridLayout(form_group)
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

        # Culture
        form.addWidget(QLabel("Culture *"), 0, 0)
        self.combo_culture = QComboBox()
        self.combo_culture.setMinimumWidth(220)
        self.combo_culture.currentIndexChanged.connect(self._on_culture_changed)
        form.addWidget(self.combo_culture, 0, 1)

        # Bio-agresseur
        form.addWidget(QLabel("Bio-agresseur *"), 0, 2)
        self.combo_bio_agr = QComboBox()
        self.combo_bio_agr.setMinimumWidth(220)
        form.addWidget(self.combo_bio_agr, 0, 3)

        # Mode
        form.addWidget(QLabel("Mode"), 1, 0)
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Bio et conventionnel", None)
        self.combo_mode.addItem("Bio uniquement", "bio")
        self.combo_mode.addItem("Conventionnel uniquement", "conventionnel")
        form.addWidget(self.combo_mode, 1, 1)

        # Seuil de dégâts (optionnel)
        form.addWidget(QLabel("Seuil de dégâts (optionnel)"), 1, 2)
        self.inp_seuil = QLineEdit()
        self.inp_seuil.setPlaceholderText("Ex : > 5%, forte pression...")
        form.addWidget(self.inp_seuil, 1, 3)

        # Bouton recherche
        self.btn_rechercher = QPushButton("Rechercher")
        self.btn_rechercher.setFixedHeight(36)
        self.btn_rechercher.clicked.connect(self._rechercher)
        form.addWidget(self.btn_rechercher, 2, 0, 1, 4)

        root.addWidget(form_group)

        # ── Résultats ─────────────────────────
        # Splitter vertical : liste produits / détail
        vsplit = QSplitter(Qt.Vertical)

        # Table résultats
        results_group = QGroupBox("Produits recommandés")
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(6, 6, 6, 6)

        self.lbl_results_info = QLabel("Renseignez une culture et un bio-agresseur puis cliquez sur Rechercher.")
        self.lbl_results_info.setStyleSheet("color: palette(mid); font-size: 12px;")
        self.lbl_results_info.setWordWrap(True)
        results_layout.addWidget(self.lbl_results_info)

        self.table_results = QTableWidget(0, 6)
        self.table_results.setHorizontalHeaderLabels(
            ["Produit", "N° AMM", "Dose", "Unité", "DAR (j)", "Mode"])
        self.table_results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_results.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_results.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_results.setAlternatingRowColors(True)
        self.table_results.setWordWrap(False)
        hh = self.table_results.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_results.itemSelectionChanged.connect(self._on_produit_changed)
        results_layout.addWidget(self.table_results)
        vsplit.addWidget(results_group)

        # Détail produit sélectionné
        detail_group = QGroupBox("Détail du produit sélectionné")
        detail_layout = QHBoxLayout(detail_group)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        detail_layout.setSpacing(12)

        # Fiche gauche
        fiche = QWidget()
        fiche_layout = QFormLayout(fiche)
        fiche_layout.setSpacing(6)

        self.lbl_d_nom  = QLabel("—")
        self.lbl_d_nom.setWordWrap(True)
        f2 = QFont(); f2.setBold(True); f2.setPointSize(12)
        self.lbl_d_nom.setFont(f2)

        self.lbl_d_amm  = QLabel("—")
        self.lbl_d_sa   = QLabel("—")
        self.lbl_d_sa.setWordWrap(True)
        self.lbl_d_mode = QLabel("—")
        self.lbl_d_dose = QLabel("—")
        self.lbl_d_dar  = QLabel("—")
        self.lbl_d_nma  = QLabel("—")
        self.lbl_d_znt  = QLabel("—")
        self.lbl_d_znt.setWordWrap(True)

        fiche_layout.addRow("Produit :",     self.lbl_d_nom)
        fiche_layout.addRow("N° AMM :",      self.lbl_d_amm)
        fiche_layout.addRow("Substance(s) :", self.lbl_d_sa)
        fiche_layout.addRow("Mode :",        self.lbl_d_mode)
        fiche_layout.addRow("Dose :",        self.lbl_d_dose)
        fiche_layout.addRow("DAR :",         self.lbl_d_dar)
        fiche_layout.addRow("NMA :",         self.lbl_d_nma)
        fiche_layout.addRow("ZNT :",         self.lbl_d_znt)

        # Homologation — mis à jour à chaque sélection produit
        self.lbl_d_homol = QLabel("—")
        self.lbl_d_homol.setWordWrap(True)
        self.lbl_d_homol.setStyleSheet("font-size: 12px; font-weight: bold;")
        fiche_layout.addRow("Homologation :", self.lbl_d_homol)

        detail_layout.addWidget(fiche, 1)

        # Conditions + bouton droite
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(8)

        lbl_cond = QLabel("Conditions d'emploi")
        lbl_cond.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(lbl_cond)

        self.txt_cond = QTextEdit()
        self.txt_cond.setReadOnly(True)
        self.txt_cond.setStyleSheet("font-size: 12px;")
        self.txt_cond.setMaximumHeight(120)
        right_layout.addWidget(self.txt_cond)

        lbl_cond_usage = QLabel("Condition spécifique à l'usage")
        lbl_cond_usage.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(lbl_cond_usage)

        self.txt_cond_usage = QTextEdit()
        self.txt_cond_usage.setReadOnly(True)
        self.txt_cond_usage.setStyleSheet("font-size: 12px;")
        self.txt_cond_usage.setMaximumHeight(80)
        right_layout.addWidget(self.txt_cond_usage)

        right_layout.addStretch()

        # Bouton "Utiliser ce produit" — visible selon droits
        self.btn_utiliser = QPushButton("Utiliser ce produit → Carnet")
        self.btn_utiliser.setFixedHeight(38)
        self.btn_utiliser.setEnabled(False)
        self.btn_utiliser.clicked.connect(self._utiliser_produit)

        if not peut(self.current_user, "carnet_ecriture"):
            self.btn_utiliser.setToolTip(
                "Votre certificat ne vous autorise pas à enregistrer des traitements.")
            self.btn_utiliser.setVisible(False)

        right_layout.addWidget(self.btn_utiliser)
        detail_layout.addWidget(right, 1)

        vsplit.addWidget(detail_group)
        vsplit.setSizes([300, 250])
        root.addWidget(vsplit, 1)

        # Stockage usage courant pour le bouton
        self._usage_courant = None
        self._produit_courant = None

    # ──────────────────────────────────────────
    # Chargement filtres
    # ──────────────────────────────────────────
    def _charger_cultures(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT culture FROM ppp_usages "
                        "WHERE culture IS NOT NULL ORDER BY culture")
            self.combo_culture.blockSignals(True)
            self.combo_culture.clear()
            self.combo_culture.addItem("— Sélectionnez une culture —", None)
            for row in cur.fetchall():
                self.combo_culture.addItem(row[0], row[0])
            self.combo_culture.blockSignals(False)
            cur.close()
        except Exception as e:
            traceback.print_exc()

    def _on_culture_changed(self):
        culture = self.combo_culture.currentData()
        try:
            conn = get_connection()
            cur = conn.cursor()
            self.combo_bio_agr.clear()
            self.combo_bio_agr.addItem("— Sélectionnez un bio-agresseur —", None)
            if culture:
                cur.execute("""
                    SELECT DISTINCT bio_agresseur FROM ppp_usages
                    WHERE culture = ? AND bio_agresseur IS NOT NULL
                    ORDER BY bio_agresseur
                """, (culture,))
                for row in cur.fetchall():
                    self.combo_bio_agr.addItem(row[0], row[0])
            cur.close()
        except Exception as e:
            traceback.print_exc()

    # ──────────────────────────────────────────
    # Recherche
    # ──────────────────────────────────────────
    def _rechercher(self):
        culture = self.combo_culture.currentData()
        bio_agr = self.combo_bio_agr.currentData()
        mode    = self.combo_mode.currentData()

        if not culture:
            QMessageBox.warning(self, "Champ manquant", "Veuillez sélectionner une culture.")
            return
        if not bio_agr:
            QMessageBox.warning(self, "Champ manquant", "Veuillez sélectionner un bio-agresseur.")
            return

        try:
            conn = get_connection()
            cur = conn.cursor()

            sql = """
                SELECT u.id, p.id, p.nom_commercial, p.num_amm,
                       u.dose, u.dose_unite, u.dar, u.nma, u.mode,
                       p.bio_compatible
                FROM ppp_usages u
                JOIN ppp_produits p ON p.id = u.produit_id
                WHERE u.culture = ? AND u.bio_agresseur = ?
            """
            params = [culture, bio_agr]

            if mode == "bio":
                sql += " AND p.bio_compatible = 1"
            elif mode == "conventionnel":
                sql += " AND p.bio_compatible = 0"

            sql += " ORDER BY p.nom_commercial"

            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()

            self.table_results.setRowCount(0)
            self._vider_detail()

            if not rows:
                self.lbl_results_info.setText(
                    f"Aucun produit homologué trouvé pour {culture} / {bio_agr}.")
                return

            self.lbl_results_info.setText(
                f"{len(rows)} produit(s) homologué(s) pour {culture} — {bio_agr}")

            for row in rows:
                r = self.table_results.rowCount()
                self.table_results.insertRow(r)
                self.table_results.setItem(r, 0, QTableWidgetItem(row[2] or ""))
                self.table_results.setItem(r, 1, QTableWidgetItem(row[3] or ""))
                dose_txt = str(row[4]) if row[4] is not None else "—"
                self.table_results.setItem(r, 2, QTableWidgetItem(dose_txt))
                self.table_results.setItem(r, 3, QTableWidgetItem(row[5] or "—"))
                self.table_results.setItem(r, 4,
                    QTableWidgetItem(str(row[6]) if row[6] is not None else "—"))
                self.table_results.setItem(r, 5, QTableWidgetItem(row[8] or ""))
                # Stocker usage_id et produit_id
                self.table_results.item(r, 0).setData(Qt.UserRole, (row[0], row[1]))

                # Colorer les lignes bio en vert clair
                if row[9]:
                    for col in range(6):
                        item = self.table_results.item(r, col)
                        if item:
                            item.setBackground(QColor("#EAF3DE"))

        except Exception as e:
            traceback.print_exc()
            debug.debug(f"[aide_decision] Erreur recherche : {e}")

    # ──────────────────────────────────────────
    # Détail produit sélectionné
    # ──────────────────────────────────────────
    def _on_produit_changed(self):
        row = self.table_results.currentRow()
        if row < 0:
            return
        item = self.table_results.item(row, 0)
        if not item:
            return
        ids = item.data(Qt.UserRole)
        if ids is None:
            return
        usage_id, produit_id = ids

        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT * FROM ppp_produits WHERE id = ?", (produit_id,))
            prod = dict(cur.fetchone())

            cur.execute("""
                SELECT dose, dose_unite, dar, nma,
                       znt_eau, znt_arthropodes, znt_plantes,
                       condition_usage, mode
                FROM ppp_usages WHERE id = ?
            """, (usage_id,))
            usage = cur.fetchone()
            cur.close()

            if not usage:
                return

            self._produit_courant = prod
            self._usage_courant = dict(zip(
                ["dose", "dose_unite", "dar", "nma",
                 "znt_eau", "znt_arthropodes", "znt_plantes",
                 "condition_usage", "mode"], usage))
            self._usage_courant["id"] = usage_id
            self._usage_courant["produit_id"] = produit_id

            self.lbl_d_nom.setText(prod.get("nom_commercial", "—"))
            self.lbl_d_amm.setText(prod.get("num_amm", "—"))
            sa = (prod.get("substance_active") or "—").replace(" | ", "\n")
            self.lbl_d_sa.setText(sa)
            self.lbl_d_mode.setText(
                "Bio" if prod.get("bio_compatible") else "Conventionnel")

            dose = usage[0]
            dose_u = usage[1] or ""
            self.lbl_d_dose.setText(f"{dose} {dose_u}" if dose is not None else "—")
            self.lbl_d_dar.setText(
                f"{usage[2]} jour(s)" if usage[2] is not None else "—")
            self.lbl_d_nma.setText(str(usage[3]) if usage[3] is not None else "—")

            znt_parts = []
            if usage[4] is not None:
                znt_parts.append(f"Eau : {usage[4]} m")
            if usage[5] is not None:
                znt_parts.append(f"Arthropodes : {usage[5]} m")
            if usage[6] is not None:
                znt_parts.append(f"Plantes : {usage[6]} m")
            self.lbl_d_znt.setText(" | ".join(znt_parts) if znt_parts else "—")

            # Vérification homologation culture + bio-agresseur
            culture_sel = self.combo_culture.currentData()
            bio_agr_sel = self.combo_bio_agr.currentData()
            if culture_sel and bio_agr_sel:
                cur.execute("""
                    SELECT COUNT(*) FROM ppp_usages
                    WHERE produit_id = ? AND culture = ? AND bio_agresseur = ?
                """, (produit_id, culture_sel, bio_agr_sel))
                homol_count = cur.fetchone()[0]
                if homol_count > 0:
                    self.lbl_d_homol.setText(
                        f"✓ Homologué pour {culture_sel} / {bio_agr_sel}")
                    self.lbl_d_homol.setStyleSheet(
                        "font-size: 12px; font-weight: bold; color: #16a34a;")
                else:
                    self.lbl_d_homol.setText(
                        f"✗ Non homologué pour {culture_sel} / {bio_agr_sel}")
                    self.lbl_d_homol.setStyleSheet(
                        "font-size: 12px; font-weight: bold; color: #dc2626;")
            else:
                self.lbl_d_homol.setText("—")
                self.lbl_d_homol.setStyleSheet("font-size: 12px;")

            self.txt_cond.setPlainText(
                prod.get("conditions_emploi") or "Aucune condition générale.")
            self.txt_cond_usage.setPlainText(
                usage[7] or "Aucune condition spécifique à cet usage.")

            # Activer le bouton si l'utilisateur a les droits
            self.btn_utiliser.setEnabled(
                peut(self.current_user, "carnet_ecriture"))

        except Exception as e:
            traceback.print_exc()

    def _vider_detail(self):
        for lbl in (self.lbl_d_nom, self.lbl_d_amm, self.lbl_d_sa,
                    self.lbl_d_mode, self.lbl_d_dose, self.lbl_d_dar,
                    self.lbl_d_nma, self.lbl_d_znt):
            lbl.setText("—")
        self.lbl_d_homol.setText("—")
        self.lbl_d_homol.setStyleSheet("font-size: 12px;")
        self.txt_cond.clear()
        self.txt_cond_usage.clear()
        self.btn_utiliser.setEnabled(False)
        self._usage_courant = None
        self._produit_courant = None

    # ──────────────────────────────────────────
    # Bouton "Utiliser ce produit"
    # ──────────────────────────────────────────
    def _utiliser_produit(self):
        if not self._usage_courant or not self._produit_courant:
            return

        culture = self.combo_culture.currentData()
        bio_agr = self.combo_bio_agr.currentData()

        self.creer_traitement.emit(
            self._produit_courant["id"],
            self._usage_courant["id"],
            culture or "",
            bio_agr or "",
        )