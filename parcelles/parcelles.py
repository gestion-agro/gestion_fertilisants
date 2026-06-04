# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import (get_connection, get_categories_ppp_parcelle,
                set_categories_ppp_parcelle,
                get_engrais_vert_varietes, set_engrais_vert_varietes)
import utils.debug as debug
import traceback

# ── Labels types parcelle ─────────────────────
TYPES_PARCELLE = {
    "arbo":         "Arboriculture / Grandes cultures",
    "maraichage":   "Maraîchage",
    "ruche":        "Emplacement de ruche",
    "jachere":      "Jachère",
    "engrais_vert": "Engrais vert",
}


# ──────────────────────────────────────────────
# Widget sélection catégories PPP
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
        self.inp_recherche.focusInEvent = self._on_focus_in
        layout.addWidget(self.inp_recherche)

        self.liste = QListWidget()
        self.liste.setMaximumHeight(110)
        self.liste.setSelectionMode(QAbstractItemView.SingleSelection)
        self.liste.itemDoubleClicked.connect(self._ajouter_depuis_liste)
        self.liste.setVisible(False)
        layout.addWidget(self.liste)

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

    def _on_focus_in(self, event):
        self.liste.setVisible(True)
        QLineEdit.focusInEvent(self.inp_recherche, event)

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
# Widget ligne variété engrais vert
# ──────────────────────────────────────────────
class LigneVarieteEV(QFrame):
    def __init__(self, on_supprimer, variete="", taux=None, parent=None):
        super().__init__(parent)
        self.on_supprimer = on_supprimer
        self.setAutoFillBackground(True)
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
        lbl_pct.setStyleSheet("color:palette(mid); border:none;")
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
        self._build_ui()
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
        self.btn_ajouter = QPushButton("+ Ajouter")
        self.btn_ajouter.clicked.connect(lambda: self._ouvrir_dialog())
        top.addWidget(self.btn_ajouter)
        root.addLayout(top)

        filtre = QHBoxLayout()
        self.chk_archivees = QCheckBox("Afficher les parcelles archivées")
        self.chk_archivees.stateChanged.connect(self._charger)
        filtre.addWidget(self.chk_archivees)
        filtre.addStretch()
        root.addLayout(filtre)

        splitter = QSplitter(Qt.Horizontal)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Nom", "Type", "Culture", "Surface", "Sol", "État"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_context)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.table)

        # Panneau détail
        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(8, 0, 0, 0)
        dl.setSpacing(8)

        self.fiche_group = QGroupBox("Fiche parcelle")
        fl = QFormLayout(self.fiche_group)
        fl.setSpacing(6)
        fl.setContentsMargins(8, 8, 8, 8)

        self.lbl_nom       = QLabel("—")
        self.lbl_type      = QLabel("—")
        self.lbl_culture   = QLabel("—")
        self.lbl_surface   = QLabel("—")
        self.lbl_sol       = QLabel("—")
        self.lbl_rendement = QLabel("—")
        self.lbl_densite   = QLabel("—")
        self.lbl_cat_ppp   = QLabel("—")
        self.lbl_cat_ppp.setWordWrap(True)
        self.lbl_notes     = QLabel("—")
        self.lbl_notes.setWordWrap(True)

        for lbl in (self.lbl_nom, self.lbl_type, self.lbl_culture,
                    self.lbl_surface, self.lbl_sol, self.lbl_rendement,
                    self.lbl_densite, self.lbl_cat_ppp, self.lbl_notes):
            lbl.setStyleSheet("font-size:13px;")

        fl.addRow("Nom :",        self.lbl_nom)
        fl.addRow("Type :",       self.lbl_type)
        fl.addRow("Culture :",    self.lbl_culture)
        fl.addRow("Surface :",    self.lbl_surface)
        fl.addRow("Sol :",        self.lbl_sol)
        fl.addRow("Rendement :",  self.lbl_rendement)
        fl.addRow("Densité :",    self.lbl_densite)
        fl.addRow("Catég. PPP :", self.lbl_cat_ppp)
        fl.addRow("Notes :",      self.lbl_notes)
        dl.addWidget(self.fiche_group)

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
        self.table_sys = QTableWidget(0, 5)
        self.table_sys.setHorizontalHeaderLabels(
            ["Type", "Nb émetteurs", "Débit (L/h)", "Vol/h (L)", "Description"])
        self.table_sys.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sys.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sys.setAlternatingRowColors(True)
        self.table_sys.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_sys.customContextMenuRequested.connect(self._menu_systeme)
        sh = self.table_sys.horizontalHeader()
        sh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        sh.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_sys.setMaximumHeight(160)
        sys_lay.addWidget(self.table_sys)
        dl.addWidget(sys_group)
        dl.addStretch()

        splitter.addWidget(detail)
        splitter.setSizes([450, 350])
        root.addWidget(splitter, 1)

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

                type_key = p.get("type_unite", "arbo")
                self.table.setItem(r, 1, QTableWidgetItem(
                    TYPES_PARCELLE.get(type_key, type_key)))

                culture_txt = p.get("culture_reelle") or p.get("culture") or "—"
                if type_key == "jachere":
                    culture_txt = "Jachère"
                elif type_key == "engrais_vert":
                    culture_txt = p.get("melange_nom") or "Engrais vert"
                elif type_key == "ruche":
                    culture_txt = p.get("commune") or "—"
                self.table.setItem(r, 2, QTableWidgetItem(culture_txt))

                surf = self._surface_txt(p)
                self.table.setItem(r, 3, QTableWidgetItem(surf))
                self.table.setItem(r, 4, QTableWidgetItem(p.get("type_sol") or "—"))
                etat = "Active" if p.get("actif") else "Archivée"
                self.table.setItem(r, 5, QTableWidgetItem(etat))
                self.table.item(r, 0).setData(Qt.UserRole, p["id"])

                # Style selon type
                if not p.get("actif"):
                    self._colorier_ligne(r, QColor("gray"), italic=True)
                elif type_key == "jachere":
                    self._colorier_ligne(r, QColor("#9ca3af"), italic=True)
                elif type_key == "engrais_vert":
                    self._colorier_ligne(r, QColor("#15803d"), italic=False)
                elif type_key == "ruche":
                    self._colorier_ligne(r, QColor("#b45309"), italic=False)
        except Exception as e:
            debug.debug(f"[parcelles] Erreur chargement : {e}")
            traceback.print_exc()

    def _colorier_ligne(self, row: int, color: QColor, italic: bool):
        for col in range(6):
            item = self.table.item(row, col)
            if item:
                item.setForeground(color)
                if italic:
                    f = item.font(); f.setItalic(True); item.setFont(f)

    def _surface_txt(self, p: dict) -> str:
        type_key = p.get("type_unite", "arbo")
        if type_key == "maraichage":
            nb = p.get("nb_planches") or 1
            l  = p.get("longueur_m") or 0
            w  = p.get("largeur_m") or 0
            return f"{nb}×{l}×{w} m" if l and w else "—"
        elif p.get("surface_ha"):
            return f"{p['surface_ha']} ha"
        return "—"

    def _on_selection(self):
        row = self.table.currentRow()
        if row < 0:
            return
        item = self.table.item(row, 0)
        if not item:
            return
        parcelle_id = item.data(Qt.UserRole)
        self._afficher_detail(parcelle_id)
        self._charger_systemes(parcelle_id)
        self.btn_add_sys.setEnabled(True)
        self.btn_add_sys.setProperty("parcelle_id", parcelle_id)

    def _afficher_detail(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id=?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            type_key = p.get("type_unite", "arbo")
            self.fiche_group.setTitle(f"Fiche — {p.get('nom','')}")
            self.lbl_nom.setText(p.get("nom", "—"))
            self.lbl_type.setText(TYPES_PARCELLE.get(type_key, type_key))

            # Culture selon type
            if type_key == "jachere":
                self.lbl_culture.setText("Jachère")
            elif type_key == "engrais_vert":
                melange = p.get("melange_nom") or "—"
                varietes = get_engrais_vert_varietes(parcelle_id)
                if varietes:
                    v_txt = ", ".join(
                        f"{v['variete']}" + (f" ({v['taux_pct']}%)" if v['taux_pct'] else "")
                        for v in varietes)
                    self.lbl_culture.setText(f"{melange} — {v_txt}")
                else:
                    self.lbl_culture.setText(melange)
            elif type_key == "ruche":
                commune = p.get("commune") or "—"
                cp = p.get("code_postal_parc") or ""
                self.lbl_culture.setText(f"{cp} {commune}".strip() or "—")
            else:
                self.lbl_culture.setText(
                    p.get("culture_reelle") or p.get("culture") or "—")

            # Surface
            self.lbl_surface.setText(self._surface_detail(p))
            self.lbl_sol.setText(p.get("type_sol") or "—")

            # Rendement / densité
            if type_key == "maraichage":
                rend = p.get("rendement_m2")
                self.lbl_rendement.setText(f"{rend} kg/m²" if rend else "—")
                self.lbl_densite.setText("—")
            elif type_key == "arbo":
                rend = p.get("rendement_ha")
                self.lbl_rendement.setText(f"{rend} t/ha" if rend else "—")
                dens = p.get("densite_ha")
                self.lbl_densite.setText(f"{dens} unités/ha" if dens else "—")
            else:
                self.lbl_rendement.setText("—")
                self.lbl_densite.setText("—")

            cats = get_categories_ppp_parcelle(parcelle_id)
            self.lbl_cat_ppp.setText(", ".join(cats) if cats else "—")
            self.lbl_notes.setText(p.get("notes") or "—")
        except Exception as e:
            traceback.print_exc()

    def _surface_detail(self, p: dict) -> str:
        type_key = p.get("type_unite", "arbo")
        if type_key == "maraichage":
            nb = p.get("nb_planches") or 1
            l  = p.get("longueur_m") or 0
            w  = p.get("largeur_m") or 0
            surf_planche = l * w
            surf_total   = surf_planche * nb
            txt = f"{nb} planche(s) × {l}m × {w}m = {surf_total:.0f} m² total"
            nr = p.get("nb_rangs")
            if nr:
                txt += f" — {nr} rang(s)/planche"
            if p.get("distance_plants_cm"):
                txt += f" — {p['distance_plants_cm']} cm entre plants"
            return txt
        elif p.get("surface_ha"):
            return f"{p['surface_ha']} ha"
        return "—"

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
            cur.close()
            self.table_sys.setRowCount(0)
            for row in rows:
                s = dict(row)
                r = self.table_sys.rowCount()
                self.table_sys.insertRow(r)
                self.table_sys.setItem(r, 0, QTableWidgetItem(s.get("type_emetteur", "")))
                self.table_sys.setItem(r, 1, QTableWidgetItem(str(s.get("nb_emetteurs", 0))))
                self.table_sys.setItem(r, 2, QTableWidgetItem(str(s.get("debit_lh", 0))))
                vol_h = s.get("nb_emetteurs", 0) * s.get("debit_lh", 0)
                self.table_sys.setItem(r, 3, QTableWidgetItem(f"{vol_h:.0f}"))
                self.table_sys.setItem(r, 4, QTableWidgetItem(s.get("description") or ""))
                self.table_sys.item(r, 0).setData(Qt.UserRole, s["id"])
        except Exception:
            traceback.print_exc()

    def _ouvrir_dialog(self, parcelle_id=None):
        dlg = DialogParcelle(parcelle_id=parcelle_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger()
            self.parcelle_modifiee.emit()

    def _ajouter_systeme(self):
        parcelle_id = self.btn_add_sys.property("parcelle_id")
        if not parcelle_id:
            return
        dlg = DialogSysteme(parcelle_id=parcelle_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_systemes(parcelle_id)

    def _menu_context(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        parcelle_id = item.data(Qt.UserRole)
        type_key = ""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT type_unite, actif FROM parcelles WHERE id=?",
                        (parcelle_id,))
            r = cur.fetchone()
            cur.close()
            type_key = r[0] if r else ""
            actif    = r[1] if r else 1
        except Exception:
            actif = 1

        menu = QMenu(self)
        menu.addAction("Modifier", lambda: self._ouvrir_dialog(parcelle_id))
        menu.addSeparator()

        if actif:
            if type_key not in ("jachere", "engrais_vert"):
                menu.addAction("Mettre en jachère",
                    lambda: self._changer_type(parcelle_id, "jachere"))
                menu.addAction("Mettre en engrais vert",
                    lambda: self._changer_type(parcelle_id, "engrais_vert"))
            elif type_key == "jachere":
                menu.addAction("Réactiver (Arbo/GC)",
                    lambda: self._changer_type(parcelle_id, "arbo"))
                menu.addAction("Réactiver (Maraîchage)",
                    lambda: self._changer_type(parcelle_id, "maraichage"))
            elif type_key == "engrais_vert":
                menu.addAction("Réactiver (Arbo/GC)",
                    lambda: self._changer_type(parcelle_id, "arbo"))
                menu.addAction("Réactiver (Maraîchage)",
                    lambda: self._changer_type(parcelle_id, "maraichage"))
            menu.addSeparator()
            menu.addAction("Archiver",
                lambda: self._set_actif(parcelle_id, False))
        else:
            menu.addAction("Réactiver",
                lambda: self._set_actif(parcelle_id, True))

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _changer_type(self, parcelle_id: int, nouveau_type: str):
        try:
            conn = get_connection()
            cur = conn.cursor()
            if nouveau_type == "jachere":
                cur.execute("""
                    UPDATE parcelles SET type_unite='jachere',
                    culture=NULL, culture_reelle=NULL, variete=NULL
                    WHERE id=?
                """, (parcelle_id,))
            elif nouveau_type == "engrais_vert":
                cur.execute(
                    "UPDATE parcelles SET type_unite='engrais_vert', "
                    "culture=NULL, culture_reelle=NULL WHERE id=?",
                    (parcelle_id,))
            else:
                cur.execute(
                    "UPDATE parcelles SET type_unite=? WHERE id=?",
                    (nouveau_type, parcelle_id))
            conn.commit()
            cur.close()
            self._charger()
            self.parcelle_modifiee.emit()
        except Exception:
            traceback.print_exc()

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

    def _menu_systeme(self, pos):
        row = self.table_sys.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_sys.item(row, 0)
        systeme_id = item.data(Qt.UserRole)
        parcelle_id = self.btn_add_sys.property("parcelle_id")
        menu = QMenu(self)
        menu.addAction("Modifier",
            lambda: self._modifier_systeme(systeme_id, parcelle_id))
        menu.addAction("Supprimer",
            lambda: self._supprimer_systeme(systeme_id, parcelle_id))
        menu.exec(self.table_sys.viewport().mapToGlobal(pos))

    def _modifier_systeme(self, systeme_id: int, parcelle_id: int):
        dlg = DialogSysteme(systeme_id=systeme_id, parcelle_id=parcelle_id,
                            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_systemes(parcelle_id)

    def _supprimer_systeme(self, systeme_id: int, parcelle_id: int):
        rep = QMessageBox.question(self, "Confirmer", "Supprimer ce système ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE irrigation_systemes SET actif=0 WHERE id=?",
                            (systeme_id,))
                conn.commit()
                cur.close()
                self._charger_systemes(parcelle_id)
            except Exception:
                traceback.print_exc()

    def recharger_parcelles(self):
        self._charger()


# ──────────────────────────────────────────────
# Dialog Parcelle
# ──────────────────────────────────────────────
class DialogParcelle(QDialog):
    def __init__(self, parcelle_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self._lignes_ev = []  # lignes variétés engrais vert
        self.setWindowTitle(
            "Nouvelle parcelle" if not parcelle_id else "Modifier la parcelle")
        self.setMinimumWidth(540)
        self.setMinimumHeight(580)
        self._build_ui()
        if parcelle_id:
            self._charger(parcelle_id)

    def _build_ui(self):
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setContentsMargins(8, 8, 8, 8)

        # ── Base ──────────────────────────────
        self.inp_nom = QLineEdit()
        form.addRow("Nom *", self.inp_nom)

        self.combo_type = QComboBox()
        for key, label in TYPES_PARCELLE.items():
            self.combo_type.addItem(label, key)
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type *", self.combo_type)

        self.inp_sol = QLineEdit()
        self.inp_sol.setPlaceholderText("Ex: limoneux, argileux...")
        form.addRow("Type de sol", self.inp_sol)

        # ── Blocs conditionnels ───────────────

        # -- Arbo / GC -----------------------
        self.w_arbo = QWidget()
        arbo_lay = QFormLayout(self.w_arbo)
        arbo_lay.setContentsMargins(0, 0, 0, 0)
        arbo_lay.setSpacing(6)

        self.inp_culture_reelle = QLineEdit()
        self.inp_culture_reelle.setPlaceholderText("Ex: Golden, Carottes...")
        arbo_lay.addRow("Culture", self.inp_culture_reelle)

        self.inp_variete = QLineEdit()
        self.inp_variete.setPlaceholderText("Optionnel")
        arbo_lay.addRow("Variété", self.inp_variete)

        self.inp_surface_ha = QDoubleSpinBox()
        self.inp_surface_ha.setRange(0, 9999)
        self.inp_surface_ha.setDecimals(4)
        self.inp_surface_ha.setSuffix(" ha")
        arbo_lay.addRow("Surface", self.inp_surface_ha)

        self.inp_densite_ha = QDoubleSpinBox()
        self.inp_densite_ha.setRange(0, 99999)
        self.inp_densite_ha.setDecimals(0)
        self.inp_densite_ha.setSuffix(" unités/ha")
        arbo_lay.addRow("Densité", self.inp_densite_ha)

        self.inp_rendement_ha = QDoubleSpinBox()
        self.inp_rendement_ha.setRange(0, 9999)
        self.inp_rendement_ha.setDecimals(2)
        self.inp_rendement_ha.setSuffix(" t/ha")
        arbo_lay.addRow("Rendement", self.inp_rendement_ha)
        form.addRow(self.w_arbo)

        # -- Maraîchage ----------------------
        self.w_maraich = QWidget()
        mar_lay = QFormLayout(self.w_maraich)
        mar_lay.setContentsMargins(0, 0, 0, 0)
        mar_lay.setSpacing(6)

        self.inp_culture_mar = QLineEdit()
        self.inp_culture_mar.setPlaceholderText("Ex: Tomate cerise...")
        mar_lay.addRow("Culture", self.inp_culture_mar)

        dim_w = QWidget()
        dim_lay = QHBoxLayout(dim_w)
        dim_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_longueur = QDoubleSpinBox()
        self.inp_longueur.setRange(0, 9999)
        self.inp_longueur.setSuffix(" m")
        self.inp_longueur.valueChanged.connect(self._calc_surface)
        self.inp_largeur = QDoubleSpinBox()
        self.inp_largeur.setRange(0, 999)
        self.inp_largeur.setSuffix(" m")
        self.inp_largeur.valueChanged.connect(self._calc_surface)
        self.lbl_surf_calc = QLabel("= — m²")
        dim_lay.addWidget(QLabel("L:"))
        dim_lay.addWidget(self.inp_longueur)
        dim_lay.addWidget(QLabel("l:"))
        dim_lay.addWidget(self.inp_largeur)
        dim_lay.addWidget(self.lbl_surf_calc)
        mar_lay.addRow("Dimensions *", dim_w)

        self.inp_nb_planches = QSpinBox()
        self.inp_nb_planches.setRange(1, 9999)
        self.inp_nb_planches.setValue(1)
        self.inp_nb_planches.setSuffix(" planche(s)")
        self.inp_nb_planches.valueChanged.connect(self._calc_surface)
        mar_lay.addRow("Nb planches", self.inp_nb_planches)

        self.inp_nb_rangs = QSpinBox()
        self.inp_nb_rangs.setRange(0, 999)
        self.inp_nb_rangs.setSuffix(" rang(s)")
        mar_lay.addRow("Rangs/planche", self.inp_nb_rangs)

        self.inp_dist_plants = QDoubleSpinBox()
        self.inp_dist_plants.setRange(0, 999)
        self.inp_dist_plants.setSuffix(" cm")
        self.inp_dist_plants.setDecimals(1)
        mar_lay.addRow("Distance plants", self.inp_dist_plants)

        self.inp_rendement_m2 = QDoubleSpinBox()
        self.inp_rendement_m2.setRange(0, 9999)
        self.inp_rendement_m2.setDecimals(2)
        self.inp_rendement_m2.setSuffix(" kg/m²")
        mar_lay.addRow("Rendement", self.inp_rendement_m2)
        form.addRow(self.w_maraich)

        # -- Ruche ---------------------------
        self.w_ruche = QWidget()
        ruc_lay = QFormLayout(self.w_ruche)
        ruc_lay.setContentsMargins(0, 0, 0, 0)
        ruc_lay.setSpacing(6)

        cp_vil = QWidget()
        cp_lay = QHBoxLayout(cp_vil)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_cp_parc = QLineEdit()
        self.inp_cp_parc.setFixedWidth(60)
        self.inp_cp_parc.setMaxLength(5)
        self.inp_cp_parc.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"^\d{0,5}$")))
        self.inp_commune = QLineEdit()
        self.inp_commune.setPlaceholderText("Commune")
        cp_lay.addWidget(self.inp_cp_parc)
        cp_lay.addWidget(self.inp_commune)
        ruc_lay.addRow("CP / Commune", cp_vil)

        self.inp_surface_ruche = QDoubleSpinBox()
        self.inp_surface_ruche.setRange(0, 9999)
        self.inp_surface_ruche.setDecimals(4)
        self.inp_surface_ruche.setSuffix(" ha")
        ruc_lay.addRow("Surface (optionnel)", self.inp_surface_ruche)
        form.addRow(self.w_ruche)

        # -- Jachère -------------------------
        self.w_jachere = QWidget()
        jac_lay = QFormLayout(self.w_jachere)
        jac_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_surface_jac = QDoubleSpinBox()
        self.inp_surface_jac.setRange(0, 9999)
        self.inp_surface_jac.setDecimals(4)
        self.inp_surface_jac.setSuffix(" ha")
        jac_lay.addRow("Surface", self.inp_surface_jac)
        form.addRow(self.w_jachere)

        # -- Engrais vert --------------------
        self.w_ev = QWidget()
        ev_lay = QVBoxLayout(self.w_ev)
        ev_lay.setContentsMargins(0, 0, 0, 0)
        ev_lay.setSpacing(6)

        ev_form = QFormLayout()
        self.inp_surface_ev = QDoubleSpinBox()
        self.inp_surface_ev.setRange(0, 9999)
        self.inp_surface_ev.setDecimals(4)
        self.inp_surface_ev.setSuffix(" ha")
        ev_form.addRow("Surface", self.inp_surface_ev)

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

        # ── PPP ───────────────────────────────
        sep_ppp = QLabel("── Catégories PPP ──")
        sep_ppp.setStyleSheet("color:gray; font-size:11px;")
        self.w_sep_ppp = sep_ppp

        # Conteneur pour masquer label + widget ensemble
        self.w_ppp_container = QWidget()
        ppp_lay = QFormLayout(self.w_ppp_container)
        ppp_lay.setContentsMargins(0, 0, 0, 0)
        ppp_lay.setSpacing(6)
        self.cat_ppp_widget = CategoriesPPPWidget()
        self.w_cat_ppp = self.cat_ppp_widget
        ppp_lay.addRow("Cultures e-phy", self.cat_ppp_widget)
        form.addRow(self.w_sep_ppp)
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
        self.inp_notes.setMaximumHeight(70)
        form.addRow("Notes", self.inp_notes)

        scroll.setWidget(w)
        root.addWidget(scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._on_type_changed()

    def _on_type_changed(self):
        type_key = self.combo_type.currentData()
        self.w_arbo.setVisible(type_key == "arbo")
        self.w_maraich.setVisible(type_key == "maraichage")
        self.w_ruche.setVisible(type_key == "ruche")
        self.w_jachere.setVisible(type_key == "jachere")
        self.w_ev.setVisible(type_key == "engrais_vert")
        # PPP pas pertinent pour ruche/jachere
        show_ppp = type_key not in ("ruche", "jachere")
        self.w_sep_ppp.setVisible(show_ppp)
        self.w_ppp_container.setVisible(show_ppp)

    def _calc_surface(self):
        l  = self.inp_longueur.value()
        lw = self.inp_largeur.value()
        nb = self.inp_nb_planches.value()
        surf_une = l * lw
        surf_tot = surf_une * nb
        self.lbl_surf_calc.setText(
            f"= {surf_une:.0f} m² × {nb} = {surf_tot:.0f} m² total")

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

    def _charger(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id=?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(p.get("nom", ""))
            type_key = p.get("type_unite", "arbo")
            idx = self.combo_type.findData(type_key)
            if idx >= 0:
                self.combo_type.setCurrentIndex(idx)
            self.inp_sol.setText(p.get("type_sol") or "")
            self.inp_notes.setPlainText(p.get("notes") or "")

            if type_key == "arbo":
                self.inp_culture_reelle.setText(p.get("culture_reelle") or "")
                self.inp_variete.setText(p.get("variete") or "")
                self.inp_surface_ha.setValue(p.get("surface_ha") or 0)
                self.inp_densite_ha.setValue(p.get("densite_ha") or 0)
                self.inp_rendement_ha.setValue(p.get("rendement_ha") or 0)
            elif type_key == "maraichage":
                self.inp_culture_mar.setText(p.get("culture_reelle") or "")
                self.inp_longueur.setValue(p.get("longueur_m") or 0)
                self.inp_largeur.setValue(p.get("largeur_m") or 0)
                self.inp_nb_planches.setValue(p.get("nb_planches") or 1)
                self.inp_nb_rangs.setValue(p.get("nb_rangs") or 0)
                self.inp_dist_plants.setValue(p.get("distance_plants_cm") or 0)
                self.inp_rendement_m2.setValue(p.get("rendement_m2") or 0)
            elif type_key == "ruche":
                self.inp_commune.setText(p.get("commune") or "")
                self.inp_cp_parc.setText(p.get("code_postal_parc") or "")
                self.inp_surface_ruche.setValue(p.get("surface_ha") or 0)
            elif type_key == "jachere":
                self.inp_surface_jac.setValue(p.get("surface_ha") or 0)
            elif type_key == "engrais_vert":
                self.inp_surface_ev.setValue(p.get("surface_ha") or 0)
                self.inp_melange_nom.setText(p.get("melange_nom") or "")
                varietes = get_engrais_vert_varietes(parcelle_id)
                for v in varietes:
                    self._ajouter_variete_ev(v["variete"], v.get("taux_pct"))

            cats = get_categories_ppp_parcelle(parcelle_id)
            self.cat_ppp_widget.set_selections(cats)
            self._on_type_changed()
        except Exception:
            traceback.print_exc()

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant", "Le nom est obligatoire.")
            return

        type_key = self.combo_type.currentData()
        sol      = self.inp_sol.text().strip() or None
        notes    = self.inp_notes.toPlainText().strip() or None

        # Valeurs selon type
        culture = culture_reelle = variete = None
        surface_ha = longueur = largeur = None
        nb_planches = nb_rangs = None
        dist_plants = rendement_m2 = None
        densite_ha = rendement_ha = None
        melange_nom = commune = cp_parc = None

        if type_key == "arbo":
            culture_reelle = self.inp_culture_reelle.text().strip() or None
            variete        = self.inp_variete.text().strip() or None
            surface_ha     = self.inp_surface_ha.value() or None
            densite_ha     = self.inp_densite_ha.value() or None
            rendement_ha   = self.inp_rendement_ha.value() or None
        elif type_key == "maraichage":
            culture_reelle = self.inp_culture_mar.text().strip() or None
            longueur       = self.inp_longueur.value() or None
            largeur        = self.inp_largeur.value() or None
            nb_planches    = self.inp_nb_planches.value()
            nb_rangs       = self.inp_nb_rangs.value() or None
            dist_plants    = self.inp_dist_plants.value() or None
            rendement_m2   = self.inp_rendement_m2.value() or None
        elif type_key == "ruche":
            commune    = self.inp_commune.text().strip() or None
            cp_parc    = self.inp_cp_parc.text().strip() or None
            surface_ha = self.inp_surface_ruche.value() or None
        elif type_key == "jachere":
            surface_ha = self.inp_surface_jac.value() or None
        elif type_key == "engrais_vert":
            surface_ha  = self.inp_surface_ev.value() or None
            melange_nom = self.inp_melange_nom.text().strip() or None

        try:
            conn = get_connection()
            cur  = conn.cursor()
            if self.parcelle_id:
                cur.execute("""
                    UPDATE parcelles SET
                        nom=?, type_unite=?, culture=?, culture_reelle=?,
                        variete=?, surface_ha=?, longueur_m=?, largeur_m=?,
                        nb_planches=?, nb_rangs=?, distance_plants_cm=?,
                        rendement_m2=?, densite_ha=?, rendement_ha=?,
                        type_sol=?, melange_nom=?, commune=?,
                        code_postal_parc=?, notes=?
                    WHERE id=?
                """, (nom, type_key, culture, culture_reelle,
                      variete, surface_ha, longueur, largeur,
                      nb_planches, nb_rangs, dist_plants,
                      rendement_m2, densite_ha, rendement_ha,
                      sol, melange_nom, commune, cp_parc,
                      notes, self.parcelle_id))
                pid = self.parcelle_id
            else:
                cur.execute("""
                    INSERT INTO parcelles (
                        nom, type_unite, culture, culture_reelle,
                        variete, surface_ha, longueur_m, largeur_m,
                        nb_planches, nb_rangs, distance_plants_cm,
                        rendement_m2, densite_ha, rendement_ha,
                        type_sol, melange_nom, commune,
                        code_postal_parc, notes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (nom, type_key, culture, culture_reelle,
                      variete, surface_ha, longueur, largeur,
                      nb_planches, nb_rangs, dist_plants,
                      rendement_m2, densite_ha, rendement_ha,
                      sol, melange_nom, commune, cp_parc, notes))
                pid = cur.lastrowid

            conn.commit()
            cur.close()

            # Catégories PPP
            if type_key not in ("ruche", "jachere"):
                cats = self.cat_ppp_widget.get_selections()
                set_categories_ppp_parcelle(pid, cats)

            # Variétés engrais vert
            if type_key == "engrais_vert":
                varietes_ev = [l.get_data() for l in self._lignes_ev]
                varietes_ev = [v for v in varietes_ev if v]
                set_engrais_vert_varietes(pid, varietes_ev)

            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))


# ──────────────────────────────────────────────
# Dialog Système d'irrigation
# ──────────────────────────────────────────────
class DialogSysteme(QDialog):
    TYPES = ["goutteur", "asperseur", "micro-asperseur", "pivot", "rampe", "autre"]

    def __init__(self, parcelle_id: int, systeme_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self.systeme_id  = systeme_id
        self.setWindowTitle("Système d'irrigation")
        self.setMinimumWidth(380)
        self._build_ui()
        if systeme_id:
            self._charger(systeme_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.combo_type = QComboBox()
        for t in self.TYPES:
            self.combo_type.addItem(t.capitalize(), t)
        form.addRow("Type d'émetteur *", self.combo_type)

        self.inp_nb = QSpinBox()
        self.inp_nb.setRange(1, 99999)
        self.inp_nb.setSuffix(" émetteurs")
        self.inp_nb.valueChanged.connect(self._calc_vol)
        form.addRow("Nombre *", self.inp_nb)

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
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _calc_vol(self):
        vol = self.inp_nb.value() * self.inp_debit.value()
        self.lbl_vol.setText(f"Volume/h : {vol:.0f} L/h total")

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
            self._calc_vol()
        except Exception:
            traceback.print_exc()

    def _valider(self):
        type_emetteur = self.combo_type.currentData()
        nb    = self.inp_nb.value()
        debit = self.inp_debit.value()
        desc  = self.inp_desc.text().strip() or None
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.systeme_id:
                cur.execute("""
                    UPDATE irrigation_systemes
                    SET type_emetteur=?, nb_emetteurs=?, debit_lh=?, description=?
                    WHERE id=?
                """, (type_emetteur, nb, debit, desc, self.systeme_id))
            else:
                cur.execute("""
                    INSERT INTO irrigation_systemes
                    (parcelle_id, type_emetteur, nb_emetteurs, debit_lh, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.parcelle_id, type_emetteur, nb, debit, desc))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))