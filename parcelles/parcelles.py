# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import *

import traceback

CATEGORIES_CULTURE = {
    "maraichage":   "🥕 Maraîchage",
    "arbo":         "🌳 Arboriculture",
    "jachere":      "🟫 Jachère",
    "engrais_vert": "🌱 Engrais vert",
}


# ──────────────────────────────────────────────
# Widget catégories PPP (tags avec recherche)
# ──────────────────────────────────────────────
class CategoriesPPPWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._toutes_categories = []
        self._selections = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.inp_recherche = QLineEdit()
        self.inp_recherche.setPlaceholderText("Rechercher une culture e-phy...")
        self.inp_recherche.textChanged.connect(self._filtrer)
        layout.addWidget(self.inp_recherche)

        self.liste = QListWidget()
        self.liste.setMaximumHeight(110)
        self.liste.itemDoubleClicked.connect(self._ajouter_depuis_liste)
        self.liste.setVisible(False)
        layout.addWidget(self.liste)

        self.inp_recherche.installEventFilter(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(36)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tags_widget = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_widget)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(4)
        self.tags_layout.addStretch()
        scroll.setWidget(self.tags_widget)
        layout.addWidget(scroll)

    def eventFilter(self, obj, event):
        if obj is self.inp_recherche and event.type() == QEvent.FocusIn:
            self.liste.setVisible(self.liste.count() > 0)
        return super().eventFilter(obj, event)

    def charger_categories(self, categories: list):
        self._toutes_categories = categories
        self._filtrer("")

    def _filtrer(self, texte: str):
        self.liste.clear()
        terme = texte.lower().strip()
        for cat in self._toutes_categories:
            if cat in self._selections:
                continue
            if not terme or terme in cat.lower():
                self.liste.addItem(cat)
        self.liste.setVisible(self.liste.count() > 0)

    def _ajouter_depuis_liste(self, item):
        cat = item.text()
        if cat not in self._selections:
            self._selections.append(cat)
            self._ajouter_tag(cat)
        self.inp_recherche.clear()
        self.liste.setVisible(False)

    def _ajouter_tag(self, cat: str):
        tag = QWidget()
        tag.setProperty("cat", cat)
        tag.setStyleSheet("""
            QWidget { background:#DBEAFE; border:1px solid #93C5FD;
                border-radius:4px; }
        """)
        tag_lay = QHBoxLayout(tag)
        tag_lay.setContentsMargins(6, 2, 4, 2)
        tag_lay.setSpacing(4)
        lbl = QLabel(cat)
        lbl.setStyleSheet("font-size:11px; color:#1D4ED8; border:none;")
        tag_lay.addWidget(lbl)
        btn = QPushButton("×")
        btn.setFixedSize(14, 14)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#6B7280;
                border:none; font-size:13px; font-weight:bold; padding:0; }
            QPushButton:hover { color:#DC2626; }
        """)
        btn.clicked.connect(lambda checked=False, c=cat: self._supprimer_tag(c))
        tag_lay.addWidget(btn)
        idx = self.tags_layout.count() - 1
        self.tags_layout.insertWidget(idx, tag)

    def _supprimer_tag(self, cat: str):
        if cat in self._selections:
            self._selections.remove(cat)
        for i in range(self.tags_layout.count()):
            item = self.tags_layout.itemAt(i)
            if item and item.widget() and item.widget().property("cat") == cat:
                item.widget().deleteLater()
                break
        self._filtrer(self.inp_recherche.text())

    def get_selections(self) -> list:
        return list(self._selections)

    def set_selections(self, categories: list):
        for cat in list(self._selections):
            self._supprimer_tag(cat)
        self._selections = []
        for cat in categories:
            if cat:
                self._selections.append(cat)
                self._ajouter_tag(cat)
        self._filtrer(self.inp_recherche.text())


# ──────────────────────────────────────────────
# Ligne variété engrais vert
# ──────────────────────────────────────────────
class LigneVarieteEV(QFrame):
    def __init__(self, on_supprimer, variete="", taux=None, parent=None):
        super().__init__(parent)
        self.on_supprimer = on_supprimer
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(1)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)

        self.inp_variete = QLineEdit(variete)
        self.inp_variete.setPlaceholderText("Variété / espèce semée")
        lay.addWidget(self.inp_variete, 2)

        self.inp_taux = QLineEdit(str(taux) if taux is not None else "")
        self.inp_taux.setFixedWidth(60)
        self.inp_taux.setPlaceholderText("Taux")
        self.inp_taux.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,3}([.,]\d{0,1})?$")))
        lay.addWidget(self.inp_taux)

        lbl_pct = QLabel("%")
        lbl_pct.setStyleSheet("color:palette(mid);")
        lay.addWidget(lbl_pct)

        btn = QPushButton("×")
        btn.setFixedSize(20, 20)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#9ca3af;
                border:none; font-size:14px; font-weight:bold; }
            QPushButton:hover { background:#FEE2E2; color:#DC2626; }
        """)
        btn.clicked.connect(lambda: self.on_supprimer(self))
        lay.addWidget(btn)

    def get_data(self) -> dict | None:
        variete = self.inp_variete.text().strip()
        if not variete:
            return None
        try:
            taux_txt = self.inp_taux.text().replace(",", ".").strip()
            taux = float(taux_txt) if taux_txt else None
        except ValueError:
            taux = None
        return {"variete": variete, "taux_pct": taux}


