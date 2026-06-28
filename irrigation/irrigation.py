# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, peut_action, get_cultures_systeme
import traceback
from datetime import datetime


class IrrigationPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_supprimer = peut_action(current_user, "irrigation", "suppression")
        self._peut_ecrire    = peut_action(current_user, "irrigation", "ecriture")
        self._build_ui()
        self.btn_enregistrer.setVisible(self._peut_ecrire)
        self._charger_parcelles()
        self._charger_historique()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Gestion de l'irrigation")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        vsplit = QSplitter(Qt.Vertical)

        # ── Saisie ────────────────────────────
        saisie_group = QGroupBox("Nouvelle session d'irrigation")
        saisie_layout = QGridLayout(saisie_group)
        saisie_layout.setSpacing(10)
        saisie_layout.setContentsMargins(12, 12, 12, 12)

        saisie_layout.addWidget(QLabel("Parcelle *"), 0, 0)
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.setMinimumWidth(200)
        self.combo_parcelle.currentIndexChanged.connect(self._on_parcelle_changed)
        saisie_layout.addWidget(self.combo_parcelle, 0, 1)

        saisie_layout.addWidget(QLabel("Système *"), 0, 2)
        self.combo_systeme = QComboBox()
        self.combo_systeme.setMinimumWidth(220)
        self.combo_systeme.currentIndexChanged.connect(self._on_systeme_changed)
        saisie_layout.addWidget(self.combo_systeme, 0, 3)

        # Info cultures couvertes par le système sélectionné
        self.lbl_cultures_sys = QLabel("")
        self.lbl_cultures_sys.setStyleSheet(
            "color:#1D4ED8; font-size:11px; font-style:italic;")
        self.lbl_cultures_sys.setWordWrap(True)
        saisie_layout.addWidget(self.lbl_cultures_sys, 1, 0, 1, 4)

        saisie_layout.addWidget(QLabel("Date *"), 2, 0)
        self.inp_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.inp_date.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.inp_date.setCalendarPopup(True)
        saisie_layout.addWidget(self.inp_date, 2, 1)

        saisie_layout.addWidget(QLabel("Durée *"), 2, 2)
        dur_widget = QWidget()
        dur_layout = QHBoxLayout(dur_widget)
        dur_layout.setContentsMargins(0, 0, 0, 0)
        self.inp_heures = QSpinBox()
        self.inp_heures.setRange(0, 999)
        self.inp_heures.setSuffix(" h")
        self.inp_heures.valueChanged.connect(self._calc_volume)
        self.inp_minutes = QSpinBox()
        self.inp_minutes.setRange(0, 59)
        self.inp_minutes.setSuffix(" min")
        self.inp_minutes.valueChanged.connect(self._calc_volume)
        dur_layout.addWidget(self.inp_heures)
        dur_layout.addWidget(self.inp_minutes)
        saisie_layout.addWidget(dur_widget, 2, 3)

        saisie_layout.addWidget(QLabel("Volume calculé"), 3, 0)
        self.lbl_volume = QLabel("—")
        self.lbl_volume.setStyleSheet("font-size: 14px; font-weight: bold;")
        saisie_layout.addWidget(self.lbl_volume, 3, 1)

        self.lbl_sys_info = QLabel("")
        self.lbl_sys_info.setStyleSheet("color: palette(mid); font-size: 12px;")
        saisie_layout.addWidget(self.lbl_sys_info, 3, 2, 1, 2)

        saisie_layout.addWidget(QLabel("Notes"), 4, 0)
        self.inp_notes = QLineEdit()
        self.inp_notes.setPlaceholderText("Observations, problèmes...")
        saisie_layout.addWidget(self.inp_notes, 4, 1, 1, 3)

        self.btn_enregistrer = QPushButton("Enregistrer la session")
        self.btn_enregistrer.setFixedHeight(38)
        self.btn_enregistrer.clicked.connect(self._enregistrer)
        saisie_layout.addWidget(self.btn_enregistrer, 5, 0, 1, 4)

        vsplit.addWidget(saisie_group)

        # ── Historique ────────────────────────
        histo_group = QGroupBox("Historique des sessions")
        histo_layout = QVBoxLayout(histo_group)
        histo_layout.setContentsMargins(6, 6, 6, 6)

        filtre_layout = QHBoxLayout()
        self.combo_filtre_parcelle = QComboBox()
        self.combo_filtre_parcelle.addItem("Toutes les parcelles", None)
        self.combo_filtre_parcelle.currentIndexChanged.connect(self._charger_historique)
        filtre_layout.addWidget(QLabel("Parcelle :"))
        filtre_layout.addWidget(self.combo_filtre_parcelle)

        self.inp_date_debut = QDateEdit(QDate.currentDate().addMonths(-1))
        self.inp_date_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_debut.setCalendarPopup(True)
        self.inp_date_debut.dateChanged.connect(self._charger_historique)
        filtre_layout.addWidget(QLabel("Du :"))
        filtre_layout.addWidget(self.inp_date_debut)

        self.inp_date_fin = QDateEdit(QDate.currentDate())
        self.inp_date_fin.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_fin.setCalendarPopup(True)
        self.inp_date_fin.dateChanged.connect(self._charger_historique)
        filtre_layout.addWidget(QLabel("Au :"))
        filtre_layout.addWidget(self.inp_date_fin)
        filtre_layout.addStretch()

        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("font-weight: bold;")
        filtre_layout.addWidget(self.lbl_total)
        histo_layout.addLayout(filtre_layout)

        self.table_histo = QTableWidget(0, 7)
        self.table_histo.setHorizontalHeaderLabels(
            ["Date", "Parcelle", "Système", "Cultures", "Durée",
             "Volume (L)", "Opérateur"])
        self.table_histo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_histo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_histo.setAlternatingRowColors(True)
        hh = self.table_histo.horizontalHeader()
        for i in range(6):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_histo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_histo.customContextMenuRequested.connect(self._menu_histo)
        histo_layout.addWidget(self.table_histo)
        vsplit.addWidget(histo_group)

        vsplit.setSizes([300, 320])
        root.addWidget(vsplit, 1)

    # ──────────────────────────────────────────
    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif = 1 ORDER BY nom")
            rows = cur.fetchall()
            cur.close()

            self.combo_parcelle.clear()
            self.combo_parcelle.addItem("— Sélectionnez —", None)
            self.combo_filtre_parcelle.clear()
            self.combo_filtre_parcelle.addItem("Toutes les parcelles", None)

            for row in rows:
                self.combo_parcelle.addItem(row[1], row[0])
                self.combo_filtre_parcelle.addItem(row[1], row[0])
        except Exception:
            traceback.print_exc()

    def _on_parcelle_changed(self):
        parcelle_id = self.combo_parcelle.currentData()
        self.combo_systeme.clear()
        self.combo_systeme.addItem("— Sélectionnez un système —", None)
        if not parcelle_id:
            self.lbl_cultures_sys.setText("")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, type_emetteur, nb_emetteurs, debit_lh, description
                FROM irrigation_systemes
                WHERE parcelle_id = ? AND actif = 1
            """, (parcelle_id,))
            for row in cur.fetchall():
                s = dict(row)
                label = (f"{s['type_emetteur'].capitalize()} — "
                         f"{s['nb_emetteurs']} × {s['debit_lh']} L/h")
                if s.get("description"):
                    label += f" ({s['description']})"
                self.combo_systeme.addItem(label, s["id"])
                self.combo_systeme.setItemData(
                    self.combo_systeme.count() - 1,
                    (s["nb_emetteurs"], s["debit_lh"]),
                    Qt.UserRole + 1)
            cur.close()
        except Exception:
            traceback.print_exc()
        self._calc_volume()

    def _on_systeme_changed(self):
        systeme_id = self.combo_systeme.currentData()
        if not systeme_id:
            self.lbl_cultures_sys.setText("")
        else:
            cultures = get_cultures_systeme(systeme_id)
            if cultures:
                noms = []
                for c in cultures:
                    if c.get("categorie") == "jachere":
                        noms.append("Jachère")
                    elif c.get("categorie") == "engrais_vert":
                        noms.append("Engrais vert")
                    else:
                        n = c.get("espece") or "—"
                        if c.get("variete"):
                            n += f" ({c['variete']})"
                        noms.append(n)
                self.lbl_cultures_sys.setText(
                    "🌱 Irrigue : " + ", ".join(noms))
            else:
                self.lbl_cultures_sys.setText(
                    "⚠ Aucune culture liée à ce système — "
                    "configurez-le depuis l'onglet Parcelles.")
        self._calc_volume()

    def _calc_volume(self):
        idx = self.combo_systeme.currentIndex()
        sys_data = self.combo_systeme.itemData(idx, Qt.UserRole + 1)

        if not sys_data:
            self.lbl_volume.setText("—")
            self.lbl_sys_info.setText("")
            return

        nb, debit = sys_data
        duree_h = self.inp_heures.value() + self.inp_minutes.value() / 60
        volume = nb * debit * duree_h

        self.lbl_volume.setText(f"{volume:,.0f} L ({volume/1000:.2f} m³)")
        self.lbl_sys_info.setText(
            f"{nb} émetteurs × {debit} L/h × {duree_h:.2f} h")

    def _enregistrer(self):
        parcelle_id = self.combo_parcelle.currentData()
        systeme_id  = self.combo_systeme.currentData()

        if not parcelle_id:
            QMessageBox.warning(self, "Champ manquant", "Sélectionnez une parcelle.")
            return
        if not systeme_id:
            QMessageBox.warning(self, "Champ manquant", "Sélectionnez un système.")
            return

        duree_min = self.inp_heures.value() * 60 + self.inp_minutes.value()
        if duree_min == 0:
            QMessageBox.warning(self, "Durée nulle", "Entrez une durée d'irrigation.")
            return

        idx = self.combo_systeme.currentIndex()
        sys_data = self.combo_systeme.itemData(idx, Qt.UserRole + 1)
        nb, debit = sys_data if sys_data else (0, 0)
        volume = nb * debit * (duree_min / 60)

        date_heure = self.inp_date.dateTime().toString("yyyy-MM-dd HH:mm:00")
        notes = self.inp_notes.text().strip() or None
        user_id = self.current_user.get("id")

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO irrigations
                (parcelle_id, systeme_id, user_id, date_heure,
                 duree_min, volume_calcule_l, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (parcelle_id, systeme_id, user_id,
                  date_heure, duree_min, round(volume, 1), notes))
            conn.commit()
            cur.close()

            QMessageBox.information(self, "Enregistré",
                f"Session enregistrée — Volume : {volume:,.0f} L")
            self.inp_heures.setValue(0)
            self.inp_minutes.setValue(0)
            self.inp_notes.clear()
            self._charger_historique()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))

    def _charger_historique(self):
        parcelle_id = self.combo_filtre_parcelle.currentData()
        date_debut  = self.inp_date_debut.date().toString("yyyy-MM-dd")
        date_fin    = self.inp_date_fin.date().toString("yyyy-MM-dd")

        try:
            conn = get_connection()
            cur = conn.cursor()

            sql = """
                SELECT i.date_heure, p.nom, s.type_emetteur,
                       i.duree_min, i.volume_calcule_l,
                       u.prenom || ' ' || u.nom, i.id, i.systeme_id
                FROM irrigations i
                JOIN parcelles p            ON p.id = i.parcelle_id
                JOIN irrigation_systemes s  ON s.id = i.systeme_id
                JOIN users u                ON u.id = i.user_id
                WHERE DATE(i.date_heure) BETWEEN ? AND ?
            """
            params = [date_debut, date_fin]
            if parcelle_id:
                sql += " AND i.parcelle_id = ?"
                params.append(parcelle_id)
            sql += " ORDER BY i.date_heure DESC"

            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()

            self.table_histo.setRowCount(0)
            total_vol = 0
            for row in rows:
                r = self.table_histo.rowCount()
                self.table_histo.insertRow(r)
                try:
                    dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
                    date_fmt = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    date_fmt = row[0]
                self.table_histo.setItem(r, 0, QTableWidgetItem(date_fmt))
                self.table_histo.setItem(r, 1, QTableWidgetItem(row[1] or ""))
                self.table_histo.setItem(r, 2,
                    QTableWidgetItem(row[2].capitalize() if row[2] else ""))

                cultures = get_cultures_systeme(row[7])
                noms = [c.get("espece") or c.get("categorie", "") for c in cultures]
                cultures_txt = ", ".join(noms) if noms else "—"
                self.table_histo.setItem(r, 3, QTableWidgetItem(cultures_txt))

                h = row[3] // 60
                m = row[3] % 60
                self.table_histo.setItem(r, 4, QTableWidgetItem(f"{h}h{m:02d}"))
                vol = row[4] or 0
                total_vol += vol
                self.table_histo.setItem(r, 5, QTableWidgetItem(f"{vol:,.0f}"))
                self.table_histo.setItem(r, 6, QTableWidgetItem(row[5] or ""))
                self.table_histo.item(r, 0).setData(Qt.UserRole, row[6])

            self.lbl_total.setText(
                f"Total période : {total_vol:,.0f} L ({total_vol/1000:.1f} m³)")
        except Exception:
            traceback.print_exc()

    def _menu_histo(self, pos):
        row = self.table_histo.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_histo.item(row, 0)
        irrigation_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        if self._peut_supprimer:
            menu.addAction("Supprimer cette session",
                lambda: self._supprimer(irrigation_id))
        if menu.isEmpty():
            return
        menu.exec(self.table_histo.viewport().mapToGlobal(pos))

    def _supprimer(self, irrigation_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer cette session d'irrigation ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM irrigations WHERE id = ?", (irrigation_id,))
                conn.commit()
                cur.close()
                self._charger_historique()
            except Exception:
                traceback.print_exc()

    def recharger_parcelles(self):
        self._charger_parcelles()
        self._charger_historique()