# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
from ppp.ephy_import import count_produits, telecharger_ephy, importer_depuis_zip
import utils.debug as debug
import traceback


class EphyWorker(QThread):
    progress = Signal(str)
    finished = Signal(int, int)
    error    = Signal(str)

    def run(self):
        try:
            self.progress.emit("Téléchargement des données e-phy...")
            zip_bytes = telecharger_ephy(
                progress_callback=lambda p:
                    self.progress.emit(f"Téléchargement... {p}%")
            )
            self.progress.emit("Import en base de données...")
            nb_p, nb_u = importer_depuis_zip(zip_bytes,
                progress_callback=lambda i:
                    self.progress.emit(f"Import en cours... {i} produits")
            )
            self.finished.emit(nb_p, nb_u)
        except Exception as e:
            traceback.print_exc()
            self.error.emit(str(e))


class CataloguePPP(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._check_auto_import()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(6)

        # ── Filtres ───────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Rechercher par nom ou n° AMM...")
        self.inp_search.textChanged.connect(self._filtrer)
        toolbar.addWidget(self.inp_search, 2)

        self.combo_culture = QComboBox()
        self.combo_culture.addItem("Toutes les cultures", None)
        self.combo_culture.currentIndexChanged.connect(self._on_culture_changed)
        toolbar.addWidget(self.combo_culture, 2)

        self.combo_bio_agresseur = QComboBox()
        self.combo_bio_agresseur.addItem("Tous les bio-agresseurs", None)
        self.combo_bio_agresseur.currentIndexChanged.connect(self._filtrer)
        toolbar.addWidget(self.combo_bio_agresseur, 2)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("UAB et conventionnel", None)
        self.combo_mode.addItem("UAB uniquement", "bio")
        self.combo_mode.currentIndexChanged.connect(self._filtrer)
        toolbar.addWidget(self.combo_mode, 1)

        btn_maj = QPushButton("Mettre à jour (e-phy)")
        btn_maj.clicked.connect(self._lancer_import)
        toolbar.addWidget(btn_maj)

        root.addLayout(toolbar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: palette(mid); font-size: 12px;")
        root.addWidget(self.lbl_status)

        # ── Splitter vertical : produits (haut) / détail (bas) ──
        vsplit = QSplitter(Qt.Vertical)

        # Table produits
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Nom commercial", "N° AMM", "Substance(s) active(s)", "Mode"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setWordWrap(False)
        self.table.setAlternatingRowColors(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_produit_changed)
        vsplit.addWidget(self.table)

        # ── Zone basse ────────────────────────
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 4, 0, 0)
        bottom_layout.setSpacing(8)

        # Colonne gauche : fiche produit (haut) + conditions générales (bas)
        left_col = QSplitter(Qt.Vertical)

        fiche = QGroupBox("Fiche produit")
        fiche_layout = QFormLayout(fiche)
        fiche_layout.setSpacing(6)
        fiche_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_nom  = QLabel("—")
        self.lbl_nom.setWordWrap(True)
        f = QFont(); f.setBold(True); f.setPointSize(12)
        self.lbl_nom.setFont(f)

        self.lbl_amm  = QLabel("—")
        self.lbl_sa   = QLabel("—")
        self.lbl_sa.setWordWrap(True)
        self.lbl_mode = QLabel("—")

        fiche_layout.addRow("Produit :", self.lbl_nom)
        fiche_layout.addRow("N° AMM :", self.lbl_amm)
        fiche_layout.addRow("Substance(s) :", self.lbl_sa)
        fiche_layout.addRow("Mode :", self.lbl_mode)
        left_col.addWidget(fiche)

        # Conditions générales du produit
        cond_group = QGroupBox("Conditions générales d'emploi")
        cond_layout = QVBoxLayout(cond_group)
        cond_layout.setContentsMargins(8, 8, 8, 8)
        self.txt_conditions = QTextEdit()
        self.txt_conditions.setReadOnly(True)
        self.txt_conditions.setPlaceholderText("Sélectionnez un produit")
        self.txt_conditions.setStyleSheet("font-size: 12px;")
        cond_layout.addWidget(self.txt_conditions)
        left_col.addWidget(cond_group)

        left_col.setSizes([180, 180])
        left_col.setMaximumWidth(380)
        bottom_layout.addWidget(left_col)

        # Colonne droite : tableau usages + détail usage sélectionné
        right_col = QSplitter(Qt.Vertical)

        usages_group = QGroupBox("Usages homologués")
        usages_layout = QVBoxLayout(usages_group)
        usages_layout.setContentsMargins(6, 6, 6, 6)
        usages_layout.setSpacing(4)

        self.table_usages = QTableWidget(0, 7)
        self.table_usages.setHorizontalHeaderLabels(
            ["Culture", "Bio-agresseur", "Dose", "Unité", "DAR (j)", "NMA", "Mode"])
        self.table_usages.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_usages.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_usages.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_usages.setAlternatingRowColors(True)
        self.table_usages.setWordWrap(False)
        uh = self.table_usages.horizontalHeader()
        uh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(1, QHeaderView.Stretch)
        uh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        uh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_usages.itemSelectionChanged.connect(self._on_usage_changed)
        usages_layout.addWidget(self.table_usages)

        self.lbl_usages_count = QLabel("")
        self.lbl_usages_count.setStyleSheet("font-size: 11px; color: palette(mid);")
        usages_layout.addWidget(self.lbl_usages_count)
        right_col.addWidget(usages_group)

        # Détail de l'usage sélectionné
        detail_usage_group = QGroupBox("Détail de l'usage sélectionné")
        detail_layout = QGridLayout(detail_usage_group)
        detail_layout.setContentsMargins(8, 8, 8, 8)
        detail_layout.setSpacing(6)

        self.lbl_u_culture  = QLabel("—")
        self.lbl_u_bio_agr  = QLabel("—")
        self.lbl_u_dose     = QLabel("—")
        self.lbl_u_dar      = QLabel("—")
        self.lbl_u_nma      = QLabel("—")
        self.lbl_u_stades   = QLabel("—")
        self.lbl_u_znt      = QLabel("—")
        self.lbl_u_cond     = QLabel("—")
        self.lbl_u_cond.setWordWrap(True)

        labels = [
            ("Culture :",           self.lbl_u_culture),
            ("Bio-agresseur :",     self.lbl_u_bio_agr),
            ("Dose retenue :",      self.lbl_u_dose),
            ("DAR :",               self.lbl_u_dar),
            ("Nb max applications :", self.lbl_u_nma),
            ("Stades BBCH :",       self.lbl_u_stades),
            ("ZNT :",               self.lbl_u_znt),
            ("Condition d'emploi :", self.lbl_u_cond),
        ]
        for i, (txt, widget) in enumerate(labels):
            row_i = i // 2
            col_i = (i % 2) * 2
            lbl = QLabel(txt)
            lbl.setStyleSheet("font-size: 12px; font-weight: bold;")
            detail_layout.addWidget(lbl, row_i, col_i)
            widget.setStyleSheet("font-size: 12px;")
            detail_layout.addWidget(widget, row_i, col_i + 1)

        right_col.addWidget(detail_usage_group)
        right_col.setSizes([280, 180])
        bottom_layout.addWidget(right_col, 1)

        vsplit.addWidget(bottom)
        vsplit.setSizes([280, 360])
        root.addWidget(vsplit, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("font-size: 11px; color: palette(mid);")
        root.addWidget(self.lbl_count)

    # ──────────────────────────────────────────
    # Données
    # ──────────────────────────────────────────
    def _check_auto_import(self):
        if count_produits() == 0:
            self.lbl_status.setText("Aucun produit — import e-phy automatique...")
            QTimer.singleShot(500, self._lancer_import)
        else:
            self._charger_filtres()
            self._filtrer()

    def _charger_filtres(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT culture FROM ppp_usages "
                        "WHERE culture IS NOT NULL ORDER BY culture")
            self.combo_culture.blockSignals(True)
            self.combo_culture.clear()
            self.combo_culture.addItem("Toutes les cultures", None)
            for row in cur.fetchall():
                self.combo_culture.addItem(row[0], row[0])
            self.combo_culture.blockSignals(False)

            cur.execute("SELECT DISTINCT bio_agresseur FROM ppp_usages "
                        "WHERE bio_agresseur IS NOT NULL ORDER BY bio_agresseur")
            self.combo_bio_agresseur.blockSignals(True)
            self.combo_bio_agresseur.clear()
            self.combo_bio_agresseur.addItem("Tous les bio-agresseurs", None)
            for row in cur.fetchall():
                self.combo_bio_agresseur.addItem(row[0], row[0])
            self.combo_bio_agresseur.blockSignals(False)
            cur.close()
        except Exception as e:
            traceback.print_exc()

    def _on_culture_changed(self):
        culture = self.combo_culture.currentData()
        try:
            conn = get_connection()
            cur = conn.cursor()
            if culture:
                cur.execute("SELECT DISTINCT bio_agresseur FROM ppp_usages "
                            "WHERE culture = ? AND bio_agresseur IS NOT NULL "
                            "ORDER BY bio_agresseur", (culture,))
            else:
                cur.execute("SELECT DISTINCT bio_agresseur FROM ppp_usages "
                            "WHERE bio_agresseur IS NOT NULL ORDER BY bio_agresseur")
            self.combo_bio_agresseur.blockSignals(True)
            self.combo_bio_agresseur.clear()
            self.combo_bio_agresseur.addItem("Tous les bio-agresseurs", None)
            for row in cur.fetchall():
                self.combo_bio_agresseur.addItem(row[0], row[0])
            self.combo_bio_agresseur.blockSignals(False)
            cur.close()
        except Exception as e:
            traceback.print_exc()
        self._filtrer()

    def _filtrer(self):
        search  = self.inp_search.text().strip().lower()
        culture = self.combo_culture.currentData()
        bio_agr = self.combo_bio_agresseur.currentData()
        mode    = self.combo_mode.currentData()

        try:
            conn = get_connection()
            cur = conn.cursor()

            sql = ("SELECT DISTINCT p.id, p.nom_commercial, p.num_amm, "
                   "p.substance_active, p.bio_compatible "
                   "FROM ppp_produits p")
            params = []
            wheres = []

            if culture or bio_agr:
                sql += " JOIN ppp_usages u ON u.produit_id = p.id"
                if culture:
                    wheres.append("u.culture = ?")
                    params.append(culture)
                if bio_agr:
                    wheres.append("u.bio_agresseur = ?")
                    params.append(bio_agr)

            if mode == "bio":
                wheres.append("p.bio_compatible = 1")
                

            if search:
                wheres.append(
                    "(LOWER(p.nom_commercial) LIKE ? OR LOWER(p.num_amm) LIKE ?)")
                params += [f"%{search}%", f"%{search}%"]

            if wheres:
                sql += " WHERE " + " AND ".join(wheres)
            sql += " ORDER BY p.nom_commercial"

            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()

            self.table.setRowCount(0)
            for row in rows:
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(row[1] or ""))
                self.table.setItem(r, 1, QTableWidgetItem(row[2] or ""))
                self.table.setItem(r, 2, QTableWidgetItem(row[3] or ""))
                self.table.setItem(r, 3,
                    QTableWidgetItem("UAB" if row[4] else "Conventionnel"))
                self.table.item(r, 0).setData(Qt.UserRole, row[0])

            self.lbl_count.setText(
                f"{len(rows)} produit(s) affiché(s) sur {count_produits()} en base")
            self._vider_detail()
        except Exception as e:
            traceback.print_exc()

    def _vider_detail(self):
        self.lbl_nom.setText("—")
        self.lbl_amm.setText("—")
        self.lbl_sa.setText("—")
        self.lbl_mode.setText("—")
        self.txt_conditions.clear()
        self.table_usages.setRowCount(0)
        self.lbl_usages_count.setText("")
        self._vider_usage()

    def _vider_usage(self):
        for lbl in (self.lbl_u_culture, self.lbl_u_bio_agr, self.lbl_u_dose,
                    self.lbl_u_dar, self.lbl_u_nma, self.lbl_u_stades,
                    self.lbl_u_znt, self.lbl_u_cond):
            lbl.setText("—")

    def _on_produit_changed(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        produit_id = item.data(Qt.UserRole)
        if produit_id is None:
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM ppp_produits WHERE id = ?", (produit_id,))
            prod = dict(cur.fetchone())

            self.lbl_nom.setText(prod.get("nom_commercial", "—"))
            self.lbl_amm.setText(prod.get("num_amm", "—"))
            sa = (prod.get("substance_active") or "—").replace(" | ", "\n")
            self.lbl_sa.setText(sa)
            self.lbl_mode.setText("UAB" if prod.get("bio_compatible") else "Conventionnel")
            self.txt_conditions.setPlainText(prod.get("conditions_emploi") or "Aucune condition générale enregistrée")

            # Usages filtrés par la culture sélectionnée si applicable
            culture_filtre = self.combo_culture.currentData()
            if culture_filtre:
                cur.execute("""
                    SELECT id, culture, bio_agresseur, dose, dose_unite,
                           dar, nma, stade_min, stade_max,
                           znt_eau, znt_arthropodes, znt_plantes,
                           condition_usage, mode
                    FROM ppp_usages
                    WHERE produit_id = ? AND culture = ?
                    ORDER BY bio_agresseur
                """, (produit_id, culture_filtre))
            else:
                cur.execute("""
                    SELECT id, culture, bio_agresseur, dose, dose_unite,
                           dar, nma, stade_min, stade_max,
                           znt_eau, znt_arthropodes, znt_plantes,
                           condition_usage, mode
                    FROM ppp_usages
                    WHERE produit_id = ?
                    ORDER BY culture, bio_agresseur
                """, (produit_id,))
            usages = cur.fetchall()
            cur.close()

            self.table_usages.setRowCount(0)
            for u in usages:
                r = self.table_usages.rowCount()
                self.table_usages.insertRow(r)
                self.table_usages.setItem(r, 0, QTableWidgetItem(u[1] or ""))
                self.table_usages.setItem(r, 1, QTableWidgetItem(u[2] or ""))
                dose_txt = f"{u[3]}" if u[3] is not None else "—"
                self.table_usages.setItem(r, 2, QTableWidgetItem(dose_txt))
                self.table_usages.setItem(r, 3, QTableWidgetItem(u[4] or "—"))
                self.table_usages.setItem(r, 4,
                    QTableWidgetItem(str(u[5]) if u[5] is not None else "—"))
                self.table_usages.setItem(r, 5,
                    QTableWidgetItem(str(u[6]) if u[6] is not None else "—"))
                self.table_usages.setItem(r, 6, QTableWidgetItem(u[13] or ""))
                # Stocker l'id usage pour le détail
                self.table_usages.item(r, 0).setData(Qt.UserRole, u[0])

            self.lbl_usages_count.setText(f"{len(usages)} usage(s)")
            self._vider_usage()
        except Exception as e:
            traceback.print_exc()

    def _on_usage_changed(self):
        row = self.table_usages.currentRow()
        if row < 0:
            return
        item = self.table_usages.item(row, 0)
        if not item:
            return
        usage_id = item.data(Qt.UserRole)
        if usage_id is None:
            return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT culture, bio_agresseur, dose, dose_unite,
                       dar, nma, stade_min, stade_max,
                       znt_eau, znt_arthropodes, znt_plantes,
                       condition_usage, mode
                FROM ppp_usages WHERE id = ?
            """, (usage_id,))
            u = cur.fetchone()
            cur.close()
            if not u:
                return

            self.lbl_u_culture.setText(u[0] or "—")
            self.lbl_u_bio_agr.setText(u[1] or "—")
            dose_txt = f"{u[2]} {u[3]}" if u[2] is not None else "—"
            self.lbl_u_dose.setText(dose_txt)
            self.lbl_u_dar.setText(f"{u[4]} jour(s)" if u[4] is not None else "—")
            self.lbl_u_nma.setText(str(u[5]) if u[5] is not None else "—")

            stade_min = u[6] or "?"
            stade_max = u[7] or "?"
            self.lbl_u_stades.setText(f"BBCH {stade_min} → {stade_max}")

            znt_parts = []
            if u[8] is not None:
                znt_parts.append(f"Eau : {u[8]} m")
            if u[9] is not None:
                znt_parts.append(f"Arthropodes : {u[9]} m")
            if u[10] is not None:
                znt_parts.append(f"Plantes : {u[10]} m")
            self.lbl_u_znt.setText(" | ".join(znt_parts) if znt_parts else "—")

            self.lbl_u_cond.setText(u[11] or "—")
        except Exception as e:
            traceback.print_exc()

    def _lancer_import(self):
        self.lbl_status.setText("Import e-phy en cours...")
        self._worker = EphyWorker()
        self._worker.progress.connect(self.lbl_status.setText)
        self._worker.finished.connect(self._import_termine)
        self._worker.error.connect(self._import_erreur)
        self._worker.start()

    def _import_termine(self, nb_p: int, nb_u: int):
        self.lbl_status.setText(f"Import terminé : {nb_p} produits, {nb_u} usages.")
        self._charger_filtres()
        self._filtrer()

    def _import_erreur(self, msg: str):
        self.lbl_status.setText(f"Erreur import : {msg}")
        QMessageBox.warning(self, "Erreur e-phy",
            f"Impossible de récupérer les données e-phy :\n{msg}\n\n"
            "Vérifiez votre connexion internet.")