# ──────────────────────────────────────────────
# Page Parcelles
# ──────────────────────────────────────────────
class ParcellePage(QWidget):
    parcelle_modifiee = Signal()

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_ecrire    = peut_action(current_user, "parcelles", "ecriture")
        self._peut_supprimer = peut_action(current_user, "parcelles", "suppression")
        self._parcelle_courante = None
        self._build_ui()
        self.btn_ajouter.setVisible(self._peut_ecrire)
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        titre = QLabel("Gestion des parcelles")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        top.addWidget(titre)
        top.addStretch()
        self.btn_ajouter = QPushButton("+ Ajouter une parcelle")
        self.btn_ajouter.clicked.connect(lambda: self._ouvrir_dialog_parcelle())
        top.addWidget(self.btn_ajouter)
        root.addLayout(top)

        filtre = QHBoxLayout()
        self.chk_archivees = QCheckBox("Afficher les parcelles archivées")
        self.chk_archivees.stateChanged.connect(self._charger)
        filtre.addWidget(self.chk_archivees)
        filtre.addStretch()
        root.addLayout(filtre)

        splitter = QSplitter(Qt.Horizontal)

        # ── Liste parcelles ───────────────────
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nom", "Surface", "Ruches"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_parcelle)
        self.table.cellDoubleClicked.connect(
            lambda row, col: self._ouvrir_dialog_parcelle(self.table.item(row, 0).data(Qt.UserRole))
        )

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 3):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.table)

        # ── Détail parcelle + cultures ────────
        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(8, 0, 0, 0)
        dl.setSpacing(8)

        self.fiche_group = QGroupBox("Fiche parcelle")
        fl = QFormLayout(self.fiche_group)
        fl.setSpacing(6)
        fl.setContentsMargins(8, 8, 8, 8)

        self.lbl_nom      = QLabel("—")
        self.lbl_surface  = QLabel("—")
        self.lbl_sol      = QLabel("—")
        self.lbl_ruches   = QLabel("—")
        self.lbl_surf_occ = QLabel("—")
        self.lbl_notes    = QLabel("—")
        self.lbl_notes.setWordWrap(True)

        for lbl in (self.lbl_nom, self.lbl_surface, self.lbl_sol,
                    self.lbl_ruches, self.lbl_surf_occ, self.lbl_notes):
            lbl.setStyleSheet("font-size:13px;")

        fl.addRow("Nom :",          self.lbl_nom)
        fl.addRow("Surface :",      self.lbl_surface)
        fl.addRow("Sol :",          self.lbl_sol)
        fl.addRow("Ruches :",       self.lbl_ruches)
        fl.addRow("Occupation :",   self.lbl_surf_occ)
        fl.addRow("Notes :",        self.lbl_notes)
        dl.addWidget(self.fiche_group)

        # Cultures de la parcelle
        cult_group = QGroupBox("Cultures sur cette parcelle")
        cult_lay = QVBoxLayout(cult_group)
        cult_lay.setContentsMargins(6, 6, 6, 6)

        cult_top = QHBoxLayout()
        cult_top.addStretch()
        self.btn_add_culture = QPushButton("+ Ajouter une culture")
        self.btn_add_culture.setEnabled(False)
        self.btn_add_culture.clicked.connect(self._ajouter_culture)
        cult_top.addWidget(self.btn_add_culture)
        cult_lay.addLayout(cult_top)

        self.table_cultures = QTableWidget(0, 5)
        self.table_cultures.setHorizontalHeaderLabels(
            ["Catégorie", "Espèce / Variété", "Surface", "Rendement", "Prix moyen"])
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.cellDoubleClicked.connect(
            lambda row, col: self._modifier_culture(self.table_cultures.item(row, 0).data(Qt.UserRole))
        )

        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setAlternatingRowColors(True)
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(self._menu_culture)
        ch = self.table_cultures.horizontalHeader()
        ch.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        ch.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 5):
            ch.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        cult_lay.addWidget(self.table_cultures)
        dl.addWidget(cult_group, 1)

        # Systèmes irrigation
        sys_group = QGroupBox("Systèmes d'irrigation")
        sys_lay = QVBoxLayout(sys_group)
        sys_lay.setContentsMargins(6, 6, 6, 6)
        sys_btn = QHBoxLayout()
        self.btn_add_sys = QPushButton("+ Ajouter un système")
        self.btn_add_sys.setEnabled(False)
        self.btn_add_sys.clicked.connect(self._ajouter_systeme)
        sys_btn.addWidget(self.btn_add_sys)
        sys_btn.addStretch()
        sys_lay.addLayout(sys_btn)
        self.table_sys = QTableWidget(0, 4)
        self.table_sys.setHorizontalHeaderLabels(
            ["Type", "Émetteurs / Débit", "Cultures couvertes", "Vol/h (L)"])
        self.table_sys.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sys.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sys.setAlternatingRowColors(True)
        self.table_sys.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_sys.customContextMenuRequested.connect(self._menu_systeme)
        self.table_sys.cellDoubleClicked.connect(
            lambda row, col: self._modifier_systeme(self.table_sys.item(row, 0).data(Qt.UserRole)))
        sh = self.table_sys.horizontalHeader()
        sh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(2, QHeaderView.Stretch)
        sh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table_sys.setMaximumHeight(160)
        sys_lay.addWidget(self.table_sys)
        dl.addWidget(sys_group)

        splitter.addWidget(detail)
        splitter.setSizes([380, 520])
        root.addWidget(splitter, 1)

    # ──────────────────────────────────────────
    # Chargement parcelles
    # ──────────────────────────────────────────
    def _charger(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.chk_archivees.isChecked():
                cur.execute("SELECT * FROM parcelles ORDER BY nom")
            else:
                cur.execute("SELECT * FROM parcelles WHERE actif=1 ORDER BY nom")
            rows = cur.fetchall()
            cur.close()

            self.table.setRowCount(0)
            for row in rows:
                p = dict(row)
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(p.get("nom", "")))
                surf = f"{p['surface_ha']} ha" if p.get("surface_ha") else "—"
                self.table.setItem(r, 1, QTableWidgetItem(surf))
                ruches_txt = "🐝 Oui" if p.get("has_ruches") else "—"
                self.table.setItem(r, 2, QTableWidgetItem(ruches_txt))
                self.table.item(r, 0).setData(Qt.UserRole, p["id"])

                if not p.get("actif"):
                    for col in range(3):
                        item = self.table.item(r, col)
                        if item:
                            item.setForeground(QColor("gray"))
                            f = item.font(); f.setItalic(True); item.setFont(f)
        except Exception as e:
            debug.debug(f"[parcelles] Erreur chargement : {e}")
            traceback.print_exc()

    def _on_selection(self):
        row = self.table.currentRow()
        if row < 0:
            self.btn_add_culture.setEnabled(False)
            self._parcelle_courante = None
            return
        item = self.table.item(row, 0)
        if not item:
            return
        parcelle_id = item.data(Qt.UserRole)
        self._parcelle_courante = parcelle_id
        self._afficher_detail(parcelle_id)
        self._charger_cultures(parcelle_id)
        self._charger_systemes(parcelle_id)
        self.btn_add_culture.setEnabled(self._peut_ecrire)
        self.btn_add_sys.setEnabled(self._peut_ecrire)

    def _afficher_detail(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id=?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            self.fiche_group.setTitle(f"Fiche — {p.get('nom','')}")
            self.lbl_nom.setText(p.get("nom", "—"))
            self.lbl_surface.setText(
                f"{p['surface_ha']} ha" if p.get("surface_ha") else "—")
            self.lbl_sol.setText(p.get("type_sol") or "—")

            if p.get("has_ruches"):
                commune = p.get("commune") or ""
                cp = p.get("code_postal_parc") or ""
                loc = f" — {cp} {commune}".strip() if (commune or cp) else ""
                self.lbl_ruches.setText(f"🐝 Oui{loc}")
            else:
                self.lbl_ruches.setText("Non")

            self.lbl_notes.setText(p.get("notes") or "—")
            self._maj_surface_occupee(p)
        except Exception:
            traceback.print_exc()

    def _maj_surface_occupee(self, p: dict):
        try:
            cultures = get_cultures_parcelle(p["id"])
            total_occ_m2 = sum(c.get("surface_occupee_m2") or 0 for c in cultures)
            total_occ_ha = total_occ_m2 / 10000
            surf_totale = p.get("surface_ha") or 0
            if surf_totale > 0:
                pct = (total_occ_ha / surf_totale * 100)
                txt = f"{total_occ_ha:.3f} / {surf_totale:.3f} ha ({pct:.0f}%)"
                if pct > 100:
                    self.lbl_surf_occ.setStyleSheet(
                        "color:#DC2626; font-weight:bold; font-size:13px;")
                else:
                    self.lbl_surf_occ.setStyleSheet("font-size:13px;")
                self.lbl_surf_occ.setText(txt)
            else:
                self.lbl_surf_occ.setText(f"{total_occ_ha:.3f} ha occupés")
        except Exception:
            self.lbl_surf_occ.setText("—")

    def _charger_cultures(self, parcelle_id: int):
        try:
            cultures = get_cultures_parcelle(parcelle_id)
            self.table_cultures.setRowCount(0)
            for c in cultures:
                r = self.table_cultures.rowCount()
                self.table_cultures.insertRow(r)

                cat_lbl = CATEGORIES_CULTURE.get(c.get("categorie"), c.get("categorie"))
                self.table_cultures.setItem(r, 0, QTableWidgetItem(cat_lbl))

                if c.get("categorie") == "engrais_vert":
                    nom = c.get("melange_nom") or "Engrais vert"
                elif c.get("categorie") == "jachere":
                    nom = "Jachère"
                else:
                    esp = c.get("espece") or "—"
                    var = c.get("variete")
                    nom = f"{esp} — {var}" if var else esp
                self.table_cultures.setItem(r, 1, QTableWidgetItem(nom))

                surf_m2 = c.get("surface_occupee_m2")
                surf_txt = f"{surf_m2/10000:.3f} ha" if surf_m2 else "—"
                self.table_cultures.setItem(r, 2, QTableWidgetItem(surf_txt))

                if c.get("categorie") == "arbo":
                    rend = c.get("rendement_ha")
                    rend_txt = f"{rend} t/ha" if rend else "—"
                elif c.get("categorie") == "maraichage":
                    rend = c.get("rendement_ml")
                    rend_txt = f"{rend} kg/m.l." if rend else "—"
                else:
                    rend_txt = "—"
                self.table_cultures.setItem(r, 3, QTableWidgetItem(rend_txt))

                if c.get("categorie") == "arbo":
                    prix = c.get("prix_moyen_tonne")
                    prix_txt = f"{prix} €/t" if prix else "—"
                elif c.get("categorie") == "maraichage":
                    prix = c.get("prix_moyen_kg")
                    prix_txt = f"{prix} €/kg" if prix else "—"
                else:
                    prix_txt = "—"
                self.table_cultures.setItem(r, 4, QTableWidgetItem(prix_txt))

                self.table_cultures.item(r, 0).setData(Qt.UserRole, c["id"])

                if c.get("categorie") == "jachere":
                    for col in range(5):
                        item = self.table_cultures.item(r, col)
                        if item:
                            item.setForeground(QColor("#9ca3af"))
                            f = item.font(); f.setItalic(True); item.setFont(f)
                elif c.get("categorie") == "engrais_vert":
                    for col in range(5):
                        item = self.table_cultures.item(r, col)
                        if item:
                            item.setForeground(QColor("#15803d"))
                elif c.get("categorie") == "arbo":
                    for col in range(5):
                        item = self.table_cultures.item(r, col)
                        if item:
                            item.setForeground(QColor("#92400e"))
        except Exception:
            traceback.print_exc()

    # ──────────────────────────────────────────
    # Actions Parcelle
    # ──────────────────────────────────────────
    def _ouvrir_dialog_parcelle(self, parcelle_id=None):
        dlg = DialogParcelle(parcelle_id=parcelle_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger()
            self.parcelle_modifiee.emit()

    def _menu_parcelle(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        parcelle_id = item.data(Qt.UserRole)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT actif FROM parcelles WHERE id=?", (parcelle_id,))
            actif = cur.fetchone()[0]
            cur.close()
        except Exception:
            actif = 1

        menu = QMenu(self)
        if self._peut_ecrire:
            menu.addAction("Modifier",
                lambda: self._ouvrir_dialog_parcelle(parcelle_id))
        if self._peut_supprimer:
            menu.addSeparator()
            if actif:
                menu.addAction("Archiver",
                    lambda: self._set_actif(parcelle_id, False))
            else:
                menu.addAction("Réactiver",
                    lambda: self._set_actif(parcelle_id, True))
        if not menu.isEmpty():
            menu.exec(self.table.viewport().mapToGlobal(pos))

    def _set_actif(self, parcelle_id: int, actif: bool):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE parcelles SET actif=? WHERE id=?",
                        (1 if actif else 0, parcelle_id))
            conn.commit()
            cur.close()
            self._charger()
            self.parcelle_modifiee.emit()
        except Exception:
            traceback.print_exc()

    def _ajouter_culture(self):
        if not self._parcelle_courante:
            return
        dlg = DialogCulture(parcelle_id=self._parcelle_courante, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_cultures(self._parcelle_courante)
            self._on_selection()
            self.parcelle_modifiee.emit()

    def _menu_culture(self, pos):
        row = self.table_cultures.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_cultures.item(row, 0)
        culture_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        if self._peut_ecrire:
            menu.addAction("Modifier",
                lambda: self._modifier_culture(culture_id))
        if self._peut_supprimer:
            menu.addSeparator()
            menu.addAction("Supprimer",
                lambda: self._supprimer_culture(culture_id))
        if not menu.isEmpty():
            menu.exec(self.table_cultures.viewport().mapToGlobal(pos))

    def _modifier_culture(self, culture_id: int):
        dlg = DialogCulture(
            parcelle_id=self._parcelle_courante,
            culture_id=culture_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_cultures(self._parcelle_courante)
            self._on_selection()
            self.parcelle_modifiee.emit()

    def _supprimer_culture(self, culture_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer cette culture de la parcelle ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM cultures_parcelle WHERE id=?",
                            (culture_id,))
                conn.commit()
                cur.close()
                self._charger_cultures(self._parcelle_courante)
                self._on_selection()
                self.parcelle_modifiee.emit()
            except Exception:
                traceback.print_exc()

    def _charger_systemes(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM irrigation_systemes
                WHERE parcelle_id=? AND actif=1
                ORDER BY type_emetteur
            """, (parcelle_id,))
            rows = cur.fetchall()

            self.table_sys.setRowCount(0)
            for row in rows:
                s = dict(row)
                r = self.table_sys.rowCount()
                self.table_sys.insertRow(r)
                self.table_sys.setItem(r, 0,
                    QTableWidgetItem(s.get("type_emetteur", "").capitalize()))
                self.table_sys.setItem(r, 1, QTableWidgetItem(
                    f"{s.get('nb_emetteurs', 0)} × {s.get('debit_lh', 0)} L/h"))

                cur.execute("""
                    SELECT cp.espece, cp.variete, cp.categorie
                    FROM irrigation_systeme_cultures isc
                    JOIN cultures_parcelle cp ON cp.id = isc.culture_parcelle_id
                    WHERE isc.systeme_id = ?
                """, (s["id"],))
                cultures_liees = cur.fetchall()
                if cultures_liees:
                    noms = []
                    for esp, var, catg in cultures_liees:
                        if catg == "jachere":
                            noms.append("Jachère")
                        elif catg == "engrais_vert":
                            noms.append("Engrais vert")
                        else:
                            noms.append(f"{esp}" + (f" ({var})" if var else ""))
                    cultures_txt = ", ".join(noms)
                else:
                    cultures_txt = "— Aucune culture liée —"
                self.table_sys.setItem(r, 2, QTableWidgetItem(cultures_txt))

                vol_h = s.get("nb_emetteurs", 0) * s.get("debit_lh", 0)
                self.table_sys.setItem(r, 3, QTableWidgetItem(f"{vol_h:.0f}"))
                self.table_sys.item(r, 0).setData(Qt.UserRole, s["id"])
            cur.close()
        except Exception:
            traceback.print_exc()

    def _ajouter_systeme(self):
        if not self._parcelle_courante:
            return
        dlg = DialogSysteme(parcelle_id=self._parcelle_courante, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_systemes(self._parcelle_courante)

    def _menu_systeme(self, pos):
        row = self.table_sys.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_sys.item(row, 0)
        systeme_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        if self._peut_ecrire:
            menu.addAction("Modifier",
                lambda: self._modifier_systeme(systeme_id))
        if self._peut_supprimer:
            menu.addAction("Supprimer",
                lambda: self._supprimer_systeme(systeme_id))
        if not menu.isEmpty():
            menu.exec(self.table_sys.viewport().mapToGlobal(pos))

    def _modifier_systeme(self, systeme_id: int):
        dlg = DialogSysteme(systeme_id=systeme_id,
                            parcelle_id=self._parcelle_courante, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_systemes(self._parcelle_courante)

    def _supprimer_systeme(self, systeme_id: int):
        rep = QMessageBox.question(self, "Confirmer", "Supprimer ce système ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE irrigation_systemes SET actif=0 WHERE id=?",
                            (systeme_id,))
                conn.commit()
                cur.close()
                self._charger_systemes(self._parcelle_courante)
            except Exception:
                traceback.print_exc()

    def recharger_parcelles(self):
        self._charger()


# ──────────────────────────────────────────────
# Dialog Parcelle (surface uniquement)
# ──────────────────────────────────────────────
class DialogParcelle(QDialog):
    def __init__(self, parcelle_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self.setWindowTitle(
            "Nouvelle parcelle" if not parcelle_id else "Modifier la parcelle")
        self.setMinimumWidth(440)
        self._build_ui()
        if parcelle_id:
            self._charger(parcelle_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_nom = QLineEdit()
        self.inp_nom.setMaxLength(150)
        form.addRow("Nom *", self.inp_nom)

        self.inp_sol = QLineEdit()
        self.inp_sol.setPlaceholderText("Ex: limoneux, argileux...")
        form.addRow("Type de sol", self.inp_sol)

        self.inp_surface_ha = QDoubleSpinBox()
        self.inp_surface_ha.setRange(0, 9999)
        self.inp_surface_ha.setDecimals(4)
        self.inp_surface_ha.setSuffix(" ha")
        form.addRow("Surface *", self.inp_surface_ha)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        form.addRow(sep)

        self.chk_ruches = QCheckBox("Des ruches sont présentes sur cette parcelle")
        form.addRow("", self.chk_ruches)

        self.w_ruches_loc = QWidget()
        rl_lay = QFormLayout(self.w_ruches_loc)
        rl_lay.setContentsMargins(20, 4, 0, 0)
        cp_vil = QWidget()
        cp_lay = QHBoxLayout(cp_vil)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_cp = QLineEdit()
        self.inp_cp.setFixedWidth(60)
        self.inp_cp.setMaxLength(5)
        self.inp_cp.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,5}$")))
        self.inp_commune = QLineEdit()
        self.inp_commune.setPlaceholderText("Commune")
        cp_lay.addWidget(self.inp_cp)
        cp_lay.addWidget(self.inp_commune)
        rl_lay.addRow("CP / Commune", cp_vil)
        self.w_ruches_loc.setVisible(False)
        self.chk_ruches.toggled.connect(self.w_ruches_loc.setVisible)
        form.addRow(self.w_ruches_loc)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        form.addRow(sep2)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        form.addRow("Notes", self.inp_notes)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _charger(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id=?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(p.get("nom", ""))
            self.inp_sol.setText(p.get("type_sol") or "")
            self.inp_surface_ha.setValue(p.get("surface_ha") or 0)
            self.chk_ruches.setChecked(bool(p.get("has_ruches")))
            self.inp_commune.setText(p.get("commune") or "")
            self.inp_cp.setText(p.get("code_postal_parc") or "")
            self.inp_notes.setPlainText(p.get("notes") or "")
        except Exception:
            traceback.print_exc()

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant", "Le nom est obligatoire.")
            return

        sol = self.inp_sol.text().strip() or None
        surface_ha = self.inp_surface_ha.value() or None
        has_ruches = 1 if self.chk_ruches.isChecked() else 0
        commune = self.inp_commune.text().strip() or None
        cp = self.inp_cp.text().strip() or None
        notes = self.inp_notes.toPlainText().strip() or None

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.parcelle_id:
                cur.execute("""
                    UPDATE parcelles SET
                        nom=?, type_sol=?, surface_ha=?, has_ruches=?,
                        commune=?, code_postal_parc=?, notes=?
                    WHERE id=?
                """, (nom, sol, surface_ha, has_ruches,
                      commune, cp, notes, self.parcelle_id))
            else:
                cur.execute("""
                    INSERT INTO parcelles (
                        nom, type_sol, surface_ha, has_ruches,
                        commune, code_postal_parc, notes
                    ) VALUES (?,?,?,?,?,?,?)
                """, (nom, sol, surface_ha, has_ruches, commune, cp, notes))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))


# ──────────────────────────────────────────────
# Dialog Culture (formulaires distincts maraîchage/arbo)
# ──────────────────────────────────────────────
class DialogCulture(QDialog):
    def __init__(self, parcelle_id: int, culture_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self.culture_id  = culture_id
        self._lignes_ev = []
        self._parcelle_info = self._get_parcelle_info()
        self._params = get_parametres_app()
        self.setWindowTitle(
            "Nouvelle culture" if not culture_id else "Modifier la culture")
        self.setMinimumWidth(540)
        self.setMinimumHeight(600)
        self._build_ui()
        if culture_id:
            self._charger(culture_id)

    def _get_parcelle_info(self) -> dict:
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id=?", (self.parcelle_id,))
            row = cur.fetchone()
            cur.close()
            return dict(row) if row else {}
        except Exception:
            return {}

    def _build_ui(self):
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setContentsMargins(8, 8, 8, 8)

        nom_p = self._parcelle_info.get("nom", "")
        surf_p = self._parcelle_info.get("surface_ha")
        lbl_parcelle = QLabel(
            f"Parcelle : {nom_p}" +
            (f" ({surf_p} ha)" if surf_p else ""))
        lbl_parcelle.setStyleSheet("font-weight:bold; color:palette(mid);")
        form.addRow(lbl_parcelle)

        self.combo_categorie = QComboBox()
        for key, label in CATEGORIES_CULTURE.items():
            self.combo_categorie.addItem(label, key)
        self.combo_categorie.currentIndexChanged.connect(self._on_categorie_changed)
        form.addRow("Catégorie *", self.combo_categorie)

        # ── Bloc commun espèce/variété ────────
        self.w_espece = QWidget()
        e_lay = QFormLayout(self.w_espece)
        e_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_espece = QLineEdit()
        self.inp_espece.setPlaceholderText("Ex: Tomate, Pommier...")
        self.inp_espece.editingFinished.connect(self._charger_npk_espece)
        e_lay.addRow("Espèce *", self.inp_espece)
        self.inp_variete = QLineEdit()
        self.inp_variete.setPlaceholderText("Optionnel")
        e_lay.addRow("Variété", self.inp_variete)

        sep_npk = QLabel("── Besoins NPK (kg/ha) — partagés avec Fertilisants ──")
        sep_npk.setStyleSheet("color:gray; font-size:11px;")
        e_lay.addRow(sep_npk)

        npk_w = QWidget()
        npk_lay = QHBoxLayout(npk_w)
        npk_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_n = QDoubleSpinBox()
        self.inp_n.setRange(0, 9999)
        self.inp_n.setDecimals(1)
        self.inp_n.setPrefix("N: ")
        self.inp_p = QDoubleSpinBox()
        self.inp_p.setRange(0, 9999)
        self.inp_p.setDecimals(1)
        self.inp_p.setPrefix("P: ")
        self.inp_k = QDoubleSpinBox()
        self.inp_k.setRange(0, 9999)
        self.inp_k.setDecimals(1)
        self.inp_k.setPrefix("K: ")
        npk_lay.addWidget(self.inp_n)
        npk_lay.addWidget(self.inp_p)
        npk_lay.addWidget(self.inp_k)
        e_lay.addRow("NPK", npk_w)

        lbl_npk_info = QLabel(
            "ℹ Modifiable ici ou dans l'onglet Fertilisants — synchronisé.")
        lbl_npk_info.setStyleSheet("color:palette(mid); font-size:10px;")
        lbl_npk_info.setWordWrap(True)
        e_lay.addRow(lbl_npk_info)

        form.addRow(self.w_espece)
        # ── Bloc MARAÎCHAGE ───────────────────
        self.w_maraichage = QWidget()
        m_lay = QFormLayout(self.w_maraichage)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_lay.setSpacing(8)

        self.inp_nb_rangs_m = QSpinBox()
        self.inp_nb_rangs_m.setRange(0, 999)
        m_lay.addRow("Nombre de rangs", self.inp_nb_rangs_m)

        self.inp_dist_rangs_m = QDoubleSpinBox()
        self.inp_dist_rangs_m.setRange(0, 999)
        self.inp_dist_rangs_m.setSuffix(" cm")
        m_lay.addRow("Distance entre rangs", self.inp_dist_rangs_m)

        self.inp_dist_plants_m = QDoubleSpinBox()
        self.inp_dist_plants_m.setRange(0, 999)
        self.inp_dist_plants_m.setSuffix(" cm")
        m_lay.addRow("Distance entre plants", self.inp_dist_plants_m)

        sep_p = QLabel("── Planche ──")
        sep_p.setStyleSheet("color:gray; font-size:11px;")
        m_lay.addRow(sep_p)

        self.inp_largeur_planche = QDoubleSpinBox()
        self.inp_largeur_planche.setRange(0, 50)
        self.inp_largeur_planche.setDecimals(2)
        self.inp_largeur_planche.setSuffix(" m")
        self.inp_largeur_planche.setValue(self._params.get("largeur_planche_defaut", 1.20))
        self.inp_largeur_planche.valueChanged.connect(self._calculer_maraichage)
        m_lay.addRow("Largeur planche", self.inp_largeur_planche)

        self.inp_longueur_planche = QDoubleSpinBox()
        self.inp_longueur_planche.setRange(0, 9999)
        self.inp_longueur_planche.setDecimals(1)
        self.inp_longueur_planche.setSuffix(" m")
        self.inp_longueur_planche.valueChanged.connect(self._calculer_maraichage)
        m_lay.addRow("Longueur planche", self.inp_longueur_planche)

        self.inp_nb_planches_m = QSpinBox()
        self.inp_nb_planches_m.setRange(0, 9999)
        self.inp_nb_planches_m.valueChanged.connect(self._calculer_maraichage)
        m_lay.addRow("Nombre de planches", self.inp_nb_planches_m)

        self.inp_passe_pied = QDoubleSpinBox()
        self.inp_passe_pied.setRange(0, 10)
        self.inp_passe_pied.setDecimals(2)
        self.inp_passe_pied.setSuffix(" m")
        self.inp_passe_pied.setValue(self._params.get("passe_pied_defaut", 0.40))
        self.inp_passe_pied.valueChanged.connect(self._calculer_maraichage)
        m_lay.addRow("Passe-pied", self.inp_passe_pied)

        self.lbl_calcul_m = QLabel("")
        self.lbl_calcul_m.setStyleSheet(
            "background:#EFF6FF; border:1px solid #93C5FD; "
            "border-radius:4px; padding:6px; color:#1D4ED8; font-size:12px;")
        self.lbl_calcul_m.setWordWrap(True)
        m_lay.addRow(self.lbl_calcul_m)

        self.inp_rendement_ml = QDoubleSpinBox()
        self.inp_rendement_ml.setRange(0, 9999)
        self.inp_rendement_ml.setDecimals(2)
        self.inp_rendement_ml.setSuffix(" kg/m linéaire")
        m_lay.addRow("Rendement", self.inp_rendement_ml)

        self.inp_prix_kg = QDoubleSpinBox()
        self.inp_prix_kg.setRange(0, 9999)
        self.inp_prix_kg.setDecimals(2)
        self.inp_prix_kg.setSuffix(" €/kg")
        m_lay.addRow("Prix moyen de vente", self.inp_prix_kg)

        form.addRow(self.w_maraichage)

        # ── Bloc ARBORICULTURE ────────────────
        self.w_arbo = QWidget()
        a_lay = QFormLayout(self.w_arbo)
        a_lay.setContentsMargins(0, 0, 0, 0)
        a_lay.setSpacing(8)

        self.inp_nb_rangs_a = QSpinBox()
        self.inp_nb_rangs_a.setRange(0, 999)
        a_lay.addRow("Nombre de rangs", self.inp_nb_rangs_a)

        self.inp_dist_rangs_a = QDoubleSpinBox()
        self.inp_dist_rangs_a.setRange(0, 99)
        self.inp_dist_rangs_a.setDecimals(2)
        self.inp_dist_rangs_a.setSuffix(" m")
        self.inp_dist_rangs_a.valueChanged.connect(self._calculer_arbo)
        a_lay.addRow("Distance entre rangs", self.inp_dist_rangs_a)

        self.inp_dist_arbres_a = QDoubleSpinBox()
        self.inp_dist_arbres_a.setRange(0, 99)
        self.inp_dist_arbres_a.setDecimals(2)
        self.inp_dist_arbres_a.setSuffix(" m")
        self.inp_dist_arbres_a.valueChanged.connect(self._calculer_arbo)
        a_lay.addRow("Distance entre arbres", self.inp_dist_arbres_a)

        self.inp_nb_arbres_rang = QSpinBox()
        self.inp_nb_arbres_rang.setRange(0, 9999)
        self.inp_nb_arbres_rang.valueChanged.connect(self._calculer_arbo)
        a_lay.addRow("Nombre d'arbres par rang", self.inp_nb_arbres_rang)

        self.lbl_calcul_a = QLabel("")
        self.lbl_calcul_a.setStyleSheet(
            "background:#FEF3C7; border:1px solid #F59E0B; "
            "border-radius:4px; padding:6px; color:#92400E; font-size:12px;")
        self.lbl_calcul_a.setWordWrap(True)
        a_lay.addRow(self.lbl_calcul_a)

        self.inp_surface_arbo = QDoubleSpinBox()
        self.inp_surface_arbo.setRange(0, 9999)
        self.inp_surface_arbo.setDecimals(4)
        self.inp_surface_arbo.setSuffix(" ha")
        self.inp_surface_arbo.setReadOnly(True)
        self.inp_surface_arbo.setStyleSheet(
            "background: palette(window); color: palette(text);")
        a_lay.addRow("Surface occupée (calculée)", self.inp_surface_arbo)

        self.chk_surface_manuelle = QCheckBox(
            "Saisir la surface manuellement (vignes en foule, formes irrégulières...)")
        self.chk_surface_manuelle.toggled.connect(self._toggle_surface_manuelle)
        a_lay.addRow("", self.chk_surface_manuelle)

        self.inp_rendement_ha = QDoubleSpinBox()
        self.inp_rendement_ha.setRange(0, 9999)
        self.inp_rendement_ha.setDecimals(2)
        self.inp_rendement_ha.setSuffix(" t/ha")
        a_lay.addRow("Rendement", self.inp_rendement_ha)

        self.inp_prix_tonne = QDoubleSpinBox()
        self.inp_prix_tonne.setRange(0, 99999)
        self.inp_prix_tonne.setDecimals(2)
        self.inp_prix_tonne.setSuffix(" €/t")
        a_lay.addRow("Prix moyen de vente", self.inp_prix_tonne)

        form.addRow(self.w_arbo)

        # ── Bloc ENGRAIS VERT ─────────────────
        self.w_ev = QWidget()
        ev_lay = QVBoxLayout(self.w_ev)
        ev_lay.setContentsMargins(0, 0, 0, 0)
        ev_lay.setSpacing(6)

        ev_form = QFormLayout()
        self.inp_melange_nom = QLineEdit()
        self.inp_melange_nom.setPlaceholderText(
            "Ex: Mélange prairie temporaire, Phacélie...")
        ev_form.addRow("Nom du mélange", self.inp_melange_nom)
        ev_lay.addLayout(ev_form)

        lbl_var = QLabel("Variétés semées")
        lbl_var.setStyleSheet("font-weight:bold; font-size:12px;")
        ev_lay.addWidget(lbl_var)

        self.ev_varietes_lay = QVBoxLayout()
        self.ev_varietes_lay.setSpacing(4)
        ev_lay.addLayout(self.ev_varietes_lay)

        btn_add_var = QPushButton("+ Ajouter une variété")
        btn_add_var.clicked.connect(lambda: self._ajouter_variete_ev())
        btn_add_var.setStyleSheet("""
            QPushButton { border:1px dashed palette(mid);
                border-radius:4px; padding:3px 10px; }
            QPushButton:hover { border-color:#16a34a; color:#16a34a; }
        """)
        ev_lay.addWidget(btn_add_var)
        form.addRow(self.w_ev)

        # ── Surface (jachère / engrais vert) ──
        self.w_surface_simple = QWidget()
        s_lay = QFormLayout(self.w_surface_simple)
        s_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_surface_simple = QDoubleSpinBox()
        self.inp_surface_simple.setRange(0, 9999)
        self.inp_surface_simple.setDecimals(4)
        self.inp_surface_simple.setSuffix(" ha")
        s_lay.addRow("Surface occupée *", self.inp_surface_simple)
        form.addRow(self.w_surface_simple)

        # ── PPP ───────────────────────────────
        self.w_ppp_sep = QLabel("── Catégories PPP ──")
        self.w_ppp_sep.setStyleSheet("color:gray; font-size:11px;")
        form.addRow(self.w_ppp_sep)

        self.w_ppp_container = QWidget()
        ppp_lay = QFormLayout(self.w_ppp_container)
        ppp_lay.setContentsMargins(0, 0, 0, 0)
        self.cat_ppp_widget = CategoriesPPPWidget()
        ppp_lay.addRow("Cultures e-phy", self.cat_ppp_widget)
        form.addRow(self.w_ppp_container)

        try:
            cur = get_connection().cursor()
            cur.execute("SELECT DISTINCT culture FROM ppp_usages ORDER BY culture")
            cats = [row[0] for row in cur.fetchall()]
            cur.close()
            self.cat_ppp_widget.charger_categories(cats)
        except Exception:
            pass

        # ── Notes ─────────────────────────────
        sep_notes = QLabel("── Notes ──")
        sep_notes.setStyleSheet("color:gray; font-size:11px;")
        form.addRow(sep_notes)
        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(60)
        form.addRow("Notes", self.inp_notes)

        scroll.setWidget(w)
        root.addWidget(scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._on_categorie_changed()
        self._calculer_maraichage()
        self._calculer_arbo()

    def _on_categorie_changed(self):
        cat = self.combo_categorie.currentData()
        self.w_espece.setVisible(cat in ("maraichage", "arbo"))
        self.w_maraichage.setVisible(cat == "maraichage")
        self.w_arbo.setVisible(cat == "arbo")
        self.w_ev.setVisible(cat == "engrais_vert")
        self.w_surface_simple.setVisible(cat in ("jachere",))
        show_ppp = cat in ("maraichage", "arbo")
        self.w_ppp_sep.setVisible(show_ppp)
        self.w_ppp_container.setVisible(show_ppp)

    def _charger_npk_espece(self):
        espece = self.inp_espece.text().strip()
        if not espece:
            return
        npk = get_npk_culture_ref(espece)
        self.inp_n.setValue(npk["n"] or 0)
        self.inp_p.setValue(npk["p"] or 0)
        self.inp_k.setValue(npk["k"] or 0)

    def _calculer_maraichage(self):
        largeur = self.inp_largeur_planche.value()
        longueur = self.inp_longueur_planche.value()
        nb = self.inp_nb_planches_m.value()
        passe_pied = self.inp_passe_pied.value()

        surface_planches = largeur * longueur * nb
        surface_passe_pieds = passe_pied * longueur * nb
        self._surface_calc_m = surface_planches

        surf_p = self._parcelle_info.get("surface_ha")
        if surf_p:
            surf_totale_m2 = surf_p * 10000
            pct = (surface_planches / surf_totale_m2 * 100) if surf_totale_m2 else 0
            self.lbl_calcul_m.setText(
                f"📐 {nb} planche(s) {largeur}×{longueur}m = "
                f"{surface_planches:.0f} m² ({pct:.1f}% de la parcelle)\n"
                f"+ passe-pieds : {surface_passe_pieds:.0f} m²")
        else:
            self.lbl_calcul_m.setText(
                f"📐 {nb} planche(s) {largeur}×{longueur}m = "
                f"{surface_planches:.0f} m²\n"
                f"+ passe-pieds : {surface_passe_pieds:.0f} m²")

    def _calculer_arbo(self):
        dist_rangs = self.inp_dist_rangs_a.value()
        dist_arbres = self.inp_dist_arbres_a.value()
        if dist_rangs > 0 and dist_arbres > 0:
            densite_ha = 10000 / (dist_rangs * dist_arbres)
            self._densite_calc = densite_ha
            self.lbl_calcul_a.setText(f"🌳 Densité estimée : {densite_ha:.0f} arbres/ha")
        else:
            self._densite_calc = None
            self.lbl_calcul_a.setText(
                "ℹ Renseignez les distances pour calculer la densité.")

    def _toggle_surface_manuelle(self, checked: bool):
        self.inp_surface_arbo.setReadOnly(not checked)
        if checked:
            self.inp_surface_arbo.setStyleSheet("")
        else:
            self.inp_surface_arbo.setStyleSheet(
                "background: palette(window); color: palette(mid);")
            self._calculer_arbo()

    def _ajouter_variete_ev(self, variete="", taux=None):
        ligne = LigneVarieteEV(
            on_supprimer=self._supprimer_variete_ev,
            variete=variete, taux=taux)
        self._lignes_ev.append(ligne)
        self.ev_varietes_lay.addWidget(ligne)

    def _supprimer_variete_ev(self, ligne):
        if ligne in self._lignes_ev:
            self._lignes_ev.remove(ligne)
        ligne.setParent(None)
        ligne.deleteLater()

    def _charger(self, culture_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM cultures_parcelle WHERE id=?", (culture_id,))
            c = dict(cur.fetchone())
            cur.close()

            cat = c.get("categorie", "maraichage")
            idx = self.combo_categorie.findData(cat)
            if idx >= 0:
                self.combo_categorie.setCurrentIndex(idx)

            self.inp_espece.setText(c.get("espece") or "")
            self.inp_variete.setText(c.get("variete") or "")
            self._charger_npk_espece()

            if cat == "maraichage":
                self.inp_nb_rangs_m.setValue(c.get("nb_rangs") or 0)
                self.inp_dist_rangs_m.setValue(c.get("distance_rangs") or 0)
                self.inp_dist_plants_m.setValue(c.get("distance_plants") or 0)
                if c.get("largeur_planche"):
                    self.inp_largeur_planche.setValue(c["largeur_planche"])
                self.inp_longueur_planche.setValue(c.get("longueur_planche") or 0)
                self.inp_nb_planches_m.setValue(c.get("nb_planches") or 0)
                if c.get("passe_pied"):
                    self.inp_passe_pied.setValue(c["passe_pied"])
                self.inp_rendement_ml.setValue(c.get("rendement_ml") or 0)
                self.inp_prix_kg.setValue(c.get("prix_moyen_kg") or 0)
            elif cat == "arbo":
                self.inp_nb_rangs_a.setValue(c.get("nb_rangs") or 0)
                self.inp_dist_rangs_a.setValue(c.get("distance_rangs") or 0)
                self.inp_dist_arbres_a.setValue(c.get("distance_plants") or 0)
                surf_m2 = c.get("surface_occupee_m2")
                self.inp_surface_arbo.setValue((surf_m2 / 10000) if surf_m2 else 0)
                self.inp_rendement_ha.setValue(c.get("rendement_ha") or 0)
                self.inp_prix_tonne.setValue(c.get("prix_moyen_tonne") or 0)
            elif cat == "engrais_vert":
                self.inp_melange_nom.setText(c.get("melange_nom") or "")
                varietes = get_engrais_vert_varietes(culture_id)
                for v in varietes:
                    self._ajouter_variete_ev(v["variete"], v.get("taux_pct"))
                surf_m2 = c.get("surface_occupee_m2")
                self.inp_surface_simple.setValue((surf_m2 / 10000) if surf_m2 else 0)
            elif cat == "jachere":
                surf_m2 = c.get("surface_occupee_m2")
                self.inp_surface_simple.setValue((surf_m2 / 10000) if surf_m2 else 0)

            cats = get_categories_ppp_culture(culture_id)
            self.cat_ppp_widget.set_selections(cats)

            self._on_categorie_changed()
            self._calculer_maraichage()
            self._calculer_arbo()
        except Exception:
            traceback.print_exc()

    def _valider(self):
        cat = self.combo_categorie.currentData()
        notes = self.inp_notes.toPlainText().strip() or None

        espece = variete = None
        nb_rangs = dist_rangs = dist_plants = None
        largeur_planche = longueur_planche = passe_pied = nb_planches = None
        rendement_ml = prix_kg = None
        rendement_ha = prix_tonne = None
        melange_nom = None
        surface_occupee_m2 = None
        densite_calc = None

        if cat == "maraichage":
            espece = self.inp_espece.text().strip()
            if not espece:
                QMessageBox.warning(self, "Champ manquant", "L'espèce est obligatoire.")
                return
            variete = self.inp_variete.text().strip() or None
            nb_rangs = self.inp_nb_rangs_m.value() or None
            dist_rangs = self.inp_dist_rangs_m.value() or None
            dist_plants = self.inp_dist_plants_m.value() or None
            largeur_planche = self.inp_largeur_planche.value() or None
            longueur_planche = self.inp_longueur_planche.value() or None
            nb_planches = self.inp_nb_planches_m.value() or None
            passe_pied = self.inp_passe_pied.value() or None
            rendement_ml = self.inp_rendement_ml.value() or None
            prix_kg = self.inp_prix_kg.value() or None
            surface_occupee_m2 = getattr(self, "_surface_calc_m", None)

        elif cat == "arbo":
            espece = self.inp_espece.text().strip()
            if not espece:
                QMessageBox.warning(self, "Champ manquant", "L'espèce est obligatoire.")
                return
            variete = self.inp_variete.text().strip() or None
            nb_rangs = self.inp_nb_rangs_a.value() or None
            dist_rangs = self.inp_dist_rangs_a.value() or None
            dist_plants = self.inp_dist_arbres_a.value() or None
            surface_ha = self.inp_surface_arbo.value()
            if not surface_ha:
                QMessageBox.warning(self, "Champ manquant",
                    "La surface occupée est obligatoire pour l'arboriculture.")
                return
            surface_occupee_m2 = surface_ha * 10000
            rendement_ha = self.inp_rendement_ha.value() or None
            prix_tonne = self.inp_prix_tonne.value() or None
            densite_calc = getattr(self, "_densite_calc", None)

        elif cat == "engrais_vert":
            melange_nom = self.inp_melange_nom.text().strip() or None
            surf_ha = self.inp_surface_simple.value()
            surface_occupee_m2 = surf_ha * 10000 if surf_ha else None

        elif cat == "jachere":
            surf_ha = self.inp_surface_simple.value()
            surface_occupee_m2 = surf_ha * 10000 if surf_ha else None

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.culture_id:
                cur.execute("""
                    UPDATE cultures_parcelle SET
                        categorie=?, espece=?, variete=?, nb_rangs=?,
                        distance_rangs=?, distance_plants=?,
                        largeur_planche=?, longueur_planche=?, nb_planches=?,
                        passe_pied=?, rendement_ml=?, prix_moyen_kg=?,
                        rendement_ha=?, prix_moyen_tonne=?, melange_nom=?,
                        densite_calculee=?, surface_occupee_m2=?, notes=?
                    WHERE id=?
                """, (cat, espece, variete, nb_rangs, dist_rangs, dist_plants,
                      largeur_planche, longueur_planche, nb_planches, passe_pied,
                      rendement_ml, prix_kg, rendement_ha, prix_tonne,
                      melange_nom, densite_calc, surface_occupee_m2, notes,
                      self.culture_id))
                cid = self.culture_id
            else:
                cur.execute("""
                    INSERT INTO cultures_parcelle (
                        parcelle_id, categorie, espece, variete, nb_rangs,
                        distance_rangs, distance_plants, largeur_planche,
                        longueur_planche, nb_planches, passe_pied,
                        rendement_ml, prix_moyen_kg, rendement_ha,
                        prix_moyen_tonne, melange_nom, densite_calculee,
                        surface_occupee_m2, notes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (self.parcelle_id, cat, espece, variete, nb_rangs,
                      dist_rangs, dist_plants, largeur_planche,
                      longueur_planche, nb_planches, passe_pied,
                      rendement_ml, prix_kg, rendement_ha, prix_tonne,
                      melange_nom, densite_calc, surface_occupee_m2, notes))
                cid = cur.lastrowid

            conn.commit()
            cur.close()

            if cat in ("maraichage", "arbo"):
                cats = self.cat_ppp_widget.get_selections()
                set_categories_ppp_culture(cid, cats)
                get_or_create_culture_ref(espece)
                set_npk_culture_ref(
                    espece, self.inp_n.value(),
                    self.inp_p.value(), self.inp_k.value())
            if cat == "engrais_vert":
                varietes_ev = [l.get_data() for l in self._lignes_ev]
                varietes_ev = [v for v in varietes_ev if v]
                set_engrais_vert_varietes(cid, varietes_ev)

            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))


# ──────────────────────────────────────────────
# Dialog Système d'irrigation (avec sélection multi-cultures)
# ──────────────────────────────────────────────
class DialogSysteme(QDialog):
    TYPES = ["goutteur", "asperseur", "micro-asperseur", "pivot", "rampe", "autre"]

    def __init__(self, parcelle_id: int, systeme_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self.systeme_id  = systeme_id
        self.setWindowTitle("Système d'irrigation")
        self.setMinimumWidth(440)
        self.setMinimumHeight(480)
        self._build_ui()
        self._charger_cultures_disponibles()
        if systeme_id:
            self._charger(systeme_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.combo_type = QComboBox()
        for t in self.TYPES:
            self.combo_type.addItem(t.capitalize(), t)
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type d'émetteur *", self.combo_type)

        # ── Bloc standard (tout sauf goutteur) ──
        self.inp_nb = QSpinBox()
        self.inp_nb.setRange(1, 99999)
        self.inp_nb.setSuffix(" émetteurs")
        self.inp_nb.valueChanged.connect(self._calc_vol)
        self.row_nb = form.addRow("Nombre *", self.inp_nb)

        # ── Bloc goutteur (distance + longueur) ──
        self.w_goutteur = QWidget()
        g_lay = QFormLayout(self.w_goutteur)
        g_lay.setContentsMargins(0, 0, 0, 0)
        g_lay.setSpacing(8)

        self.inp_distance_goutteurs = QDoubleSpinBox()
        self.inp_distance_goutteurs.setRange(1, 500)
        self.inp_distance_goutteurs.setDecimals(0)
        self.inp_distance_goutteurs.setSuffix(" cm")
        self.inp_distance_goutteurs.setValue(30)
        self.inp_distance_goutteurs.valueChanged.connect(self._calc_goutteurs)
        g_lay.addRow("Distance entre goutteurs", self.inp_distance_goutteurs)

        self.lbl_longueur_auto = QLabel("Longueur détectée : —")
        self.lbl_longueur_auto.setStyleSheet("color:#1D4ED8; font-size:11px;")
        self.lbl_longueur_auto.setWordWrap(True)
        g_lay.addRow(self.lbl_longueur_auto)

        self.chk_longueur_manuelle = QCheckBox("Saisir la longueur manuellement")
        self.chk_longueur_manuelle.toggled.connect(self._toggle_longueur_manuelle)
        g_lay.addRow(self.chk_longueur_manuelle)

        self.inp_longueur_manuelle = QDoubleSpinBox()
        self.inp_longueur_manuelle.setRange(0, 99999)
        self.inp_longueur_manuelle.setDecimals(1)
        self.inp_longueur_manuelle.setSuffix(" m")
        self.inp_longueur_manuelle.setEnabled(False)
        self.inp_longueur_manuelle.valueChanged.connect(self._calc_goutteurs)
        g_lay.addRow("Longueur totale", self.inp_longueur_manuelle)

        self.lbl_nb_calcule = QLabel("Nombre de goutteurs calculé : —")
        self.lbl_nb_calcule.setStyleSheet(
            "background:#EFF6FF; border:1px solid #93C5FD; "
            "border-radius:4px; padding:6px; color:#1D4ED8; font-size:12px;")
        g_lay.addRow(self.lbl_nb_calcule)

        form.addRow(self.w_goutteur)

        self.inp_debit = QDoubleSpinBox()
        self.inp_debit.setRange(0.1, 9999)
        self.inp_debit.setDecimals(1)
        self.inp_debit.setSuffix(" L/h")
        self.inp_debit.valueChanged.connect(self._calc_vol)
        form.addRow("Débit unitaire *", self.inp_debit)

        self.lbl_vol = QLabel("Volume/h : —")
        self.lbl_vol.setStyleSheet("color:palette(mid); font-size:12px;")
        form.addRow("", self.lbl_vol)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Ex: rang nord, zone A...")
        form.addRow("Description", self.inp_desc)

        layout.addLayout(form)

        sep = QLabel("── Cultures couvertes par ce système ──")
        sep.setStyleSheet("color:gray; font-size:11px;")
        layout.addWidget(sep)

        info = QLabel(
            "Sélectionnez une ou plusieurs cultures de cette parcelle "
            "irriguées par ce système.")
        info.setStyleSheet("color:palette(mid); font-size:11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.liste_cultures = QListWidget()
        self.liste_cultures.setSelectionMode(QAbstractItemView.MultiSelection)
        self.liste_cultures.setMaximumHeight(160)
        self.liste_cultures.itemSelectionChanged.connect(self._calc_goutteurs)
        layout.addWidget(self.liste_cultures)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._on_type_changed()

    def _on_type_changed(self):
        is_goutteur = self.combo_type.currentData() == "goutteur"
        self.inp_nb.setVisible(not is_goutteur)
        self.w_goutteur.setVisible(is_goutteur)
        if is_goutteur:
            self._calc_goutteurs()

    def _toggle_longueur_manuelle(self, checked: bool):
        self.inp_longueur_manuelle.setEnabled(checked)
        self._calc_goutteurs()

    def _longueur_cultures_selectionnees(self) -> float:
        """Somme des longueurs (nb_planches × longueur_planche) des
        cultures maraîchage sélectionnées qui ont ces infos."""
        total = 0.0
        manquantes = []
        for i in range(self.liste_cultures.count()):
            item = self.liste_cultures.item(i)
            if not item.isSelected():
                continue
            cid = item.data(Qt.UserRole)
            info = self._cultures_info.get(cid, {})
            nb_p = info.get("nb_planches")
            long_p = info.get("longueur_planche")
            if nb_p and long_p:
                total += nb_p * long_p
            else:
                manquantes.append(item.text())
        return total, manquantes

    def _calc_goutteurs(self):
        if self.combo_type.currentData() != "goutteur":
            return

        if self.chk_longueur_manuelle.isChecked():
            longueur = self.inp_longueur_manuelle.value()
            self.lbl_longueur_auto.setText(
                "Longueur saisie manuellement.")
        else:
            longueur, manquantes = self._longueur_cultures_selectionnees()
            if longueur > 0:
                txt = f"Longueur détectée : {longueur:.1f} m (depuis les planches sélectionnées)"
                if manquantes:
                    txt += f"\n⚠ Pas de longueur pour : {', '.join(manquantes)}"
                self.lbl_longueur_auto.setText(txt)
            else:
                self.lbl_longueur_auto.setText(
                    "⚠ Aucune longueur détectée — cochez « Saisir manuellement »\n"
                    "(utile pour l'arboriculture, sans planches définies).")

        distance_cm = self.inp_distance_goutteurs.value()
        if longueur > 0 and distance_cm > 0:
            nb = int((longueur * 100) / distance_cm)
            self._nb_goutteurs_calc = nb
            self.lbl_nb_calcule.setText(
                f"💧 {nb} goutteurs (longueur {longueur:.1f}m ÷ {distance_cm:.0f}cm)")
        else:
            self._nb_goutteurs_calc = 0
            self.lbl_nb_calcule.setText("Nombre de goutteurs calculé : —")

        self._calc_vol()

    def _calc_vol(self):
        if self.combo_type.currentData() == "goutteur":
            nb = getattr(self, "_nb_goutteurs_calc", 0)
        else:
            nb = self.inp_nb.value()
        vol = nb * self.inp_debit.value()
        self.lbl_vol.setText(f"Volume/h : {vol:.0f} L/h total")

    def _charger_cultures_disponibles(self):
        self._cultures_info = {}
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, categorie, espece, variete, melange_nom,
                       nb_planches, longueur_planche
                FROM cultures_parcelle
                WHERE parcelle_id=? AND actif=1
                ORDER BY id
            """, (self.parcelle_id,))
            for cid, cat, esp, var, melange, nb_p, long_p in cur.fetchall():
                self._cultures_info[cid] = {
                    "nb_planches": nb_p, "longueur_planche": long_p}
                if cat == "jachere":
                    label = "🟫 Jachère"
                elif cat == "engrais_vert":
                    label = f"🌱 {melange or 'Engrais vert'}"
                else:
                    icon = "🥕" if cat == "maraichage" else "🌳"
                    label = f"{icon} {esp or '—'}" + (f" — {var}" if var else "")
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, cid)
                self.liste_cultures.addItem(item)
            cur.close()
        except Exception:
            traceback.print_exc()

    def _charger(self, systeme_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM irrigation_systemes WHERE id=?",
                        (systeme_id,))
            s = dict(cur.fetchone())
            cur.close()
            idx = self.combo_type.findData(s.get("type_emetteur"))
            self.combo_type.setCurrentIndex(idx)
            self.inp_nb.setValue(s.get("nb_emetteurs", 1))
            self.inp_debit.setValue(s.get("debit_lh", 1.0))
            self.inp_desc.setText(s.get("description") or "")

            from db import get_cultures_systeme
            cultures_liees = get_cultures_systeme(systeme_id)
            ids_liees = {c["id"] for c in cultures_liees}
            for i in range(self.liste_cultures.count()):
                item = self.liste_cultures.item(i)
                if item.data(Qt.UserRole) in ids_liees:
                    item.setSelected(True)

            self._on_type_changed()

            # Pour un goutteur existant, si la longueur détectée ne
            # correspond pas au nb_emetteurs enregistré, on bascule en
            # saisie manuelle pour ne pas écraser la valeur historique.
            if s.get("type_emetteur") == "goutteur":
                longueur_auto, _ = self._longueur_cultures_selectionnees()
                distance = self.inp_distance_goutteurs.value()
                nb_attendu = int((longueur_auto * 100) / distance) if (longueur_auto and distance) else 0
                if nb_attendu != s.get("nb_emetteurs", 0):
                    self.chk_longueur_manuelle.setChecked(True)
                    if distance > 0:
                        longueur_manuelle = (s.get("nb_emetteurs", 0) * distance) / 100
                        self.inp_longueur_manuelle.setValue(longueur_manuelle)
                self._calc_goutteurs()

            self._calc_vol()
        except Exception:
            traceback.print_exc()

    def _valider(self):
        type_emetteur = self.combo_type.currentData()
        if type_emetteur == "goutteur":
            nb = getattr(self, "_nb_goutteurs_calc", 0)
            if not nb:
                QMessageBox.warning(self, "Calcul impossible",
                    "Impossible de calculer le nombre de goutteurs.\n"
                    "Sélectionnez une culture avec planches ou saisissez "
                    "la longueur manuellement.")
                return
        else:
            nb = self.inp_nb.value()
        debit = self.inp_debit.value()
        desc  = self.inp_desc.text().strip() or None

        culture_ids = [
            self.liste_cultures.item(i).data(Qt.UserRole)
            for i in range(self.liste_cultures.count())
            if self.liste_cultures.item(i).isSelected()
        ]

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.systeme_id:
                cur.execute("""
                    UPDATE irrigation_systemes
                    SET type_emetteur=?, nb_emetteurs=?, debit_lh=?, description=?
                    WHERE id=?
                """, (type_emetteur, nb, debit, desc, self.systeme_id))
                sid = self.systeme_id
            else:
                cur.execute("""
                    INSERT INTO irrigation_systemes
                    (parcelle_id, type_emetteur, nb_emetteurs, debit_lh, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.parcelle_id, type_emetteur, nb, debit, desc))
                sid = cur.lastrowid
            conn.commit()
            cur.close()

            from db import set_cultures_systeme
            set_cultures_systeme(sid, culture_ids)

            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))