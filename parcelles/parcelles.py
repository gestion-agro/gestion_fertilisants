# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
import traceback


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

        # Titre + bouton ajout
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

        # Filtre actif/archivé
        filtre = QHBoxLayout()
        self.chk_archivees = QCheckBox("Afficher les parcelles archivées")
        self.chk_archivees.stateChanged.connect(self._charger)
        filtre.addWidget(self.chk_archivees)
        filtre.addStretch()
        root.addLayout(filtre)

        # Splitter : liste gauche / détail droite
        splitter = QSplitter(Qt.Horizontal)

        # Table parcelles
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
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._on_selection)
        splitter.addWidget(self.table)

        # Détail + systèmes d'irrigation
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.setSpacing(8)

        # Fiche parcelle
        self.fiche_group = QGroupBox("Fiche parcelle")
        fiche_layout = QFormLayout(self.fiche_group)
        fiche_layout.setSpacing(6)
        fiche_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_nom     = QLabel("—")
        self.lbl_type    = QLabel("—")
        self.lbl_culture = QLabel("—")
        self.lbl_surface = QLabel("—")
        self.lbl_sol     = QLabel("—")
        self.lbl_notes   = QLabel("—")
        self.lbl_notes.setWordWrap(True)

        for lbl in (self.lbl_nom, self.lbl_type, self.lbl_culture,
                    self.lbl_surface, self.lbl_sol, self.lbl_notes):
            lbl.setStyleSheet("font-size: 13px;")

        fiche_layout.addRow("Nom :",     self.lbl_nom)
        fiche_layout.addRow("Type :",    self.lbl_type)
        fiche_layout.addRow("Culture :", self.lbl_culture)
        fiche_layout.addRow("Surface :", self.lbl_surface)
        fiche_layout.addRow("Sol :",     self.lbl_sol)
        fiche_layout.addRow("Notes :",   self.lbl_notes)
        detail_layout.addWidget(self.fiche_group)

        # Systèmes d'irrigation de la parcelle
        sys_group = QGroupBox("Systèmes d'irrigation")
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setContentsMargins(6, 6, 6, 6)

        sys_btn = QHBoxLayout()
        self.btn_add_sys = QPushButton("+ Ajouter un système")
        self.btn_add_sys.setEnabled(False)
        self.btn_add_sys.clicked.connect(self._ajouter_systeme)
        sys_btn.addWidget(self.btn_add_sys)
        sys_btn.addStretch()
        sys_layout.addLayout(sys_btn)

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
        self.table_sys.setMaximumHeight(180)
        sys_layout.addWidget(self.table_sys)
        detail_layout.addWidget(sys_group)
        detail_layout.addStretch()

        splitter.addWidget(detail)
        splitter.setSizes([420, 320])
        root.addWidget(splitter, 1)

    # ──────────────────────────────────────────
    # Chargement
    # ──────────────────────────────────────────
    def _charger(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            show_archived = self.chk_archivees.isChecked()
            if show_archived:
                cur.execute("SELECT * FROM parcelles ORDER BY nom")
            else:
                cur.execute("SELECT * FROM parcelles WHERE actif = 1 ORDER BY nom")
            rows = cur.fetchall()
            cur.close()

            self.table.setRowCount(0)
            for row in rows:
                p = dict(row)
                r = self.table.rowCount()
                self.table.insertRow(r)
                self.table.setItem(r, 0, QTableWidgetItem(p.get("nom", "")))
                type_lbl = "Planche" if p.get("type_unite") == "planche" else "Parcelle"
                self.table.setItem(r, 1, QTableWidgetItem(type_lbl))
                self.table.setItem(r, 2, QTableWidgetItem(p.get("culture") or "—"))

                if p.get("type_unite") == "planche" and p.get("longueur_m") and p.get("largeur_m"):
                    surface = p["longueur_m"] * p["largeur_m"]
                    surface_txt = f"{surface:.0f} m²"
                elif p.get("surface_ha"):
                    surface_txt = f"{p['surface_ha']} ha"
                else:
                    surface_txt = "—"
                self.table.setItem(r, 3, QTableWidgetItem(surface_txt))
                self.table.setItem(r, 4, QTableWidgetItem(p.get("type_sol") or "—"))
                etat = "Active" if p.get("actif") else "Archivée"
                self.table.setItem(r, 5, QTableWidgetItem(etat))
                self.table.item(r, 0).setData(Qt.UserRole, p["id"])

                if not p.get("actif"):
                    for col in range(6):
                        item = self.table.item(r, col)
                        if item:
                            item.setForeground(QColor("gray"))
        except Exception as e:
            traceback.print_exc()

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
            cur.execute("SELECT * FROM parcelles WHERE id = ?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            self.fiche_group.setTitle(f"Fiche — {p.get('nom', '')}")
            self.lbl_nom.setText(p.get("nom", "—"))
            type_lbl = "Planche (maraîchage)" if p.get("type_unite") == "planche" else "Parcelle"
            self.lbl_type.setText(type_lbl)
            self.lbl_culture.setText(p.get("culture") or "—")

            if p.get("type_unite") == "planche" and p.get("longueur_m") and p.get("largeur_m"):
                surface_txt = (f"{p['longueur_m']} m × {p['largeur_m']} m "
                               f"= {p['longueur_m'] * p['largeur_m']:.0f} m²")
            elif p.get("surface_ha"):
                surface_txt = f"{p['surface_ha']} ha"
            else:
                surface_txt = "—"
            self.lbl_surface.setText(surface_txt)
            self.lbl_sol.setText(p.get("type_sol") or "—")
            self.lbl_notes.setText(p.get("notes") or "—")
        except Exception as e:
            traceback.print_exc()

    def _charger_systemes(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM irrigation_systemes
                WHERE parcelle_id = ? AND actif = 1
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
        except Exception as e:
            traceback.print_exc()

    # ──────────────────────────────────────────
    # Dialogs
    # ──────────────────────────────────────────
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
        menu = QMenu(self)
        menu.addAction("Modifier", lambda: self._ouvrir_dialog(parcelle_id))
        etat_item = self.table.item(row, 5)
        if etat_item and etat_item.text() == "Active":
            menu.addAction("Archiver", lambda: self._archiver(parcelle_id, False))
        else:
            menu.addAction("Réactiver", lambda: self._archiver(parcelle_id, True))
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _menu_systeme(self, pos):
        row = self.table_sys.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_sys.item(row, 0)
        systeme_id = item.data(Qt.UserRole)
        parcelle_id = self.btn_add_sys.property("parcelle_id")
        menu = QMenu(self)
        menu.addAction("Modifier", lambda: self._modifier_systeme(systeme_id, parcelle_id))
        menu.addAction("Supprimer", lambda: self._supprimer_systeme(systeme_id, parcelle_id))
        menu.exec(self.table_sys.viewport().mapToGlobal(pos))

    def _archiver(self, parcelle_id: int, actif: bool):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE parcelles SET actif = ? WHERE id = ?",
                        (1 if actif else 0, parcelle_id))
            conn.commit()
            cur.close()
            self._charger()
        except Exception as e:
            traceback.print_exc()

    def _modifier_systeme(self, systeme_id: int, parcelle_id: int):
        dlg = DialogSysteme(systeme_id=systeme_id, parcelle_id=parcelle_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_systemes(parcelle_id)

    def _supprimer_systeme(self, systeme_id: int, parcelle_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer ce système d'irrigation ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("UPDATE irrigation_systemes SET actif = 0 WHERE id = ?",
                            (systeme_id,))
                conn.commit()
                cur.close()
                self._charger_systemes(parcelle_id)
            except Exception as e:
                traceback.print_exc()


# ──────────────────────────────────────────────
# Dialog Parcelle
# ──────────────────────────────────────────────
class DialogParcelle(QDialog):
    def __init__(self, parcelle_id=None, parent=None):
        super().__init__(parent)
        self.parcelle_id = parcelle_id
        self.setWindowTitle("Parcelle" if not parcelle_id else "Modifier la parcelle")
        self.setMinimumWidth(420)
        self._build_ui()
        if parcelle_id:
            self._charger(parcelle_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_nom = QLineEdit()
        form.addRow("Nom *", self.inp_nom)

        self.combo_type = QComboBox()
        self.combo_type.addItem("Parcelle (arbo / grandes cultures)", "parcelle")
        self.combo_type.addItem("Planche / rang (maraîchage)", "planche")
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type *", self.combo_type)

        self.inp_culture = QLineEdit()
        self.inp_culture.setPlaceholderText("Ex: Pommes, Tomates, Carottes...")
        form.addRow("Culture", self.inp_culture)

        # Surface parcelle
        self.widget_surface_ha = QWidget()
        lay_ha = QHBoxLayout(self.widget_surface_ha)
        lay_ha.setContentsMargins(0, 0, 0, 0)
        self.inp_surface_ha = QDoubleSpinBox()
        self.inp_surface_ha.setRange(0, 9999)
        self.inp_surface_ha.setDecimals(4)
        self.inp_surface_ha.setSuffix(" ha")
        lay_ha.addWidget(self.inp_surface_ha)
        form.addRow("Surface", self.widget_surface_ha)

        # Dimensions planche
        self.widget_planche = QWidget()
        lay_pl = QHBoxLayout(self.widget_planche)
        lay_pl.setContentsMargins(0, 0, 0, 0)
        self.inp_longueur = QDoubleSpinBox()
        self.inp_longueur.setRange(0, 9999)
        self.inp_longueur.setSuffix(" m")
        self.inp_longueur.valueChanged.connect(self._calc_surface)
        self.inp_largeur = QDoubleSpinBox()
        self.inp_largeur.setRange(0, 999)
        self.inp_largeur.setSuffix(" m")
        self.inp_largeur.valueChanged.connect(self._calc_surface)
        self.lbl_surface_calc = QLabel("= — m²")
        lay_pl.addWidget(QLabel("L :"))
        lay_pl.addWidget(self.inp_longueur)
        lay_pl.addWidget(QLabel("l :"))
        lay_pl.addWidget(self.inp_largeur)
        lay_pl.addWidget(self.lbl_surface_calc)
        self.widget_planche.setVisible(False)
        form.addRow("Dimensions", self.widget_planche)

        self.inp_sol = QLineEdit()
        self.inp_sol.setPlaceholderText("Ex: limoneux, argileux, sableux...")
        form.addRow("Type de sol", self.inp_sol)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(80)
        form.addRow("Notes", self.inp_notes)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_type_changed(self):
        is_planche = self.combo_type.currentData() == "planche"
        self.widget_surface_ha.setVisible(not is_planche)
        self.widget_planche.setVisible(is_planche)

    def _calc_surface(self):
        l = self.inp_longueur.value()
        w = self.inp_largeur.value()
        self.lbl_surface_calc.setText(f"= {l * w:.0f} m²")

    def _charger(self, parcelle_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM parcelles WHERE id = ?", (parcelle_id,))
            p = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(p.get("nom", ""))
            idx = self.combo_type.findData(p.get("type_unite", "parcelle"))
            self.combo_type.setCurrentIndex(idx)
            self.inp_culture.setText(p.get("culture") or "")
            self.inp_surface_ha.setValue(p.get("surface_ha") or 0)
            self.inp_longueur.setValue(p.get("longueur_m") or 0)
            self.inp_largeur.setValue(p.get("largeur_m") or 0)
            self.inp_sol.setText(p.get("type_sol") or "")
            self.inp_notes.setPlainText(p.get("notes") or "")
            self._on_type_changed()
        except Exception as e:
            traceback.print_exc()

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant", "Le nom est obligatoire.")
            return

        type_unite = self.combo_type.currentData()
        culture    = self.inp_culture.text().strip() or None
        sol        = self.inp_sol.text().strip() or None
        notes      = self.inp_notes.toPlainText().strip() or None

        if type_unite == "parcelle":
            surface_ha = self.inp_surface_ha.value() or None
            longueur = largeur = None
        else:
            surface_ha = None
            longueur = self.inp_longueur.value() or None
            largeur  = self.inp_largeur.value() or None

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.parcelle_id:
                cur.execute("""
                    UPDATE parcelles SET nom=?, type_unite=?, culture=?,
                    surface_ha=?, longueur_m=?, largeur_m=?,
                    type_sol=?, notes=? WHERE id=?
                """, (nom, type_unite, culture, surface_ha,
                      longueur, largeur, sol, notes, self.parcelle_id))
            else:
                cur.execute("""
                    INSERT INTO parcelles
                    (nom, type_unite, culture, surface_ha,
                     longueur_m, largeur_m, type_sol, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (nom, type_unite, culture, surface_ha,
                      longueur, largeur, sol, notes))
            conn.commit()
            cur.close()
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
        self.lbl_vol.setStyleSheet("color: palette(mid); font-size: 12px;")
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
            cur.execute("SELECT * FROM irrigation_systemes WHERE id = ?", (systeme_id,))
            s = dict(cur.fetchone())
            cur.close()
            idx = self.combo_type.findData(s.get("type_emetteur"))
            self.combo_type.setCurrentIndex(idx)
            self.inp_nb.setValue(s.get("nb_emetteurs", 1))
            self.inp_debit.setValue(s.get("debit_lh", 1.0))
            self.inp_desc.setText(s.get("description") or "")
            self._calc_vol()
        except Exception as e:
            traceback.print_exc()

    def _valider(self):
        type_emetteur = self.combo_type.currentData()
        nb     = self.inp_nb.value()
        debit  = self.inp_debit.value()
        desc   = self.inp_desc.text().strip() or None

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