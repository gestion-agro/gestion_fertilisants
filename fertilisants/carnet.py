# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from datetime import datetime

from db import (get_connection, peut_action, calculer_azote_apporte,
                verifier_depassement_azote, verifier_fractionnement,
                get_historique_fertilisation)
import utils.debug as debug
import traceback


class CarnetFertilisation(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_ecrire    = peut_action(current_user, "fertilisants", "ecriture")
        self._peut_supprimer = peut_action(current_user, "fertilisants", "suppression")
        self._build_ui()
        self.btn_ajouter.setVisible(self._peut_ecrire)
        self._charger_parcelles()
        self._charger_historique()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        titre = QLabel("Carnet de fertilisation")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        top.addWidget(titre)
        top.addStretch()
        self.btn_ajouter = QPushButton("+ Enregistrer un apport")
        self.btn_ajouter.clicked.connect(lambda: self._ouvrir_dialog())
        top.addWidget(self.btn_ajouter)
        root.addLayout(top)

        # ── Suivi azote organique par parcelle ──
        azote_group = QGroupBox("Suivi azote organique (plafond réglementaire : 170 kg N/ha/an)")
        az_lay = QVBoxLayout(azote_group)
        az_lay.setContentsMargins(8, 8, 8, 8)

        az_top = QHBoxLayout()
        az_top.addWidget(QLabel("Année :"))
        self.combo_annee = QComboBox()
        annee_actuelle = datetime.now().year
        for a in range(annee_actuelle - 3, annee_actuelle + 1):
            self.combo_annee.addItem(str(a), a)
        self.combo_annee.setCurrentText(str(annee_actuelle))
        self.combo_annee.currentIndexChanged.connect(self._charger_suivi_azote)
        az_top.addWidget(self.combo_annee)
        az_top.addStretch()
        az_lay.addLayout(az_top)

        self.table_azote = QTableWidget(0, 3)
        self.table_azote.setHorizontalHeaderLabels(
            ["Parcelle", "N organique cumulé (kg/ha)", "État"])
        self.table_azote.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_azote.setMaximumHeight(140)
        hh = self.table_azote.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        az_lay.addWidget(self.table_azote)
        root.addWidget(azote_group)

        # ── Historique ────────────────────────
        histo_group = QGroupBox("Historique des apports")
        histo_lay = QVBoxLayout(histo_group)
        histo_lay.setContentsMargins(8, 8, 8, 8)

        filtre = QHBoxLayout()
        self.combo_filtre_parcelle = QComboBox()
        self.combo_filtre_parcelle.addItem("Toutes les parcelles", None)
        self.combo_filtre_parcelle.currentIndexChanged.connect(self._charger_historique)
        filtre.addWidget(QLabel("Parcelle :"))
        filtre.addWidget(self.combo_filtre_parcelle)

        self.inp_date_debut = QDateEdit(QDate.currentDate().addMonths(-6))
        self.inp_date_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_debut.setCalendarPopup(True)
        self.inp_date_debut.dateChanged.connect(self._charger_historique)
        filtre.addWidget(QLabel("Du :"))
        filtre.addWidget(self.inp_date_debut)

        self.inp_date_fin = QDateEdit(QDate.currentDate())
        self.inp_date_fin.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_fin.setCalendarPopup(True)
        self.inp_date_fin.dateChanged.connect(self._charger_historique)
        filtre.addWidget(QLabel("Au :"))
        filtre.addWidget(self.inp_date_fin)
        filtre.addStretch()
        histo_lay.addLayout(filtre)

        self.table_histo = QTableWidget(0, 8)
        self.table_histo.setHorizontalHeaderLabels(
            ["Date", "Parcelle", "Culture", "Fertilisant", "Dose",
             "N apporté", "Opérateur", "Notes"])
        self.table_histo.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_histo.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_histo.setAlternatingRowColors(True)
        self.table_histo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_histo.customContextMenuRequested.connect(self._menu_histo)
        hh2 = self.table_histo.horizontalHeader()
        for i in range(7):
            hh2.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(7, QHeaderView.Stretch)
        histo_lay.addWidget(self.table_histo)
        root.addWidget(histo_group, 1)

    # ──────────────────────────────────────────
    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            rows = cur.fetchall()
            cur.close()
            self.combo_filtre_parcelle.clear()
            self.combo_filtre_parcelle.addItem("Toutes les parcelles", None)
            for row in rows:
                self.combo_filtre_parcelle.addItem(row[1], row[0])
            self._charger_suivi_azote()
        except Exception:
            traceback.print_exc()

    def _charger_suivi_azote(self):
        annee = self.combo_annee.currentData()
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            parcelles = cur.fetchall()
            cur.close()

            self.table_azote.setRowCount(0)
            for pid, nom in parcelles:
                check = verifier_depassement_azote(pid, annee)
                if check["cumul_actuel"] <= 0:
                    continue  # n'affiche que les parcelles avec apport organique
                r = self.table_azote.rowCount()
                self.table_azote.insertRow(r)
                self.table_azote.setItem(r, 0, QTableWidgetItem(nom))
                self.table_azote.setItem(r, 1,
                    QTableWidgetItem(f"{check['cumul_actuel']:.1f} / 170"))
                if check["depassement"]:
                    etat = "⚠ DÉPASSEMENT"
                    couleur = QColor("#FEE2E2")
                    couleur_txt = QColor("#DC2626")
                elif check["cumul_actuel"] > 170 * 0.85:
                    etat = "⚠ Proche du seuil"
                    couleur = QColor("#FEF3C7")
                    couleur_txt = QColor("#92400E")
                else:
                    etat = "✓ OK"
                    couleur = None
                    couleur_txt = QColor("#16a34a")
                item_etat = QTableWidgetItem(etat)
                item_etat.setForeground(couleur_txt)
                self.table_azote.setItem(r, 2, item_etat)
                if couleur:
                    for col in range(3):
                        self.table_azote.item(r, col).setBackground(couleur)
        except Exception:
            traceback.print_exc()

    def _charger_historique(self):
        parcelle_id = self.combo_filtre_parcelle.currentData()
        date_debut = self.inp_date_debut.date().toString("yyyy-MM-dd")
        date_fin = self.inp_date_fin.date().toString("yyyy-MM-dd")

        rows = get_historique_fertilisation(parcelle_id, date_debut, date_fin)
        self.table_histo.setRowCount(0)
        for row in rows:
            r = self.table_histo.rowCount()
            self.table_histo.insertRow(r)
            try:
                dt = datetime.strptime(row["date_apport"], "%Y-%m-%d")
                date_fmt = dt.strftime("%d/%m/%Y")
            except Exception:
                date_fmt = row["date_apport"]
            self.table_histo.setItem(r, 0, QTableWidgetItem(date_fmt))
            self.table_histo.setItem(r, 1, QTableWidgetItem(row["parcelle_nom"]))
            culture_txt = row.get("espece") or "—"
            if row.get("variete"):
                culture_txt += f" ({row['variete']})"
            self.table_histo.setItem(r, 2, QTableWidgetItem(culture_txt))
            self.table_histo.setItem(r, 3, QTableWidgetItem(row["fertilisant_nom"]))
            self.table_histo.setItem(r, 4,
                QTableWidgetItem(f"{row['dose_totale_kg']:.1f} kg"))
            n_item = QTableWidgetItem(f"{row['azote_apporte_kg']:.1f} kg")
            if row.get("origine") == "organique":
                n_item.setForeground(QColor("#92400E"))
            self.table_histo.setItem(r, 5, n_item)
            self.table_histo.setItem(r, 6, QTableWidgetItem(row["operateur"]))
            self.table_histo.setItem(r, 7, QTableWidgetItem(row.get("notes") or ""))
            self.table_histo.item(r, 0).setData(Qt.UserRole, row["id"])

    def _menu_histo(self, pos):
        row = self.table_histo.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_histo.item(row, 0)
        apport_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        if self._peut_supprimer:
            menu.addAction("Supprimer cet apport",
                lambda: self._supprimer(apport_id))
        if not menu.isEmpty():
            menu.exec(self.table_histo.viewport().mapToGlobal(pos))

    def _supprimer(self, apport_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer cet apport du carnet ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM carnet_fertilisation WHERE id=?",
                            (apport_id,))
                conn.commit()
                cur.close()
                self._charger_historique()
                self._charger_suivi_azote()
            except Exception:
                traceback.print_exc()

    def _ouvrir_dialog(self):
        dlg = DialogApportFerti(current_user=self.current_user, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_historique()
            self._charger_suivi_azote()

    def recharger(self):
        self._charger_parcelles()
        self._charger_historique()


# ──────────────────────────────────────────────
# Dialog Apport (saisie unitaire ou pré-rempli depuis Aide à la décision)
# ──────────────────────────────────────────────
class DialogApportFerti(QDialog):
    def __init__(self, current_user: dict, parcelle_id=None,
                 culture_parcelle_id=None, pre_remplissage=None, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.parcelle_id = parcelle_id
        self.culture_parcelle_id = culture_parcelle_id
        self.pre_remplissage = pre_remplissage or []
        self.setWindowTitle("Enregistrer un apport de fertilisant")
        self.setMinimumWidth(520)
        self.setMinimumHeight(480)
        self._build_ui()
        self._charger_parcelles()
        if parcelle_id:
            idx = self.combo_parcelle.findData(parcelle_id)
            if idx >= 0:
                self.combo_parcelle.setCurrentIndex(idx)
        if self.pre_remplissage:
            self._appliquer_pre_remplissage()

    def _build_ui(self):
        root = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)

        self.combo_parcelle = QComboBox()
        self.combo_parcelle.currentIndexChanged.connect(self._on_parcelle_changed)
        form.addRow("Parcelle *", self.combo_parcelle)

        self.combo_culture = QComboBox()
        self.combo_culture.addItem("— Aucune (apport global) —", None)
        form.addRow("Culture concernée", self.combo_culture)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date *", self.inp_date)

        sep = QLabel("── Apports ──")
        sep.setStyleSheet("color:gray; font-size:11px;")
        form.addRow(sep)

        self.lignes_lay = QVBoxLayout()
        self.lignes_lay.setSpacing(6)
        form.addRow(self.lignes_lay)

        btn_add_ligne = QPushButton("+ Ajouter un fertilisant")
        btn_add_ligne.clicked.connect(lambda: self._ajouter_ligne())
        btn_add_ligne.setStyleSheet("""
            QPushButton { border:1px dashed palette(mid);
                border-radius:4px; padding:4px 12px; }
            QPushButton:hover { border-color:#16a34a; color:#16a34a; }
        """)
        form.addRow(btn_add_ligne)

        self.lbl_alerte = QLabel("")
        self.lbl_alerte.setWordWrap(True)
        form.addRow(self.lbl_alerte)

        self.inp_methode = QLineEdit()
        self.inp_methode.setPlaceholderText("Ex: épandage, fertirrigation...")
        form.addRow("Méthode", self.inp_methode)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(60)
        form.addRow("Notes", self.inp_notes)

        scroll.setWidget(w)
        root.addWidget(scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._lignes = []
        if not self.pre_remplissage:
            self._ajouter_ligne()

    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom, surface_ha FROM parcelles WHERE actif=1 ORDER BY nom")
            self.combo_parcelle.clear()
            for row in cur.fetchall():
                self.combo_parcelle.addItem(row[1], dict(id=row[0], surface_ha=row[2]))
            cur.close()
        except Exception:
            traceback.print_exc()

    def _on_parcelle_changed(self):
        data = self.combo_parcelle.currentData()
        self.combo_culture.clear()
        self.combo_culture.addItem("— Aucune (apport global) —", None)
        if not data:
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, espece, variete FROM cultures_parcelle
                WHERE parcelle_id=? AND actif=1
            """, (data["id"],))
            for cid, esp, var in cur.fetchall():
                label = esp or "—"
                if var:
                    label += f" ({var})"
                self.combo_culture.addItem(label, cid)
            cur.close()
        except Exception:
            traceback.print_exc()
        if self.culture_parcelle_id:
            idx = self.combo_culture.findData(self.culture_parcelle_id)
            if idx >= 0:
                self.combo_culture.setCurrentIndex(idx)

    def _ajouter_ligne(self, fertilisant_id=None, dose=None):
        ligne = LigneApport(on_supprimer=self._supprimer_ligne,
                            fertilisant_id=fertilisant_id, dose=dose)
        ligne.dose_modifiee.connect(self._maj_alerte)
        self._lignes.append(ligne)
        idx = self.lignes_lay.count()
        self.lignes_lay.insertWidget(idx, ligne)
        self._maj_alerte()

    def _supprimer_ligne(self, ligne):
        if ligne in self._lignes:
            self._lignes.remove(ligne)
        ligne.setParent(None)
        ligne.deleteLater()
        self._maj_alerte()

    def _appliquer_pre_remplissage(self):
        for calc in self.pre_remplissage:
            self._ajouter_ligne(
                fertilisant_id=calc["fertilisant_id"],
                dose=calc["dose_surface"])

    def _maj_alerte(self):
        data_parcelle = self.combo_parcelle.currentData()
        if not data_parcelle:
            self.lbl_alerte.setText("")
            return
        surface_ha = data_parcelle.get("surface_ha") or 0

        total_n = 0
        for ligne in self._lignes:
            d = ligne.get_data()
            if d:
                total_n += d["azote_kg"]

        if surface_ha <= 0 or total_n == 0:
            self.lbl_alerte.setText("")
            return

        annee = self.inp_date.date().year()
        check = verifier_depassement_azote(
            data_parcelle["id"], annee, total_n, surface_ha)

        msgs = []
        if check["depassement"]:
            msgs.append(
                f"⚠ DÉPASSEMENT plafond azote organique : "
                f"{check['nouveau_total']:.0f} kg N/ha/an "
                f"(plafond légal : 170 kg N/ha/an, directive nitrates)")

        frac = verifier_fractionnement(total_n)
        if frac["depassement"]:
            msgs.append(
                f"⚠ Fractionnement : cet apport ({total_n:.0f} kg N) dépasse "
                f"le maximum recommandé de {frac['seuil']} kg N par passage"
                + (" pour le maïs" if frac["est_mais"] else ""))

        if msgs:
            self.lbl_alerte.setText("\n".join(msgs))
            self.lbl_alerte.setStyleSheet(
                "background:#FEE2E2; border:1px solid #DC2626; "
                "border-radius:4px; padding:6px; color:#DC2626; font-size:11px;")
        else:
            self.lbl_alerte.setText(
                f"✓ Cumul azote organique : {check['nouveau_total']:.0f} kg N/ha/an "
                f"(plafond : 170)")
            self.lbl_alerte.setStyleSheet(
                "background:#F0FDF4; border:1px solid #16a34a; "
                "border-radius:4px; padding:6px; color:#16a34a; font-size:11px;")

    def _valider(self):
        data_parcelle = self.combo_parcelle.currentData()
        if not data_parcelle:
            QMessageBox.warning(self, "Champ manquant", "Sélectionnez une parcelle.")
            return

        lignes_data = [l.get_data() for l in self._lignes]
        lignes_data = [d for d in lignes_data if d]
        if not lignes_data:
            QMessageBox.warning(self, "Champ manquant",
                "Ajoutez au moins un fertilisant avec une dose.")
            return

        from db import est_exploitation_bio
        if est_exploitation_bio():
            non_uab = [d.get("nom_fert") for d in lignes_data
                      if not d.get("uab")]
            non_uab = [n for n in non_uab if n]
            if non_uab:
                rep = QMessageBox.warning(
                    self, "⚠ Fertilisant non autorisé en agriculture biologique",
                    "Votre exploitation est déclarée en agriculture biologique, "
                    "mais le(s) fertilisant(s) suivant(s) ne sont PAS certifiés "
                    "UAB :\n\n" + "\n".join(f"• {n}" for n in non_uab) +
                    "\n\nL'utilisation de ce produit pourrait remettre en cause "
                    "votre certification bio.\n\nConfirmer malgré tout ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if rep == QMessageBox.No:
                    return

        date_apport = self.inp_date.date().toString("yyyy-MM-dd")
        culture_id = self.combo_culture.currentData()
        methode = self.inp_methode.text().strip() or None
        notes = self.inp_notes.toPlainText().strip() or None
        surface_ha = data_parcelle.get("surface_ha") or 1
        operateur_id = self.current_user.get("id")

        try:
            conn = get_connection()
            cur = conn.cursor()
            for d in lignes_data:
                cur.execute("""
                    INSERT INTO carnet_fertilisation (
                        operateur_id, parcelle_id, culture_parcelle_id,
                        fertilisant_id, date_apport, dose_totale_kg,
                        surface_traitee_ha, azote_apporte_kg,
                        phosphore_apporte_kg, potassium_apporte_kg,
                        methode, notes
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (operateur_id, data_parcelle["id"], culture_id,
                      d["fertilisant_id"], date_apport, d["dose_kg"],
                      surface_ha, d["azote_kg"], d["phosphore_kg"],
                      d["potassium_kg"], methode, notes))
            conn.commit()
            cur.close()
            debug.debug(f"[carnet_ferti] {len(lignes_data)} apport(s) enregistré(s)")
            self.accept()
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))


class LigneApport(QFrame):
    dose_modifiee = Signal()

    def __init__(self, on_supprimer, fertilisant_id=None, dose=None, parent=None):
        super().__init__(parent)
        self.on_supprimer = on_supprimer
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Plain)
        self._fertilisants = []
        self._build_ui()
        if fertilisant_id:
            for i in range(self.combo_fert.count()):
                data = self.combo_fert.itemData(i)
                if data and data.get("id") == fertilisant_id:
                    self.combo_fert.setCurrentIndex(i)
                    break
        if dose:
            self.inp_dose.setValue(dose)

    def _build_ui(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        from db import est_exploitation_bio
        self._est_bio = est_exploitation_bio()

        self.combo_fert = QComboBox()
        self.combo_fert.setMinimumWidth(180)
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id, nom, n, p, k, origine, uab FROM fertilisants ORDER BY nom")
            for row in cur.fetchall():
                label = row[1] if row[5] else f"⚠ {row[1]} (non UAB)"
                self.combo_fert.addItem(label, dict(
                    id=row[0], n=row[2], p=row[3], k=row[4],
                    origine=row[5], uab=row[6]))
            cur.close()
        except Exception:
            traceback.print_exc()
        self.combo_fert.currentIndexChanged.connect(self._on_fert_changed)
        lay.addWidget(self.combo_fert, 1)

        self.inp_dose = QDoubleSpinBox()
        self.inp_dose.setRange(0, 99999)
        self.inp_dose.setDecimals(1)
        self.inp_dose.setSuffix(" kg")
        self.inp_dose.valueChanged.connect(lambda: self.dose_modifiee.emit())
        lay.addWidget(self.inp_dose)

        btn_sup = QPushButton("×")
        btn_sup.setFixedSize(22, 22)
        btn_sup.setStyleSheet("""
            QPushButton { background:transparent; color:#9ca3af;
                border:none; font-size:16px; font-weight:bold; }
            QPushButton:hover { background:#FEE2E2; color:#DC2626; }
        """)
        btn_sup.clicked.connect(lambda: self.on_supprimer(self))
        lay.addWidget(btn_sup)

    def _on_fert_changed(self):
        fert = self.combo_fert.currentData()
        if self._est_bio and fert and not fert.get("uab"):
            self.combo_fert.setStyleSheet(
                "QComboBox { background:#FEE2E2; color:#DC2626; }")
        else:
            self.combo_fert.setStyleSheet("")
        self.dose_modifiee.emit()

    def get_data(self) -> dict | None:
        fert = self.combo_fert.currentData()
        dose = self.inp_dose.value()
        if not fert or dose <= 0:
            return None
        return {
            "fertilisant_id": fert["id"],
            "nom_fert": self.combo_fert.currentText().replace("⚠ ", "").replace(" (non UAB)", ""),
            "uab": fert.get("uab"),
            "dose_kg": dose,
            "azote_kg": dose * fert["n"] / 100,
            "phosphore_kg": dose * fert["p"] / 100,
            "potassium_kg": dose * fert["k"] / 100,
            "origine": fert["origine"],
        }