# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, peut_supprimer_ruche, peut_action
import utils.debug as debug
import traceback
import re


# ── Constantes interventions ──────────────────
TYPES_INTERVENTION = {
    "varroa":       ("Traitement varroa",   "Produit",  None,      None),
    "sirop":        ("Nourrissement sirop",  "Type sirop", "Quantité", "ml"),
    "candi":        ("Nourrissement candi",  "Marque",   "Quantité", "sachets"),
    "pollen":       ("Nourrissement pollen", "Type",     "Quantité", "g"),
    "antibiotique": ("Traitement antibio",   "Produit",  "Dose",    "ml"),
    "miel":         ("Récolte miel",         None,       "Quantité", "kg"),
    "hausse":       ("Hausse",               None,       None,      None),
    "autre":        ("Autre intervention",   "Description", None,   None),
}
# Labels des types pour affichage
LABELS_TYPE = {k: v[0] for k, v in TYPES_INTERVENTION.items()}


class RuchesPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_supprimer = peut_supprimer_ruche(current_user)
        self._peut_ecrire    = peut_action(current_user, "ruches", "ecriture")
        self._build_ui()
        self.btn_add_ruche.setVisible(self._peut_ecrire)
        self.btn_nouvelle_visite.setVisible(self._peut_ecrire)
        self._charger_ruches()
        self._charger_visites()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Gestion des ruches")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_ruches(),  "🐝 Ruches")
        self.tabs.addTab(self._tab_visites(), "📋 Suivi && Interventions")
        root.addWidget(self.tabs, 1)

    # ──────────────────────────────────────────
    # Onglet Ruches
    # ──────────────────────────────────────────
    def _tab_ruches(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        top = QHBoxLayout()
        self.chk_inactives = QCheckBox("Afficher les ruches inactives")
        self.chk_inactives.stateChanged.connect(self._charger_ruches)
        top.addWidget(self.chk_inactives)
        top.addStretch()
        self.btn_add_ruche = QPushButton("+ Ajouter une ruche")
        self.btn_add_ruche.clicked.connect(lambda: self._dialog_ruche())
        top.addWidget(self.btn_add_ruche)
        lay.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)

        # Table
        self.table_ruches = QTableWidget(0, 5)
        self.table_ruches.setHorizontalHeaderLabels(
            ["Nom", "N° NAPI", "Parcelle", "Installation", "État"])
        self.table_ruches.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_ruches.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_ruches.setAlternatingRowColors(True)
        self.table_ruches.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_ruches.customContextMenuRequested.connect(self._menu_ruche)
        self.table_ruches.cellDoubleClicked.connect(
            lambda row, col: self._dialog_ruche(self.table_ruches.item(row, 0).data(Qt.UserRole))
        )
        hh = self.table_ruches.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table_ruches.itemSelectionChanged.connect(self._on_ruche_changed)
        splitter.addWidget(self.table_ruches)

        # Fiche détail
        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(8, 0, 0, 0)
        dl.setSpacing(8)

        self.fiche_ruche = QGroupBox("Fiche ruche")
        fl = QFormLayout(self.fiche_ruche)
        fl.setSpacing(6)
        fl.setContentsMargins(8, 8, 8, 8)

        self.lbl_r_nom      = QLabel("—")
        self.lbl_r_napi     = QLabel("—")
        self.lbl_r_parcelle = QLabel("—")
        self.lbl_r_race     = QLabel("—")
        self.lbl_r_type     = QLabel("—")
        self.lbl_r_install  = QLabel("—")
        self.lbl_r_notes    = QLabel("—")
        self.lbl_r_notes.setWordWrap(True)

        for lbl in (self.lbl_r_nom, self.lbl_r_napi, self.lbl_r_parcelle,
                    self.lbl_r_race, self.lbl_r_type,
                    self.lbl_r_install, self.lbl_r_notes):
            lbl.setStyleSheet("font-size: 13px;")

        fl.addRow("Nom :",          self.lbl_r_nom)
        fl.addRow("N° NAPI :",      self.lbl_r_napi)
        fl.addRow("Parcelle :",     self.lbl_r_parcelle)
        fl.addRow("Race :",         self.lbl_r_race)
        fl.addRow("Type ruche :",   self.lbl_r_type)
        fl.addRow("Installation :", self.lbl_r_install)
        fl.addRow("Notes :",        self.lbl_r_notes)
        dl.addWidget(self.fiche_ruche)

        # Dernière visite
        self.lbl_derniere_visite = QLabel("Aucune visite enregistrée")
        self.lbl_derniere_visite.setStyleSheet(
            "color: palette(mid); font-size: 12px; padding: 4px;")
        self.lbl_derniere_visite.setWordWrap(True)
        dl.addWidget(self.lbl_derniere_visite)

        self.btn_nouvelle_visite = QPushButton("+ Nouvelle visite")
        self.btn_nouvelle_visite.setEnabled(False)
        self.btn_nouvelle_visite.clicked.connect(self._nouvelle_visite)
        dl.addWidget(self.btn_nouvelle_visite)

        # Résumé de la dernière visite
        self.w_resume_visite = QFrame()
        self.w_resume_visite.setFrameShape(QFrame.StyledPanel)
        self.w_resume_visite.setAutoFillBackground(True)
        pal = self.w_resume_visite.palette()
        pal.setColor(QPalette.Window, QColor("#f0fdf4"))
        self.w_resume_visite.setPalette(pal)
        self.w_resume_visite.setVisible(False)
        rv_lay = QVBoxLayout(self.w_resume_visite)
        rv_lay.setContentsMargins(10, 8, 10, 8)
        rv_lay.setSpacing(4)
        lbl_rv_titre = QLabel("📋 Dernière visite")
        lbl_rv_titre.setStyleSheet("font-weight: bold; color: #16a34a; font-size: 12px;")
        rv_lay.addWidget(lbl_rv_titre)
        self.lbl_rv_date       = QLabel("—")
        self.lbl_rv_population = QLabel("—")
        self.lbl_rv_reine      = QLabel("—")
        self.lbl_rv_couvain    = QLabel("—")
        self.lbl_rv_varroa     = QLabel("—")
        self.lbl_rv_notes      = QLabel("—")
        self.lbl_rv_notes.setWordWrap(True)
        for lbl in (self.lbl_rv_date, self.lbl_rv_population,
                    self.lbl_rv_reine, self.lbl_rv_couvain,
                    self.lbl_rv_varroa, self.lbl_rv_notes):
            lbl.setStyleSheet("font-size: 11px; color: #374151;")
            rv_lay.addWidget(lbl)
        dl.addWidget(self.w_resume_visite)
        dl.addStretch()

        splitter.addWidget(detail)
        splitter.setSizes([420, 280])
        lay.addWidget(splitter, 1)
        return w

    # ──────────────────────────────────────────
    # Onglet Visites & Interventions
    # ──────────────────────────────────────────
    def _tab_visites(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        filtre = QHBoxLayout()
        self.combo_filtre_ruche = QComboBox()
        self.combo_filtre_ruche.addItem("Toutes les ruches", None)
        self.combo_filtre_ruche.currentIndexChanged.connect(self._charger_visites)

        self.inp_debut = QDateEdit(QDate.currentDate().addMonths(-6))
        self.inp_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_debut.setCalendarPopup(True)
        self.inp_debut.dateChanged.connect(self._charger_visites)

        self.inp_fin = QDateEdit(QDate.currentDate())
        self.inp_fin.setDisplayFormat("dd/MM/yyyy")
        self.inp_fin.setCalendarPopup(True)
        self.inp_fin.dateChanged.connect(self._charger_visites)

        filtre.addWidget(QLabel("Ruche :"))
        filtre.addWidget(self.combo_filtre_ruche)
        filtre.addWidget(QLabel("Du :"))
        filtre.addWidget(self.inp_debut)
        filtre.addWidget(QLabel("au :"))
        filtre.addWidget(self.inp_fin)
        filtre.addStretch()
        lay.addLayout(filtre)

        # Splitter : liste visites / détail visite
        splitter = QSplitter(Qt.Vertical)

        # Table visites
        vis_group = QGroupBox("Visites")
        vis_lay = QVBoxLayout(vis_group)
        vis_lay.setContentsMargins(4, 4, 4, 4)

        self.table_visites = QTableWidget(0, 6)
        self.table_visites.setHorizontalHeaderLabels(
            ["Date", "Ruche", "Varroa %", "Reine", "Couvain", "Population"])
        self.table_visites.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_visites.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_visites.setAlternatingRowColors(True)
        self.table_visites.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_visites.customContextMenuRequested.connect(self._menu_visite)
        vh = self.table_visites.horizontalHeader()
        vh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        vh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        for i in range(2, 6):
            vh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table_visites.itemSelectionChanged.connect(self._on_visite_changed)
        vis_lay.addWidget(self.table_visites)
        splitter.addWidget(vis_group)

        # Détail interventions de la visite sélectionnée
        interv_group = QGroupBox("Interventions de la visite")
        interv_lay = QVBoxLayout(interv_group)
        interv_lay.setContentsMargins(4, 4, 4, 4)

        self.table_interventions = QTableWidget(0, 5)
        self.table_interventions.setHorizontalHeaderLabels(
            ["Type", "Produit / Description", "Quantité", "Unité", "Notes"])
        self.table_interventions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_interventions.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_interventions.setAlternatingRowColors(True)
        ih = self.table_interventions.horizontalHeader()
        ih.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ih.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 5):
            ih.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        interv_lay.addWidget(self.table_interventions)
        splitter.addWidget(interv_group)

        splitter.setSizes([300, 200])
        lay.addWidget(splitter, 1)
        return w

    # ──────────────────────────────────────────
    # Chargement
    # ──────────────────────────────────────────
    def _charger(self):
        self._charger_ruches()
        self._charger_filtre_ruches()
        self._charger_visites()

    def _charger_ruches(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            sql = """
                SELECT r.id, r.nom, r.num_napi, r.date_installation,
                       r.actif, p.nom AS parcelle_nom
                FROM ruches r
                LEFT JOIN parcelles p ON p.id = r.parcelle_id
            """
            if not self.chk_inactives.isChecked():
                sql += " WHERE r.actif = 1"
            sql += " ORDER BY r.nom"
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()

            self.table_ruches.setRowCount(0)
            for row in rows:
                i = self.table_ruches.rowCount()
                self.table_ruches.insertRow(i)
                self.table_ruches.setItem(i, 0, QTableWidgetItem(row[1] or ""))
                self.table_ruches.setItem(i, 1, QTableWidgetItem(row[2] or "—"))
                self.table_ruches.setItem(i, 2, QTableWidgetItem(row[5] or "—"))
                self.table_ruches.setItem(i, 3, QTableWidgetItem(
                    self._fmt_date(row[3])))
                etat = "Active" if row[4] else "Inactive"
                self.table_ruches.setItem(i, 4, QTableWidgetItem(etat))
                self.table_ruches.item(i, 0).setData(Qt.UserRole, row[0])

                if not row[4]:
                    for col in range(5):
                        item = self.table_ruches.item(i, col)
                        if item:
                            item.setForeground(QColor("gray"))
                            f = item.font(); f.setItalic(True); item.setFont(f)
        except Exception as e:
            debug.debug(f"[ruches] Erreur chargement : {e}")
            traceback.print_exc()

    def _charger_filtre_ruches(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM ruches WHERE actif=1 ORDER BY nom")
            self.combo_filtre_ruche.blockSignals(True)
            self.combo_filtre_ruche.clear()
            self.combo_filtre_ruche.addItem("Toutes les ruches", None)
            for row in cur.fetchall():
                self.combo_filtre_ruche.addItem(row[1], row[0])
            self.combo_filtre_ruche.blockSignals(False)
            cur.close()
        except Exception:
            traceback.print_exc()

    def _charger_visites(self):
        ruche_id   = self.combo_filtre_ruche.currentData()
        date_debut = self.inp_debut.date().toString("yyyy-MM-dd")
        date_fin   = self.inp_fin.date().toString("yyyy-MM-dd")
        try:
            conn = get_connection()
            cur = conn.cursor()
            sql = """
                SELECT v.id, v.date_visite, r.nom,
                       v.varroa_pct, v.etat_reine,
                       v.etat_couvain, v.population, v.notes
                FROM visites_ruches v
                JOIN ruches r ON r.id = v.ruche_id
                WHERE v.date_visite BETWEEN ? AND ?
            """
            params = [date_debut, date_fin]
            if ruche_id:
                sql += " AND v.ruche_id = ?"
                params.append(ruche_id)
            sql += " ORDER BY v.date_visite DESC"
            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()

            self.table_visites.setRowCount(0)
            self.table_interventions.setRowCount(0)

            for row in rows:
                i = self.table_visites.rowCount()
                self.table_visites.insertRow(i)
                self.table_visites.setItem(i, 0,
                    QTableWidgetItem(self._fmt_date(row[1])))
                self.table_visites.setItem(i, 1, QTableWidgetItem(row[2] or ""))
                varroa = f"{row[3]:.1f}%" if row[3] is not None else "—"
                self.table_visites.setItem(i, 2, QTableWidgetItem(varroa))
                self.table_visites.setItem(i, 3, QTableWidgetItem(row[4] or "—"))
                self.table_visites.setItem(i, 4, QTableWidgetItem(row[5] or "—"))
                self.table_visites.setItem(i, 5, QTableWidgetItem(row[6] or "—"))
                self.table_visites.item(i, 0).setData(Qt.UserRole, row[0])

                # Coloration varroa
                if row[3] is not None:
                    color = None
                    if row[3] > 3:
                        color = QColor("#FEE2E2")
                    elif row[3] > 1:
                        color = QColor("#FEF3C7")
                    if color:
                        for col in range(6):
                            item = self.table_visites.item(i, col)
                            if item:
                                item.setBackground(color)
        except Exception as e:
            debug.debug(f"[ruches] Erreur visites : {e}")
            traceback.print_exc()

    def _on_visite_changed(self):
        row = self.table_visites.currentRow()
        if row < 0:
            self.table_interventions.setRowCount(0)
            return
        item = self.table_visites.item(row, 0)
        if not item:
            return
        visite_id = item.data(Qt.UserRole)
        self._charger_interventions(visite_id)

    def _charger_interventions(self, visite_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT type, produit, quantite, unite, notes
                FROM interventions_ruches
                WHERE visite_id = ?
                ORDER BY id
            """, (visite_id,))
            rows = cur.fetchall()
            cur.close()

            self.table_interventions.setRowCount(0)
            for row in rows:
                i = self.table_interventions.rowCount()
                self.table_interventions.insertRow(i)
                self.table_interventions.setItem(i, 0,
                    QTableWidgetItem(LABELS_TYPE.get(row[0], row[0])))
                self.table_interventions.setItem(i, 1,
                    QTableWidgetItem(row[1] or "—"))
                qte = f"{row[2]}" if row[2] is not None else "—"
                self.table_interventions.setItem(i, 2, QTableWidgetItem(qte))
                self.table_interventions.setItem(i, 3,
                    QTableWidgetItem(row[3] or "—"))
                self.table_interventions.setItem(i, 4,
                    QTableWidgetItem(row[4] or "—"))
        except Exception as e:
            traceback.print_exc()

    def _on_ruche_changed(self):
        row = self.table_ruches.currentRow()
        if row < 0:
            self.btn_nouvelle_visite.setEnabled(False)
            self._ruche_courante = None
            return
        item = self.table_ruches.item(row, 0)
        if not item:
            return
        ruche_id = item.data(Qt.UserRole)
        self._ruche_courante = ruche_id
        self._afficher_detail_ruche(ruche_id)
        self.btn_nouvelle_visite.setEnabled(True)

    def _afficher_detail_ruche(self, ruche_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT r.*, p.nom AS parcelle_nom
                FROM ruches r
                LEFT JOIN parcelles p ON p.id = r.parcelle_id
                WHERE r.id = ?
            """, (ruche_id,))
            r = dict(cur.fetchone())

            # Dernière visite
            cur.execute("""
                SELECT v.date_visite, v.varroa_pct, v.etat_reine,
                       v.etat_couvain, v.population,
                       COUNT(i.id) AS nb_interv
                FROM visites_ruches v
                LEFT JOIN interventions_ruches i ON i.visite_id = v.id
                WHERE v.ruche_id = ?
                GROUP BY v.id
                ORDER BY v.date_visite DESC LIMIT 1
            """, (ruche_id,))
            visite = cur.fetchone()
            cur.close()

            self.fiche_ruche.setTitle(f"Fiche — {r.get('nom', '')}")
            self.lbl_r_nom.setText(r.get("nom", "—"))
            self.lbl_r_napi.setText(r.get("num_napi") or "—")
            self.lbl_r_parcelle.setText(r.get("parcelle_nom") or "—")
            self.lbl_r_race.setText(r.get("race_abeille") or "—")
            self.lbl_r_type.setText(r.get("type_ruche") or "—")
            self.lbl_r_install.setText(self._fmt_date(r.get("date_installation")))
            self.lbl_r_notes.setText(r.get("notes") or "—")

            if visite:
                varroa_txt = f"{visite[1]:.1f}%" if visite[1] is not None else "—"
                txt = (f"Dernière visite : {self._fmt_date(visite[0])} | "
                       f"Varroa : {varroa_txt} | "
                       f"Reine : {visite[2] or '—'} | "
                       f"Couvain : {visite[3] or '—'} | "
                       f"Population : {visite[4] or '—'} | "
                       f"{visite[5]} intervention(s)")
                self.lbl_derniere_visite.setText(txt)
                if visite[1] and visite[1] > 3:
                    self.lbl_derniere_visite.setStyleSheet(
                        "color: #DC2626; font-size: 12px; "
                        "font-weight: bold; padding: 4px;")
                else:
                    self.lbl_derniere_visite.setStyleSheet(
                        "color: palette(mid); font-size: 12px; padding: 4px;")

                # ── Résumé compact sous le bouton Nouvelle visite ──
                self.w_resume_visite.setVisible(True)
                self.lbl_rv_date.setText(f"📅 {self._fmt_date(visite[0])}")
                varroa_style = "color: #DC2626; font-weight: bold;" if visite[1] and visite[1] > 3 else "color: #374151;"
                self.lbl_rv_varroa.setText(f"🪲 Varroa : {varroa_txt}")
                self.lbl_rv_varroa.setStyleSheet(f"font-size: 11px; {varroa_style}")
                self.lbl_rv_reine.setText(f"👑 Reine : {visite[2] or '—'}")
                self.lbl_rv_couvain.setText(f"🥚 Couvain : {visite[3] or '—'}")
                self.lbl_rv_population.setText(f"🐝 Population : {visite[4] or '—'}")
                self.lbl_rv_notes.setText(f"🔧 {visite[5]} intervention(s)")
            else:
                self.lbl_derniere_visite.setText("Aucune visite enregistrée")
                self.lbl_derniere_visite.setStyleSheet(
                    "color: palette(mid); font-size: 12px; padding: 4px;")
                self.w_resume_visite.setVisible(False)
        except Exception as e:
            traceback.print_exc()

    # ──────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────
    def _dialog_ruche(self, ruche_id=None):
        # Pré-remplir le prochain nom si logique numérique
        nom_suivant = self._prochain_nom_ruche() if not ruche_id else None
        napi_defaut = self._napi_defaut() if not ruche_id else None

        dlg = DialogRuche(
            ruche_id=ruche_id,
            nom_suggere=nom_suivant,
            napi_defaut=napi_defaut,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger()

    def _prochain_nom_ruche(self) -> str | None:
        """Si tous les noms sont numériques, propose le suivant."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT nom FROM ruches ORDER BY nom")
            noms = [row[0] for row in cur.fetchall()]
            cur.close()
            if not noms:
                return "1"
            numeros = []
            for n in noms:
                n_strip = n.strip()
                if n_strip.isdigit():
                    numeros.append(int(n_strip))
            if len(numeros) == len(noms) and numeros:
                return str(max(numeros) + 1)
            return None
        except Exception:
            return None

    def _napi_defaut(self) -> str | None:
        from db import get_entreprise
        ent = get_entreprise()
        return ent.get("num_napi")

    def _nouvelle_visite(self):
        if not self._ruche_courante:
            return
        dlg = DialogVisite(
            ruche_id=self._ruche_courante,
            current_user=self.current_user,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_visites()
            self._afficher_detail_ruche(self._ruche_courante)

    def _menu_ruche(self, pos):
        row = self.table_ruches.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_ruches.item(row, 0)
        ruche_id = item.data(Qt.UserRole)
        etat = self.table_ruches.item(row, 4).text()

        menu = QMenu(self)

        if self._peut_ecrire:
            menu.addAction("Modifier", lambda: self._dialog_ruche(ruche_id))
            if etat == "Active":
                menu.addAction("Désactiver",
                    lambda: self._set_actif(ruche_id, False))
            else:
                menu.addAction("Réactiver",
                    lambda: self._set_actif(ruche_id, True))

        if self._peut_supprimer:
            menu.addSeparator()
            act_sup = menu.addAction("🗑 Supprimer définitivement")
            act_sup.triggered.connect(lambda: self._supprimer_ruche(ruche_id))

        if not menu.isEmpty():
            menu.exec(self.table_ruches.viewport().mapToGlobal(pos))

    def _menu_visite(self, pos):
        row = self.table_visites.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_visites.item(row, 0)
        visite_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Supprimer cette visite",
            lambda: self._supprimer_visite(visite_id))
        menu.exec(self.table_visites.viewport().mapToGlobal(pos))

    def _set_actif(self, ruche_id: int, actif: bool):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE ruches SET actif = ? WHERE id = ?",
                        (1 if actif else 0, ruche_id))
            conn.commit()
            cur.close()
            self._charger_ruches()
        except Exception:
            traceback.print_exc()

    def _supprimer_ruche(self, ruche_id: int):
        nom = self.table_ruches.item(
            self.table_ruches.currentRow(), 0).text()
        rep = QMessageBox.warning(
            self, "Supprimer définitivement",
            f"Supprimer la ruche « {nom} » et tout son historique ?\n\n"
            "Cette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM ruches WHERE id = ?", (ruche_id,))
                conn.commit()
                cur.close()
                self._ruche_courante = None
                self._charger()
            except Exception:
                traceback.print_exc()

    def _supprimer_visite(self, visite_id: int):
        rep = QMessageBox.question(self, "Supprimer",
            "Supprimer cette visite et toutes ses interventions ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM visites_ruches WHERE id = ?",
                            (visite_id,))
                conn.commit()
                cur.close()
                self._charger_visites()
                if self._ruche_courante:
                    self._afficher_detail_ruche(self._ruche_courante)
            except Exception:
                traceback.print_exc()

    @staticmethod
    def _fmt_date(d: str) -> str:
        if not d:
            return "—"
        try:
            from datetime import datetime
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return d


# ──────────────────────────────────────────────
# Dialog Ruche
# ──────────────────────────────────────────────
class DialogRuche(QDialog):
    NAPI_MAX = 12

    def __init__(self, ruche_id=None, nom_suggere=None,
                 napi_defaut=None, parent=None):
        super().__init__(parent)
        self.ruche_id = ruche_id
        self.nom_suggere  = nom_suggere
        self.napi_defaut  = napi_defaut
        self.setWindowTitle("Ruche" if not ruche_id else "Modifier la ruche")
        self.setMinimumWidth(440)
        self._build_ui()
        if ruche_id:
            self._charger(ruche_id)
        elif nom_suggere:
            self.inp_nom.setText(nom_suggere)
        if napi_defaut and not ruche_id:
            self.inp_napi.setText(napi_defaut)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # Nom
        self.inp_nom = QLineEdit()
        self.inp_nom.setMaxLength(150)
        form.addRow("Nom *", self.inp_nom)

        # N° NAPI avec compteur
        napi_w = QWidget()
        napi_lay = QHBoxLayout(napi_w)
        napi_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_napi = QLineEdit()
        self.inp_napi.setMaxLength(self.NAPI_MAX)
        self.inp_napi.setPlaceholderText(f"Max {self.NAPI_MAX} caractères")
        self.lbl_napi_count = QLabel(f"0/{self.NAPI_MAX}")
        self.lbl_napi_count.setStyleSheet("color: palette(mid); font-size: 11px;")
        self.inp_napi.textChanged.connect(
            lambda t: self.lbl_napi_count.setText(
                f"{len(t)}/{self.NAPI_MAX}"))
        napi_lay.addWidget(self.inp_napi)
        napi_lay.addWidget(self.lbl_napi_count)
        form.addRow("N° NAPI", napi_w)

        # Parcelle
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("— Aucune parcelle —", None)
        form.addRow("Parcelle", self.combo_parcelle)

        # Race
        self.inp_race = QLineEdit()
        self.inp_race.setPlaceholderText("Ex: Apis mellifera, Buckfast...")
        form.addRow("Race", self.inp_race)

        # Type
        self.inp_type = QLineEdit()
        self.inp_type.setPlaceholderText("Ex: Dadant, Warré, Langstroth...")
        form.addRow("Type de ruche", self.inp_type)

        # Date installation
        self.inp_install = QDateEdit(QDate.currentDate())
        self.inp_install.setDisplayFormat("dd/MM/yyyy")
        self.inp_install.setCalendarPopup(True)
        form.addRow("Date installation", self.inp_install)

        # Notes
        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        form.addRow("Notes", self.inp_notes)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._charger_parcelles()

    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            for row in cur.fetchall():
                self.combo_parcelle.addItem(row[1], row[0])
            cur.close()
        except Exception:
            traceback.print_exc()

    def _charger(self, ruche_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM ruches WHERE id = ?", (ruche_id,))
            r = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(r.get("nom", ""))
            napi = r.get("num_napi") or ""
            self.inp_napi.setText(napi)
            self.lbl_napi_count.setText(f"{len(napi)}/{self.NAPI_MAX}")
            idx = self.combo_parcelle.findData(r.get("parcelle_id"))
            if idx >= 0:
                self.combo_parcelle.setCurrentIndex(idx)
            self.inp_race.setText(r.get("race_abeille") or "")
            self.inp_type.setText(r.get("type_ruche") or "")
            if r.get("date_installation"):
                self.inp_install.setDate(
                    QDate.fromString(r["date_installation"], "yyyy-MM-dd"))
            self.inp_notes.setPlainText(r.get("notes") or "")
        except Exception:
            traceback.print_exc()

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant",
                "Le nom est obligatoire.")
            return
        napi       = self.inp_napi.text().strip() or None
        parcelle   = self.combo_parcelle.currentData()
        race       = self.inp_race.text().strip() or None
        type_ruche = self.inp_type.text().strip() or None
        install    = self.inp_install.date().toString("yyyy-MM-dd")
        notes      = self.inp_notes.toPlainText().strip() or None

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.ruche_id:
                cur.execute("""
                    UPDATE ruches SET nom=?, num_napi=?, parcelle_id=?,
                    race_abeille=?, type_ruche=?, date_installation=?, notes=?
                    WHERE id=?
                """, (nom, napi, parcelle, race, type_ruche, install, notes,
                      self.ruche_id))
            else:
                cur.execute("""
                    INSERT INTO ruches (nom, num_napi, parcelle_id,
                    race_abeille, type_ruche, date_installation, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (nom, napi, parcelle, race, type_ruche, install, notes))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))


# ──────────────────────────────────────────────
# Dialog Visite + Interventions
# ──────────────────────────────────────────────
class DialogVisite(QDialog):
    def __init__(self, ruche_id: int, current_user: dict, parent=None):
        super().__init__(parent)
        self.ruche_id     = ruche_id
        self.current_user = current_user
        self._lignes_intervention = []  # liste de widgets LigneIntervention
        self.setWindowTitle("Nouvelle visite")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(12)

        # ── Infos visite ──────────────────────
        visite_group = QGroupBox("Visite")
        vform = QFormLayout(visite_group)
        vform.setSpacing(8)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        vform.addRow("Date *", self.inp_date)

        self.lbl_varroa_warn = QLabel("")
        self.lbl_varroa_warn.setStyleSheet(
            "color: #DC2626; font-size: 11px; font-weight: bold;")
        self.lbl_varroa_warn.setMinimumWidth(100)

        self.inp_varroa = QLineEdit()
        self.inp_varroa.setPlaceholderText("Non mesuré (ex: 2.5)")
        self.inp_varroa.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,3}([.,]\d{0,1})?$")))
        self.inp_varroa.textChanged.connect(self._check_varroa)

        varroa_w = QWidget()
        varroa_lay = QHBoxLayout(varroa_w)
        varroa_lay.setContentsMargins(0, 0, 0, 0)
        varroa_lay.addWidget(self.inp_varroa)
        varroa_lay.addWidget(self.lbl_varroa_warn)
        vform.addRow("Taux varroa", varroa_w)

        self.combo_reine = QComboBox()
        self.combo_reine.addItems(
            ["—", "Présente", "Absente", "À remplacer", "Inconnue"])
        vform.addRow("État reine", self.combo_reine)

        self.combo_couvain = QComboBox()
        self.combo_couvain.addItems(
            ["—", "Bon", "Lacunaire", "Absent", "Anormal"])
        vform.addRow("État couvain", self.combo_couvain)

        self.combo_population = QComboBox()
        self.combo_population.addItems(["—", "Forte", "Moyenne", "Faible"])
        vform.addRow("Population", self.combo_population)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(60)
        self.inp_notes.setPlaceholderText("Observations générales...")
        vform.addRow("Notes", self.inp_notes)

        lay.addWidget(visite_group)

        # ── Interventions ─────────────────────
        interv_group = QGroupBox("Interventions")
        self.interv_lay = QVBoxLayout(interv_group)
        self.interv_lay.setSpacing(6)
        self.interv_lay.setContentsMargins(8, 8, 8, 8)

        lbl_info = QLabel(
            "Ajoutez autant d'interventions que nécessaire "
            "(traitement varroa, nourrissement, récolte...)")
        lbl_info.setStyleSheet("color: #374151; font-size: 12px;")
        lbl_info.setWordWrap(True)
        self.interv_lay.addWidget(lbl_info)

        btn_add_interv = QPushButton("+ Ajouter une intervention")
        btn_add_interv.clicked.connect(self._ajouter_intervention)
        btn_add_interv.setStyleSheet("""
            QPushButton { border: 1px dashed palette(mid);
                border-radius: 4px; padding: 4px 12px; }
            QPushButton:hover { border-color: #16a34a; color: #16a34a; }
        """)
        self.interv_lay.addWidget(btn_add_interv)
        lay.addWidget(interv_group)

        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        root.addWidget(self.lbl_err)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Enregistrer la visite")
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _check_varroa(self, txt):
        try:
            val = float(txt.replace(",", ".")) if txt.strip() else 0
        except ValueError:
            val = 0
        if val > 3:
            self.lbl_varroa_warn.setText("⚠ Élevé — traitement recommandé")
        elif val > 1:
            self.lbl_varroa_warn.setText("⚠ Modéré — surveiller")
        else:
            self.lbl_varroa_warn.setText("")

    def _ajouter_intervention(self):
        ligne = LigneIntervention(on_supprimer=self._supprimer_intervention)
        self._lignes_intervention.append(ligne)
        # Insérer avant le bouton "+" (dernier widget)
        idx = self.interv_lay.count() - 1
        self.interv_lay.insertWidget(idx, ligne)

    def _supprimer_intervention(self, ligne):
        if ligne in self._lignes_intervention:
            self._lignes_intervention.remove(ligne)
        ligne.setParent(None)
        ligne.deleteLater()

    def _valider(self):
        date_v     = self.inp_date.date().toString("yyyy-MM-dd")
        try:
            varroa = float(self.inp_varroa.text().replace(",", ".")) \
                if self.inp_varroa.text().strip() else None
        except ValueError:
            varroa = None
        reine      = self.combo_reine.currentText()
        couvain    = self.combo_couvain.currentText()
        population = self.combo_population.currentText()
        notes      = self.inp_notes.toPlainText().strip() or None

        reine      = None if reine == "—" else reine
        couvain    = None if couvain == "—" else couvain
        population = None if population == "—" else population

        # Collecter les interventions
        interventions = []
        for ligne in self._lignes_intervention:
            data = ligne.get_data()
            if data:
                interventions.append(data)

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Insérer la visite
            cur.execute("""
                INSERT INTO visites_ruches
                (ruche_id, date_visite, varroa_pct, etat_reine,
                 etat_couvain, population, notes, operateur_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.ruche_id, date_v, varroa, reine,
                  couvain, population, notes,
                  self.current_user.get("id")))
            visite_id = cur.lastrowid

            # Insérer les interventions
            for interv in interventions:
                cur.execute("""
                    INSERT INTO interventions_ruches
                    (visite_id, type, produit, quantite, unite, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (visite_id,
                      interv["type"], interv.get("produit"),
                      interv.get("quantite"), interv.get("unite"),
                      interv.get("notes")))

            conn.commit()
            cur.close()
            debug.debug(f"[ruches] Visite {visite_id} enregistrée "
                        f"avec {len(interventions)} intervention(s)")
            self.accept()
        except Exception as e:
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")


# ──────────────────────────────────────────────
# Widget LigneIntervention (une ligne dans le dialog visite)
# ──────────────────────────────────────────────
class LigneIntervention(QFrame):
    # Config par type : (label_produit, label_qte, unite, placeholder_produit)
    CONFIG = {
        "varroa":       ("Produit",       None,       None,       "Ex: Apivar, Apiguard, Oxalic..."),
        "sirop":        ("Type de sirop", "Quantité", "ml",       "Ex: 50/50, inverti..."),
        "candi":        ("Marque",        "Quantité", "sachets",  "Ex: Apifonda..."),
        "pollen":       ("Type",          "Quantité", "g",        "Ex: pollen frais, substitut..."),
        "antibiotique": ("Produit",       "Dose",     "ml",       "Ex: Terramycine..."),
        "miel":         (None,            "Quantité", "kg",       None),
        "hausse":       (None,            None,       None,       None),
        "autre":        ("Description",   "Quantité", None,       "Décrivez l'intervention..."),
    }

    def __init__(self, on_supprimer, parent=None):
        super().__init__(parent)
        self.on_supprimer = on_supprimer
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(1)
        self._build_ui()

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        # Type
        self.combo_type = QComboBox()
        for key, label in LABELS_TYPE.items():
            self.combo_type.addItem(label, key)
        self.combo_type.setFixedWidth(160)
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        lay.addWidget(self.combo_type)

        # Produit / description
        self.inp_produit = QLineEdit()
        self.inp_produit.setPlaceholderText("Produit...")
        self.inp_produit.setFixedWidth(140)
        lay.addWidget(self.inp_produit)

        # Quantité
        self.inp_qte = QLineEdit()
        self.inp_qte.setFixedWidth(75)
        self.inp_qte.setPlaceholderText("Qté")
        self.inp_qte.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,6}([.,]\d{0,2})?$")))
        lay.addWidget(self.inp_qte)

        # Unité
        self.lbl_unite = QLabel("")
        self.lbl_unite.setFixedWidth(50)
        self.lbl_unite.setStyleSheet(
            "color: palette(mid); font-size: 11px; border: none;")
        lay.addWidget(self.lbl_unite)

        # Hausse : pose ou retrait
        self.combo_hausse = QComboBox()
        self.combo_hausse.addItems(["Pose hausse", "Retrait hausse"])
        self.combo_hausse.setVisible(False)
        lay.addWidget(self.combo_hausse)

        # Notes
        self.inp_notes = QLineEdit()
        self.inp_notes.setPlaceholderText("Notes...")
        lay.addWidget(self.inp_notes, 1)

        # Bouton supprimer
        btn_sup = QPushButton("×")
        btn_sup.setFixedSize(22, 22)
        btn_sup.setStyleSheet("""
            QPushButton {
                background: transparent; color: #9ca3af;
                border: none; font-size: 16px; font-weight: bold;
                border-radius: 11px;
            }
            QPushButton:hover { background: #FEE2E2; color: #DC2626; }
        """)
        btn_sup.clicked.connect(lambda: self.on_supprimer(self))
        lay.addWidget(btn_sup)

        # Init avec le premier type
        self._on_type_changed()

    def _on_type_changed(self):
        type_key = self.combo_type.currentData()
        cfg = self.CONFIG.get(type_key, (None, None, None, None))
        lbl_produit, lbl_qte, unite, placeholder = cfg

        # Produit
        if lbl_produit:
            self.inp_produit.setVisible(True)
            self.inp_produit.setPlaceholderText(
                placeholder or lbl_produit)
        else:
            self.inp_produit.setVisible(False)
            self.inp_produit.clear()

        # Quantité
        if lbl_qte:
            self.inp_qte.setVisible(True)
            self.lbl_unite.setText(unite or "")
            self.lbl_unite.setVisible(True)
        else:
            self.inp_qte.setVisible(False)
            self.lbl_unite.setVisible(False)

        # Hausse spécial
        if type_key == "hausse":
            self.combo_hausse.setVisible(True)
        else:
            self.combo_hausse.setVisible(False)

    def get_data(self) -> dict | None:
        type_key = self.combo_type.currentData()
        cfg = self.CONFIG.get(type_key, (None, None, None, None))
        _, lbl_qte, unite, _ = cfg

        produit  = self.inp_produit.text().strip() or None

        try:
            qte_txt = self.inp_qte.text().replace(",", ".").strip()
            quantite = float(qte_txt) if lbl_qte and qte_txt else None
        except ValueError:
            quantite = None
        
        notes    = self.inp_notes.text().strip() or None

        # Hausse : produit = "Pose" ou "Retrait"
        if type_key == "hausse":
            produit = self.combo_hausse.currentText()

        return {
            "type":     type_key,
            "produit":  produit,
            "quantite": quantite,
            "unite":    unite,
            "notes":    notes,
        }