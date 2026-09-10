# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from datetime import datetime

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import (get_connection, peut_action,
                calculer_rendement_previsionnel, calculer_ca_previsionnel,
                get_recolte, upsert_recolte,
                get_ventes_recolte, get_recap_ca)
import utils.debug as debug
import traceback


class RecoltePage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_ecrire    = peut_action(current_user, "parcelles", "ecriture")
        self._peut_supprimer = peut_action(current_user, "parcelles", "suppression")
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Récoltes & Chiffre d'affaires")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        # Filtre année
        filtre = QHBoxLayout()
        filtre.addWidget(QLabel("Année :"))
        self.combo_annee = QComboBox()
        annee_act = datetime.now().year
        for a in range(annee_act - 3, annee_act + 2):
            self.combo_annee.addItem(str(a), a)
        self.combo_annee.setCurrentText(str(annee_act))
        self.combo_annee.currentIndexChanged.connect(self._charger)
        filtre.addWidget(self.combo_annee)
        filtre.addStretch()
        root.addLayout(filtre)

        tabs = QTabWidget()
        tabs.addTab(self._tab_previsionnelle(), "📊 Prévisionnelle")
        tabs.addTab(self._tab_reelle(),         "✏️ Réelle")
        tabs.addTab(self._tab_recap(),          "💶 Récap CA")
        root.addWidget(tabs, 1)

    # ──────────────────────────────────────────
    # Onglet 1 : Prévisionnelle
    # ──────────────────────────────────────────
    def _tab_previsionnelle(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)

        info = QLabel(
            "Rendements et CA prévisionnels calculés depuis les données "
            "de vos cultures (rendement/ml ou t/ha × surface × prix).")
        info.setStyleSheet("color: palette(mid); font-size: 11px;")
        info.setWordWrap(True)
        lay.addWidget(info)

        self.table_previ = QTableWidget(0, 7)
        self.table_previ.setHorizontalHeaderLabels([
            "Parcelle", "Culture", "Catégorie", "Surface",
            "Rendement prévi. (kg)", "Prix moyen", "CA prévi. (€)"])
        self.table_previ.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_previ.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_previ.setAlternatingRowColors(True)
        hh = self.table_previ.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 7):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        lay.addWidget(self.table_previ, 1)

        # Ligne totaux
        self.lbl_total_previ = QLabel("")
        self.lbl_total_previ.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 4px;")
        lay.addWidget(self.lbl_total_previ)
        return w

    # ──────────────────────────────────────────
    # Onglet 2 : Réelle
    # ──────────────────────────────────────────
    def _tab_reelle(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.addWidget(QLabel("Sélectionnez une culture pour saisir ses ventes :"))
        top.addStretch()
        lay.addLayout(top)

        splitter = QSplitter(Qt.Horizontal)

        # Liste des cultures (gauche)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("Cultures de l'année :"))
        self.table_cultures_reelle = QTableWidget(0, 4)
        self.table_cultures_reelle.setHorizontalHeaderLabels([
            "Parcelle", "Culture", "Prévi. (kg)", "Réel (kg)"])
        self.table_cultures_reelle.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures_reelle.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures_reelle.setAlternatingRowColors(True)
        self.table_cultures_reelle.itemSelectionChanged.connect(
            self._on_culture_reelle_changed)
        hh = self.table_cultures_reelle.horizontalHeader()
        for i in range(4):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        ll.addWidget(self.table_cultures_reelle)
        splitter.addWidget(left)

        # Ventes (droite)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)

        self.lbl_culture_sel = QLabel("— Sélectionnez une culture —")
        self.lbl_culture_sel.setStyleSheet("font-weight: bold; font-size: 13px;")
        rl.addWidget(self.lbl_culture_sel)

        self.table_ventes = QTableWidget(0, 6)
        self.table_ventes.setHorizontalHeaderLabels([
            "Date", "Quantité (kg)", "Prix (€/kg)", "CA (€)",
            "Canal", "Magasin/Débouché"])
        self.table_ventes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_ventes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_ventes.setAlternatingRowColors(True)
        self.table_ventes.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_ventes.customContextMenuRequested.connect(self._menu_vente)
        hh2 = self.table_ventes.horizontalHeader()
        hh2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh2.setSectionResizeMode(5, QHeaderView.Stretch)
        rl.addWidget(self.table_ventes, 1)

        btn_add_vente = QPushButton("+ Ajouter une vente")
        btn_add_vente.setEnabled(False)
        btn_add_vente.clicked.connect(self._ajouter_vente)
        self.btn_add_vente = btn_add_vente
        if not self._peut_ecrire:
            btn_add_vente.setVisible(False)
        rl.addWidget(btn_add_vente)

        self.lbl_total_reelle = QLabel("")
        self.lbl_total_reelle.setStyleSheet(
            "font-weight: bold; font-size: 12px; padding: 2px;")
        rl.addWidget(self.lbl_total_reelle)

        splitter.addWidget(right)
        splitter.setSizes([300, 500])
        lay.addWidget(splitter, 1)
        return w

    # ──────────────────────────────────────────
    # Onglet 3 : Récap CA
    # ──────────────────────────────────────────
    def _tab_recap(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        # Filtre année pour le récap (toutes années par défaut)
        recap_top = QHBoxLayout()
        self.combo_recap_annee = QComboBox()
        self.combo_recap_annee.addItem("Toutes les années", None)
        annee_act = datetime.now().year
        for a in range(annee_act - 3, annee_act + 1):
            self.combo_recap_annee.addItem(str(a), a)
        self.combo_recap_annee.currentIndexChanged.connect(self._charger_recap)
        recap_top.addWidget(QLabel("Filtrer :"))
        recap_top.addWidget(self.combo_recap_annee)
        recap_top.addStretch()
        lay.addLayout(recap_top)

        self.table_recap = QTableWidget(0, 9)
        self.table_recap.setHorizontalHeaderLabels([
            "Année", "Parcelle", "Culture", "Canal", "Magasin",
            "Qté réelle (kg)", "CA réel (€)",
            "Prévi. (kg)", "CA prévi. (€)"])
        self.table_recap.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_recap.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_recap.setAlternatingRowColors(True)
        hh = self.table_recap.horizontalHeader()
        hh.setSectionResizeMode(2, QHeaderView.Stretch)
        for i in [0, 1, 3, 4, 5, 6, 7, 8]:
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        lay.addWidget(self.table_recap, 1)

        self.lbl_recap_totaux = QLabel("")
        self.lbl_recap_totaux.setStyleSheet(
            "font-weight: bold; font-size: 13px; padding: 4px;")
        lay.addWidget(self.lbl_recap_totaux)
        return w

    # ──────────────────────────────────────────
    # Chargement
    # ──────────────────────────────────────────
    def _charger(self):
        self._charger_previsionnelle()
        self._charger_cultures_reelle()
        self._charger_recap()

    def _charger_previsionnelle(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                SELECT cp.id, cp.espece, cp.variete, cp.categorie,
                       cp.surface_occupee_m2, cp.nb_rangs,
                       cp.longueur_planche, cp.nb_planches,
                       cp.rendement_ml, cp.rendement_ha,
                       cp.prix_moyen_kg, cp.prix_moyen_tonne,
                       p.nom AS parcelle_nom
                FROM cultures_parcelle cp
                JOIN parcelles p ON p.id = cp.parcelle_id
                WHERE cp.actif = 1 AND cp.categorie IN ('maraichage', 'arbo')
                ORDER BY p.nom, cp.espece
            """)
            cultures = [dict(r) for r in cur.fetchall()]
            cur.close()

            self.table_previ.setRowCount(0)
            total_rend = total_ca = 0

            for c in cultures:
                rend_kg = calculer_rendement_previsionnel(c)
                ca_eur  = calculer_ca_previsionnel(c)
                total_rend += rend_kg
                total_ca   += ca_eur

                surf = c.get("surface_occupee_m2") or 0
                surf_txt = f"{surf:.0f} m²" if surf < 10000 else f"{surf/10000:.2f} ha"

                cat = c.get("categorie", "—")
                if c.get("categorie") == "maraichage":
                    prix_txt = f"{c.get('prix_moyen_kg') or 0:.2f} €/kg"
                else:
                    prix_txt = f"{c.get('prix_moyen_tonne') or 0:.2f} €/t"

                label = c.get("espece") or "—"
                if c.get("variete"):
                    label += f" ({c['variete']})"

                r = self.table_previ.rowCount()
                self.table_previ.insertRow(r)
                self.table_previ.setItem(r, 0, QTableWidgetItem(c["parcelle_nom"]))
                self.table_previ.setItem(r, 1, QTableWidgetItem(label))
                self.table_previ.setItem(r, 2, QTableWidgetItem(cat))
                self.table_previ.setItem(r, 3, QTableWidgetItem(surf_txt))
                self.table_previ.setItem(r, 4,
                    QTableWidgetItem(f"{rend_kg:.0f} kg" if rend_kg else "—"))
                self.table_previ.setItem(r, 5, QTableWidgetItem(prix_txt))
                ca_item = QTableWidgetItem(f"{ca_eur:.2f} €" if ca_eur else "—")
                if ca_eur > 0:
                    ca_item.setForeground(QColor("#16a34a"))
                self.table_previ.setItem(r, 6, ca_item)
                self.table_previ.item(r, 0).setData(Qt.UserRole, c["id"])

            self.lbl_total_previ.setText(
                f"Total prévisionnel : {total_rend:.0f} kg  —  "
                f"CA prévisionnel : {total_ca:,.2f} €")
        except Exception:
            traceback.print_exc()

    def _charger_cultures_reelle(self):
        annee = self.combo_annee.currentData()
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                SELECT cp.id, cp.espece, cp.variete, cp.categorie,
                       cp.surface_occupee_m2, cp.nb_rangs,
                       cp.longueur_planche, cp.nb_planches,
                       cp.rendement_ml, cp.rendement_ha,
                       cp.prix_moyen_kg, cp.prix_moyen_tonne,
                       p.nom AS parcelle_nom
                FROM cultures_parcelle cp
                JOIN parcelles p ON p.id = cp.parcelle_id
                WHERE cp.actif = 1 AND cp.categorie IN ('maraichage', 'arbo')
                ORDER BY p.nom, cp.espece
            """)
            cultures = [dict(r) for r in cur.fetchall()]
            cur.close()

            self.table_cultures_reelle.setRowCount(0)
            self._cultures_reelle = cultures

            for c in cultures:
                previ_kg = calculer_rendement_previsionnel(c)
                recolte  = get_recolte(c["id"], annee)
                reel_kg  = recolte["quantite_kg_reel"] if recolte else None

                label = c.get("espece") or "—"
                if c.get("variete"):
                    label += f" ({c['variete']})"

                r = self.table_cultures_reelle.rowCount()
                self.table_cultures_reelle.insertRow(r)
                self.table_cultures_reelle.setItem(
                    r, 0, QTableWidgetItem(c["parcelle_nom"]))
                self.table_cultures_reelle.setItem(r, 1, QTableWidgetItem(label))
                self.table_cultures_reelle.setItem(
                    r, 2, QTableWidgetItem(f"{previ_kg:.0f}" if previ_kg else "—"))
                reel_item = QTableWidgetItem(
                    f"{reel_kg:.0f}" if reel_kg is not None else "—")
                if reel_kg and previ_kg and reel_kg >= previ_kg:
                    reel_item.setForeground(QColor("#16a34a"))
                elif reel_kg is not None and previ_kg and reel_kg < previ_kg:
                    reel_item.setForeground(QColor("#D97706"))
                self.table_cultures_reelle.setItem(r, 3, reel_item)
                self.table_cultures_reelle.item(r, 0).setData(Qt.UserRole, c["id"])

        except Exception:
            traceback.print_exc()

    def _on_culture_reelle_changed(self):
        row = self.table_cultures_reelle.currentRow()
        if row < 0:
            self.btn_add_vente.setEnabled(False)
            self.table_ventes.setRowCount(0)
            self.lbl_culture_sel.setText("— Sélectionnez une culture —")
            return

        item = self.table_cultures_reelle.item(row, 0)
        culture_id = item.data(Qt.UserRole)
        annee = self.combo_annee.currentData()

        label = self.table_cultures_reelle.item(row, 1).text()
        parc  = self.table_cultures_reelle.item(row, 0).text()
        self.lbl_culture_sel.setText(f"{parc} — {label} ({annee})")
        self._culture_courante_id = culture_id
        self._culture_courante_annee = annee

        self.btn_add_vente.setEnabled(True)
        self._charger_ventes(culture_id, annee)

    def _charger_ventes(self, culture_id: int, annee: int):
        recolte = get_recolte(culture_id, annee)
        self.table_ventes.setRowCount(0)
        total_kg = total_ca = 0

        if not recolte:
            self.lbl_total_reelle.setText("Aucune vente enregistrée.")
            return

        ventes = get_ventes_recolte(recolte["id"])
        for v in ventes:
            ca = (v.get("quantite_kg") or 0) * (v.get("prix_unitaire") or 0)
            total_kg += v.get("quantite_kg") or 0
            total_ca += ca

            r = self.table_ventes.rowCount()
            self.table_ventes.insertRow(r)
            try:
                dt = datetime.strptime(v["date_vente"], "%Y-%m-%d")
                date_fmt = dt.strftime("%d/%m/%Y")
            except Exception:
                date_fmt = v["date_vente"]
            self.table_ventes.setItem(r, 0, QTableWidgetItem(date_fmt))
            self.table_ventes.setItem(r, 1,
                QTableWidgetItem(f"{v.get('quantite_kg', 0):.1f}"))
            self.table_ventes.setItem(r, 2,
                QTableWidgetItem(f"{v.get('prix_unitaire', 0):.2f}"))
            self.table_ventes.setItem(r, 3, QTableWidgetItem(f"{ca:.2f}"))
            self.table_ventes.setItem(r, 4,
                QTableWidgetItem(v.get("canal_vente") or "—"))
            self.table_ventes.setItem(r, 5,
                QTableWidgetItem(v.get("magasin") or "—"))
            self.table_ventes.item(r, 0).setData(Qt.UserRole, v["id"])

        self.lbl_total_reelle.setText(
            f"Total : {total_kg:.1f} kg  —  CA réel : {total_ca:,.2f} €")

        # Mettre à jour quantite_kg_reel dans recoltes
        upsert_recolte(culture_id, annee,
                       quantite_kg_reel=total_kg if total_kg > 0 else None)
        self._charger_cultures_reelle()

    def _ajouter_vente(self):
        if not hasattr(self, "_culture_courante_id"):
            return
        dlg = DialogVente(
            culture_parcelle_id=self._culture_courante_id,
            annee=self._culture_courante_annee,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_ventes(
                self._culture_courante_id, self._culture_courante_annee)
            self._charger_recap()

    def _menu_vente(self, pos):
        if not self._peut_supprimer:
            return
        row = self.table_ventes.rowAt(pos.y())
        if row < 0:
            return
        vente_id = self.table_ventes.item(row, 0).data(Qt.UserRole)
        menu = QMenu(self)
        menu.addAction("Supprimer cette vente",
                       lambda: self._supprimer_vente(vente_id))
        menu.exec(self.table_ventes.viewport().mapToGlobal(pos))

    def _supprimer_vente(self, vente_id: int):
        rep = QMessageBox.question(self, "Confirmer", "Supprimer cette vente ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur  = conn.cursor()
                cur.execute("DELETE FROM recolte_ventes WHERE id=?", (vente_id,))
                conn.commit()
                cur.close()
                self._charger_ventes(
                    self._culture_courante_id, self._culture_courante_annee)
                self._charger_recap()
            except Exception:
                traceback.print_exc()

    def _charger_recap(self):
        annee = self.combo_recap_annee.currentData()
        rows  = get_recap_ca(annee)

        self.table_recap.setRowCount(0)
        total_ca_reel = total_ca_previ = 0

        for row in rows:
            # Calcul prévi pour cette culture
            rend_previ = calculer_rendement_previsionnel(row)
            ca_previ   = calculer_ca_previsionnel(row)
            total_ca_reel  += row.get("ca_reel") or 0
            total_ca_previ += ca_previ

            label = row.get("espece") or "—"
            if row.get("variete"):
                label += f" ({row['variete']})"

            r = self.table_recap.rowCount()
            self.table_recap.insertRow(r)
            self.table_recap.setItem(r, 0, QTableWidgetItem(str(row["annee"])))
            self.table_recap.setItem(r, 1, QTableWidgetItem(row["parcelle_nom"] or "—"))
            self.table_recap.setItem(r, 2, QTableWidgetItem(label))
            self.table_recap.setItem(r, 3,
                QTableWidgetItem(row.get("canal_vente") or "—"))
            self.table_recap.setItem(r, 4,
                QTableWidgetItem(row.get("magasin") or "—"))

            qte = row.get("quantite_kg")
            self.table_recap.setItem(r, 5,
                QTableWidgetItem(f"{qte:.1f}" if qte else "—"))

            ca_reel = row.get("ca_reel") or 0
            ca_item = QTableWidgetItem(f"{ca_reel:.2f}")
            if ca_reel > 0:
                ca_item.setForeground(QColor("#16a34a"))
            self.table_recap.setItem(r, 6, ca_item)

            self.table_recap.setItem(r, 7,
                QTableWidgetItem(f"{rend_previ:.0f}" if rend_previ else "—"))
            self.table_recap.setItem(r, 8,
                QTableWidgetItem(f"{ca_previ:.2f}" if ca_previ else "—"))

            # Coloration écart
            if ca_reel and ca_previ:
                ecart = (ca_reel - ca_previ) / ca_previ * 100
                ecart_item = QTableWidgetItem(f"{ecart:+.1f}%")
                ecart_item.setForeground(
                    QColor("#16a34a") if ecart >= 0 else QColor("#DC2626"))

        self.lbl_recap_totaux.setText(
            f"CA réel total : {total_ca_reel:,.2f} €  —  "
            f"CA prévisionnel : {total_ca_previ:,.2f} €  —  "
            f"Écart : {total_ca_reel - total_ca_previ:+,.2f} €")

    def recharger(self):
        self._charger()


# ──────────────────────────────────────────────
# Dialog : Saisir une vente
# ──────────────────────────────────────────────
class DialogVente(QDialog):
    def __init__(self, culture_parcelle_id: int, annee: int, parent=None):
        super().__init__(parent)
        self.culture_parcelle_id = culture_parcelle_id
        self.annee = annee
        self.setWindowTitle("Enregistrer une vente")
        self.setMinimumWidth(400)
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date *", self.inp_date)

        self.inp_quantite = QDoubleSpinBox()
        self.inp_quantite.setRange(0.1, 999999)
        self.inp_quantite.setDecimals(1)
        self.inp_quantite.setSuffix(" kg")
        form.addRow("Quantité *", self.inp_quantite)

        self.inp_prix = QDoubleSpinBox()
        self.inp_prix.setRange(0, 9999)
        self.inp_prix.setDecimals(2)
        self.inp_prix.setSuffix(" €/kg")
        form.addRow("Prix unitaire *", self.inp_prix)

        self.lbl_ca = QLabel("CA : —")
        self.lbl_ca.setStyleSheet("font-weight: bold; color: #16a34a;")
        self.inp_quantite.valueChanged.connect(self._maj_ca)
        self.inp_prix.valueChanged.connect(self._maj_ca)
        form.addRow("CA estimé :", self.lbl_ca)

        self.inp_canal = QComboBox()
        self.inp_canal.setEditable(True)
        self.inp_canal.addItems([
            "", "Vente directe (marché)", "Vente directe (ferme)",
            "AMAP", "Restauration collective", "GMS (grande surface)",
            "Grossiste", "Coopérative", "Autre"])
        form.addRow("Canal de vente", self.inp_canal)

        self.inp_magasin = QLineEdit()
        self.inp_magasin.setPlaceholderText("Nom du magasin, restaurant, marché...")
        form.addRow("Magasin/Débouché", self.inp_magasin)

        self.inp_notes = QLineEdit()
        form.addRow("Notes", self.inp_notes)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        form.addRow(self.lbl_err)

        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _maj_ca(self):
        ca = self.inp_quantite.value() * self.inp_prix.value()
        self.lbl_ca.setText(f"CA : {ca:.2f} €")

    def _valider(self):
        quantite = self.inp_quantite.value()
        prix     = self.inp_prix.value()
        if quantite <= 0:
            self.lbl_err.setText("La quantité est obligatoire.")
            return
        if prix <= 0:
            self.lbl_err.setText("Le prix est obligatoire.")
            return

        date_vente = self.inp_date.date().toString("yyyy-MM-dd")
        canal      = self.inp_canal.currentText().strip() or None
        magasin    = self.inp_magasin.text().strip() or None
        notes      = self.inp_notes.text().strip() or None

        try:
            # Crée la récolte si elle n'existe pas encore
            rid = upsert_recolte(self.culture_parcelle_id, self.annee)
            if not rid:
                self.lbl_err.setText("Erreur : impossible de créer la récolte.")
                return

            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                INSERT INTO recolte_ventes
                    (recolte_id, date_vente, quantite_kg,
                     prix_unitaire, canal_vente, magasin, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rid, date_vente, quantite, prix, canal, magasin, notes))
            conn.commit()
            cur.close()
            debug.debug(f"[recolte] Vente enregistrée : {quantite}kg × {prix}€/kg")
            self.accept()
        except Exception as e:
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")