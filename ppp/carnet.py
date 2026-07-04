# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
from views.login import peut
import utils.debug as debug
import traceback


# ─────────────────────────────────────────────────────────────
# Widget ligne dépliable pour le carnet
# ─────────────────────────────────────────────────────────────
class LigneTraitement(QWidget):
    def __init__(self, traitement: dict, parent=None):
        super().__init__(parent)
        self.traitement = traitement
        self._expanded = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("QWidget { border-bottom: 1px solid palette(mid); }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(12)

        statut = self.traitement.get("statut_decision", "fait")
        couleurs = {"en_attente": "#F5A623", "en_cours": "#4A90E2",
                    "fait": "#7ED321", "annule": "#D0021B"}
        lbl_statut = QLabel("●")
        lbl_statut.setStyleSheet(
            f"color: {couleurs.get(statut, '#888')}; font-size: 16px;")
        lbl_statut.setFixedWidth(20)
        header.addWidget(lbl_statut)

        date = self.traitement.get("date_traitement") or \
               self.traitement.get("date_prevue") or "—"
        lbl_date = QLabel(self._fmt_date(date))
        lbl_date.setFixedWidth(90)
        lbl_date.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_date)

        lbl_produit = QLabel(self.traitement.get("nom_commercial", "—"))
        lbl_produit.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_produit, 2)

        lbl_culture = QLabel(self.traitement.get("culture", "—"))
        lbl_culture.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_culture, 1)

        lbl_parcelle = QLabel(self.traitement.get("parcelle_nom") or "—")
        lbl_parcelle.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_parcelle, 1)

        lbl_bio = QLabel(self.traitement.get("bio_agresseur") or "—")
        lbl_bio.setStyleSheet("color: palette(mid); font-size: 12px;")
        header.addWidget(lbl_bio, 1)

        ope = self.traitement.get("operateur_nom") or "—"
        lbl_ope = QLabel(f"OPE: {ope}")
        lbl_ope.setStyleSheet("font-size: 11px; color: palette(mid);")
        header.addWidget(lbl_ope)

        self.lbl_arrow = QLabel("▶")
        self.lbl_arrow.setFixedWidth(16)
        header.addWidget(self.lbl_arrow)

        header_widget = QWidget()
        header_widget.setLayout(header)
        header_widget.setCursor(Qt.PointingHandCursor)
        header_widget.mousePressEvent = lambda e: self._toggle()
        layout.addWidget(header_widget)

        self.detail_widget = self._build_detail()
        self.detail_widget.setVisible(False)
        layout.addWidget(self.detail_widget)

    def _build_detail(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: palette(base); border-radius: 4px;")
        layout = QGridLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)
        t = self.traitement

        def _row(layout, r, label, value):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
            val = QLabel(str(value) if value else "—")
            val.setWordWrap(True)
            val.setStyleSheet("font-size: 12px;")
            layout.addWidget(lbl, r, 0)
            layout.addWidget(val, r, 1)

        row = 0
        _row(layout, row, "Produit :",
             f"{t.get('nom_commercial','—')} (AMM {t.get('num_amm','—')})")
        row += 1; _row(layout, row, "Substance(s) :", t.get("substance_active"))
        row += 1; _row(layout, row, "Culture :", t.get("culture"))
        row += 1; _row(layout, row, "Bio-agresseur :", t.get("bio_agresseur"))
        row += 1; _row(layout, row, "Parcelle :", t.get("parcelle_nom"))
        row += 1
        dose = t.get("dose_appliquee")
        unite = t.get("unite", "L/ha")
        surf = t.get("surface_traitee_ha")
        dose_txt = f"{dose} {unite}" if dose else "—"
        if surf:
            dose_txt += f" — surface : {surf} ha"
        _row(layout, row, "Dose appliquée :", dose_txt)
        row += 1; _row(layout, row, "Date traitement :",
             self._fmt_date(t.get("date_traitement")))
        row += 1; _row(layout, row, "Décideur :", t.get("decideur_nom"))
        row += 1; _row(layout, row, "Opérateur :", t.get("operateur_nom"))
        row += 1
        meteo_parts = []
        if t.get("meteo_temperature") is not None:
            meteo_parts.append(f"{t['meteo_temperature']}°C")
        if t.get("meteo_vent"):
            meteo_parts.append(f"Vent : {t['meteo_vent']}")
        if t.get("meteo_nebulosite"):
            meteo_parts.append(t["meteo_nebulosite"])
        _row(layout, row, "Météo :",
             " | ".join(meteo_parts) if meteo_parts else None)
        row += 1; _row(layout, row, "EPI utilisés :",
             "Oui" if t.get("epi_utilises") else "Non")
        row += 1
        sig = t.get("signature_nom")
        sig_date = self._fmt_date(t.get("signature_date"))
        _row(layout, row, "Signature :",
             f"{sig} — {sig_date}" if sig else None)
        row += 1
        if t.get("notes"):
            _row(layout, row, "Notes :", t["notes"])
        return widget

    def _toggle(self):
        self._expanded = not self._expanded
        self.detail_widget.setVisible(self._expanded)
        self.lbl_arrow.setText("▼" if self._expanded else "▶")

    @staticmethod
    def _fmt_date(d: str) -> str:
        if not d:
            return "—"
        try:
            from datetime import datetime
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return d


# ─────────────────────────────────────────────────────────────
# Page principale du carnet
# ─────────────────────────────────────────────────────────────
class CarnetPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._role = current_user.get("certiphyto_type")
        self._is_decideur = (
            current_user.get("certiphyto_type") in ("CON", "DESA", "DENSA")
            or current_user.get("role") == "admin")
        self._is_applicateur = (
            peut(current_user, "carnet_ecriture")
            or current_user.get("role") == "admin")
        self._is_ope = self._is_applicateur and not self._is_decideur

        debug.debug(f"[carnet] Init — decideur={self._is_decideur} "
                    f"applicateur={self._is_applicateur} ope={self._is_ope}")
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Carnet de traitements phytosanitaires")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        self.tabs = QTabWidget()

        if self._is_decideur:
            self.tab_decisions = self._build_tab_decisions()
            self.tabs.addTab(self.tab_decisions, "Décisions en attente")

        if self._is_applicateur:
            self.tab_a_faire = self._build_tab_a_faire()
            label = "Traitements en attente" if self._is_decideur else "Traitements à effectuer"
            self.tabs.addTab(self.tab_a_faire, label)

        if peut(self.current_user, "carnet_lecture"):
            self.tab_historique = self._build_tab_historique()
            self.tabs.addTab(self.tab_historique, "Historique")

        root.addWidget(self.tabs, 1)

    def _build_tab_decisions(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QHBoxLayout()
        lbl = QLabel("Créez une décision — l'OPE la recevra et confirmera l'application.")
        lbl.setStyleSheet("color: palette(mid); font-size: 12px;")
        lbl.setWordWrap(True)
        top.addWidget(lbl, 1)
        btn_new = QPushButton("+ Nouvelle décision")
        btn_new.clicked.connect(self._dialog_decision)
        top.addWidget(btn_new)
        layout.addLayout(top)

        filtre = QHBoxLayout()
        self.combo_statut_dec = QComboBox()
        self.combo_statut_dec.addItem("En attente + En cours", ["en_attente", "en_cours"])
        self.combo_statut_dec.addItem("Toutes", None)
        self.combo_statut_dec.addItem("Faites", ["fait"])
        self.combo_statut_dec.addItem("Annulées", ["annule"])
        self.combo_statut_dec.currentIndexChanged.connect(self._charger_decisions)
        filtre.addWidget(QLabel("Statut :"))
        filtre.addWidget(self.combo_statut_dec)
        filtre.addStretch()
        layout.addLayout(filtre)

        self.scroll_decisions = QScrollArea()
        self.scroll_decisions.setWidgetResizable(True)
        self.cont_decisions = QWidget()
        self.lay_decisions = QVBoxLayout(self.cont_decisions)
        self.lay_decisions.setSpacing(0)
        self.lay_decisions.addStretch()
        self.scroll_decisions.setWidget(self.cont_decisions)
        layout.addWidget(self.scroll_decisions, 1)
        return widget

    def _build_tab_a_faire(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        lbl = QLabel("Traitements décidés en attente de votre application.")
        lbl.setStyleSheet("color: palette(mid); font-size: 12px;")
        layout.addWidget(lbl)

        self.scroll_afaire = QScrollArea()
        self.scroll_afaire.setWidgetResizable(True)
        self.cont_afaire = QWidget()
        self.lay_afaire = QVBoxLayout(self.cont_afaire)
        self.lay_afaire.setSpacing(4)
        self.lay_afaire.addStretch()
        self.scroll_afaire.setWidget(self.cont_afaire)
        layout.addWidget(self.scroll_afaire, 1)
        return widget

    def _build_tab_historique(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        filtre = QHBoxLayout()
        self.inp_histo_debut = QDateEdit(QDate.currentDate().addMonths(-3))
        self.inp_histo_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_histo_debut.setCalendarPopup(True)
        self.inp_histo_debut.dateChanged.connect(self._charger_historique)
        self.inp_histo_fin = QDateEdit(QDate.currentDate())
        self.inp_histo_fin.setDisplayFormat("dd/MM/yyyy")
        self.inp_histo_fin.setCalendarPopup(True)
        self.inp_histo_fin.dateChanged.connect(self._charger_historique)
        self.combo_histo_culture = QComboBox()
        self.combo_histo_culture.addItem("Toutes cultures", None)
        self.combo_histo_culture.currentIndexChanged.connect(self._charger_historique)

        filtre.addWidget(QLabel("Du :")); filtre.addWidget(self.inp_histo_debut)
        filtre.addWidget(QLabel("au :")); filtre.addWidget(self.inp_histo_fin)
        filtre.addWidget(QLabel("Culture :")); filtre.addWidget(self.combo_histo_culture)
        filtre.addStretch()

        self.btn_export_bio = QPushButton("📄 Export PDF contrôleur")
        self.btn_export_bio.clicked.connect(self._exporter_pdf_controleur)
        filtre.addWidget(self.btn_export_bio)

        layout.addLayout(filtre)

        self.scroll_histo = QScrollArea()
        self.scroll_histo.setWidgetResizable(True)
        self.cont_histo = QWidget()
        self.lay_histo = QVBoxLayout(self.cont_histo)
        self.lay_histo.setSpacing(0)
        self.lay_histo.addStretch()
        self.scroll_histo.setWidget(self.cont_histo)
        layout.addWidget(self.scroll_histo, 1)
        return widget

    # ──────────────────────────────────────────
    # Chargement global
    # ──────────────────────────────────────────
    def _charger(self):
        debug.debug("[carnet] _charger()")
        if self._is_decideur:
            self._charger_decisions()
        if self._is_applicateur:
            self._charger_a_faire()
        if peut(self.current_user, "carnet_lecture"):
            self._charger_cultures_filtre()
            self._charger_historique()

    def _charger_decisions(self):
        statuts = self.combo_statut_dec.currentData()
        debug.debug(f"[carnet] _charger_decisions() statuts={statuts}")
        try:
            conn = get_connection()
            cur = conn.cursor()
            sql = """
                SELECT d.id, d.statut,
                       p.nom_commercial, p.num_amm,
                       parc.nom AS parcelle_nom,
                       d.culture, d.bio_agresseur,
                       d.dose_prescrite, d.unite,
                       d.date_prevue, d.notes_decideur,
                       u.prenom || ' ' || u.nom AS decideur_nom
                FROM ppp_decisions d
                JOIN ppp_produits p  ON p.id  = d.produit_id
                LEFT JOIN parcelles parc ON parc.id = d.parcelle_id
                JOIN users u         ON u.id  = d.decideur_id
                WHERE d.decideur_id = ?
            """
            params = [self.current_user["id"]]
            if statuts:
                placeholders = ",".join("?" * len(statuts))
                sql += f" AND d.statut IN ({placeholders})"
                params.extend(statuts)
            sql += " ORDER BY d.date_prevue ASC, d.created_at DESC"
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            debug.debug(f"[carnet] {len(rows)} décision(s) chargée(s)")

            self._vider_layout(self.lay_decisions)
            if not rows:
                lbl = QLabel("Aucune décision.")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: palette(mid); padding: 20px;")
                self.lay_decisions.insertWidget(0, lbl)
            else:
                for i, row in enumerate(rows):
                    row["statut_decision"] = row["statut"]
                    row["operateur_nom"] = None
                    card = CarteDecision(
                        decision=row,
                        current_user=self.current_user,
                        on_annuler=lambda did: self._annuler_decision(did),
                        on_refresh=self._charger,
                    )
                    self.lay_decisions.insertWidget(i, card)
        except Exception as e:
            debug.debug(f"[carnet] Erreur _charger_decisions : {e}")
            traceback.print_exc()

    def _charger_a_faire(self):
        debug.debug("[carnet] _charger_a_faire()")
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT d.id, d.statut,
                       p.nom_commercial, p.num_amm, p.substance_active,
                       parc.nom AS parcelle_nom,
                       d.culture, d.bio_agresseur,
                       d.dose_prescrite, d.unite,
                       d.date_prevue, d.notes_decideur,
                       ud.prenom || ' ' || ud.nom AS decideur_nom,
                       d.produit_id, d.parcelle_id
                FROM ppp_decisions d
                JOIN ppp_produits p  ON p.id  = d.produit_id
                LEFT JOIN parcelles parc ON parc.id = d.parcelle_id
                JOIN users ud        ON ud.id = d.decideur_id
                WHERE d.statut IN ('en_attente', 'en_cours')
                ORDER BY d.date_prevue ASC
            """)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            debug.debug(f"[carnet] {len(rows)} traitement(s) à faire")

            self._vider_layout(self.lay_afaire)
            if not rows:
                lbl = QLabel("Aucun traitement en attente.")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: palette(mid); padding: 20px;")
                self.lay_afaire.insertWidget(0, lbl)
            else:
                for i, row in enumerate(rows):
                    row["statut_decision"] = row["statut"]
                    card = CarteAFaire(
                        decision=row,
                        current_user=self.current_user,
                        on_refresh=self._charger,
                    )
                    self.lay_afaire.insertWidget(i, card)
        except Exception as e:
            debug.debug(f"[carnet] Erreur _charger_a_faire : {e}")
            traceback.print_exc()

    def _charger_cultures_filtre(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT culture FROM ppp_traitements
                WHERE culture IS NOT NULL ORDER BY culture
            """)
            self.combo_histo_culture.blockSignals(True)
            self.combo_histo_culture.clear()
            self.combo_histo_culture.addItem("Toutes cultures", None)
            for row in cur.fetchall():
                self.combo_histo_culture.addItem(row[0], row[0])
            self.combo_histo_culture.blockSignals(False)
            cur.close()
        except Exception as e:
            debug.debug(f"[carnet] Erreur _charger_cultures_filtre : {e}")
            traceback.print_exc()

    def _charger_historique(self):
        date_debut = self.inp_histo_debut.date().toString("yyyy-MM-dd")
        date_fin   = self.inp_histo_fin.date().toString("yyyy-MM-dd")
        culture    = self.combo_histo_culture.currentData()
        debug.debug(f"[carnet] _charger_historique() {date_debut}→{date_fin} culture={culture}")
        try:
            conn = get_connection()
            cur = conn.cursor()
            sql = """
                SELECT t.id,
                       p.nom_commercial, p.num_amm, p.substance_active,
                       t.culture, t.bio_agresseur,
                       parc.nom AS parcelle_nom,
                       t.dose_appliquee, t.unite, t.surface_traitee_ha,
                       t.date_traitement,
                       t.meteo_temperature, t.meteo_vent, t.meteo_nebulosite,
                       t.epi_utilises,
                       t.signature_nom, t.signature_date,
                       t.notes,
                       uo.prenom || ' ' || uo.nom AS operateur_nom,
                       COALESCE(ud.prenom || ' ' || ud.nom, '—') AS decideur_nom,
                       d.statut AS statut_decision
                FROM ppp_traitements t
                JOIN ppp_produits p   ON p.id  = t.produit_id
                LEFT JOIN parcelles parc ON parc.id = t.parcelle_id
                JOIN users uo         ON uo.id = t.operateur_id
                LEFT JOIN ppp_decisions d  ON d.id  = t.decision_id
                LEFT JOIN users ud    ON ud.id = d.decideur_id
                WHERE t.date_traitement BETWEEN ? AND ?
            """
            params = [date_debut, date_fin]
            if culture:
                sql += " AND t.culture = ?"
                params.append(culture)
            sql += " ORDER BY t.date_traitement DESC"
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()
            debug.debug(f"[carnet] {len(rows)} traitement(s) dans l'historique")

            self._vider_layout(self.lay_histo)
            if not rows:
                lbl = QLabel("Aucun traitement sur cette période.")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: palette(mid); padding: 20px;")
                self.lay_histo.insertWidget(0, lbl)
            else:
                for i, row in enumerate(rows):
                    row["statut_decision"] = row.get("statut_decision", "fait")
                    ligne = LigneTraitement(traitement=row)
                    self.lay_histo.insertWidget(i, ligne)
        except Exception as e:
            debug.debug(f"[carnet] Erreur _charger_historique : {e}")
            traceback.print_exc()

    def _exporter_pdf_controleur(self):
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime as _dt

        date_debut = self.inp_histo_debut.date().toString("yyyy-MM-dd")
        date_fin = self.inp_histo_fin.date().toString("yyyy-MM-dd")

        nom_defaut = (f"carnet_traitements_"
                      f"{self.inp_histo_debut.date().toString('yyyyMMdd')}_"
                      f"{self.inp_histo_fin.date().toString('yyyyMMdd')}.pdf")
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter le carnet pour le contrôleur",
            nom_defaut, "Fichiers PDF (*.pdf)")
        if not chemin:
            return

        try:
            from ppp.export_bio import exporter_carnet_bio_pdf
            exporter_carnet_bio_pdf(date_debut, date_fin, chemin)
            QMessageBox.information(self, "Export réussi",
                f"Le carnet a été exporté :\n{chemin}")
        except Exception as e:
            debug.debug(f"[carnet] Erreur export PDF : {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur d'export", str(e))

    def _annuler_decision(self, decision_id: int):
        debug.debug(f"[carnet] _annuler_decision({decision_id})")
        rep = QMessageBox.question(self, "Annuler",
            "Annuler cette décision de traitement ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE ppp_decisions SET statut = 'annule' WHERE id = ?",
                    (decision_id,))
                conn.commit()
                cur.close()
                debug.debug(f"[carnet] Décision {decision_id} annulée en BDD")
                self._charger()
            except Exception as e:
                debug.debug(f"[carnet] Erreur annulation : {e}")
                traceback.print_exc()

    def _dialog_decision(self):
        debug.debug("[carnet] Ouverture DialogDecision")
        dlg = DialogDecision(current_user=self.current_user, parent=self)
        if dlg.exec() == QDialog.Accepted:
            debug.debug("[carnet] DialogDecision accepté → rechargement")
            self._charger()

    def pre_remplir(self, produit_id: int, usage_id: int,
                    culture: str, bio_agresseur: str):
        debug.debug(f"[carnet] pre_remplir produit={produit_id} culture={culture}")
        if not self._is_decideur and not self._is_applicateur:
            QMessageBox.information(self, "Accès limité",
                "Vous n'avez pas les droits pour créer un traitement.")
            return
        if self._is_decideur:
            _pre_remplir_carnet(self, produit_id, usage_id, culture, bio_agresseur)
        else:
            QMessageBox.information(self, "Accès limité",
                "Seuls les CON, DESA, DENSA et admins peuvent créer une décision.")

    @staticmethod
    def _vider_layout(layout: QVBoxLayout):
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()
        QApplication.processEvents()


# ─────────────────────────────────────────────────────────────
# Carte décision (vue décideur)
# ─────────────────────────────────────────────────────────────
class CarteDecision(QFrame):
    def __init__(self, decision: dict, current_user: dict,
                 on_annuler, on_refresh, parent=None):
        super().__init__(parent)
        self.decision = decision
        self.current_user = current_user
        self.on_annuler = on_annuler
        self.on_refresh = on_refresh
        self._expanded = False
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("QFrame { margin-bottom: 4px; }")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        d = self.decision
        statut = d.get("statut", "en_attente")
        couleurs = {"en_attente": "#F5A623", "en_cours": "#4A90E2",
                    "fait": "#7ED321", "annule": "#D0021B"}
        labels_statut = {"en_attente": "En attente", "en_cours": "En cours",
                         "fait": "Fait", "annule": "Annulé"}

        header = QHBoxLayout()
        badge = QLabel(f" {labels_statut.get(statut, statut)} ")
        badge.setStyleSheet(
            f"background: {couleurs.get(statut,'#888')}; color: white; "
            f"border-radius: 3px; padding: 2px 6px; font-size: 11px;")
        header.addWidget(badge)

        date_txt = self._fmt_date(d.get("date_prevue")) if d.get("date_prevue") else "Sans date"
        lbl_date = QLabel(date_txt)
        lbl_date.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_date)

        lbl_produit = QLabel(d.get("nom_commercial", "—"))
        lbl_produit.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_produit, 1)

        lbl_parc = QLabel(d.get("parcelle_nom") or "—")
        lbl_parc.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_parc)

        lbl_culture = QLabel(d.get("culture", "—"))
        lbl_culture.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_culture)

        self.lbl_arrow = QLabel("▶")
        self.lbl_arrow.setFixedWidth(16)
        header.addWidget(self.lbl_arrow)

        header_w = QWidget()
        header_w.setLayout(header)
        header_w.setCursor(Qt.PointingHandCursor)
        header_w.mousePressEvent = lambda e: self._toggle()
        layout.addWidget(header_w)

        self.detail_w = self._build_detail()
        self.detail_w.setVisible(False)
        layout.addWidget(self.detail_w)

    def _build_detail(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: palette(window);")
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        d = self.decision
        grid = QGridLayout()
        grid.setSpacing(6)

        infos = [
            ("Produit :", f"{d.get('nom_commercial','—')} — AMM {d.get('num_amm','—')}"),
            ("Parcelle :", d.get("parcelle_nom")),
            ("Culture :", d.get("culture")),
            ("Bio-agresseur :", d.get("bio_agresseur")),
            ("Dose prescrite :", f"{d.get('dose_prescrite','—')} {d.get('unite','')}"),
            ("Date prévue :", self._fmt_date(d.get("date_prevue"))),
            ("Décideur :", d.get("decideur_nom")),
            ("Notes :", d.get("notes_decideur")),
        ]
        for i, (lbl_txt, val_txt) in enumerate(infos):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
            val = QLabel(str(val_txt) if val_txt else "—")
            val.setWordWrap(True)
            val.setStyleSheet("font-size: 12px;")
            grid.addWidget(lbl, i, 0)
            grid.addWidget(val, i, 1)
        lay.addLayout(grid)

        if d.get("statut") in ("en_attente", "en_cours"):
            btns = QHBoxLayout()
            btn_annuler = QPushButton("Annuler")
            btn_annuler.clicked.connect(lambda: self.on_annuler(d["id"]))
            btns.addStretch()
            btns.addWidget(btn_annuler)
            lay.addLayout(btns)

        return widget

    def _toggle(self):
        self._expanded = not self._expanded
        self.detail_w.setVisible(self._expanded)
        self.lbl_arrow.setText("▼" if self._expanded else "▶")

    @staticmethod
    def _fmt_date(d: str) -> str:
        if not d:
            return "—"
        try:
            from datetime import datetime
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return d


# ─────────────────────────────────────────────────────────────
# Carte "à faire" (vue OPE/applicateur)
# ─────────────────────────────────────────────────────────────
class CarteAFaire(QFrame):
    def __init__(self, decision: dict, current_user: dict,
                 on_refresh, parent=None):
        super().__init__(parent)
        self.decision = decision
        self.current_user = current_user
        self.on_refresh = on_refresh
        self.setFrameShape(QFrame.NoFrame)
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#FEF3C7"))
        self.setPalette(pal)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        d = self.decision
        titre = QLabel(
            f"{d.get('nom_commercial','—')} — {d.get('culture','—')} "
            f"/ {d.get('bio_agresseur','—')}")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        titre.setFont(f)
        layout.addWidget(titre)

        infos = QLabel(
            f"Parcelle : {d.get('parcelle_nom') or '—'}  |  "
            f"Dose : {d.get('dose_prescrite','—')} {d.get('unite','')}  |  "
            f"Date prévue : {self._fmt_date(d.get('date_prevue'))}  |  "
            f"Décidé par : {d.get('decideur_nom','—')}")
        infos.setStyleSheet("font-size: 12px; color: #78716c;")
        infos.setWordWrap(True)
        layout.addWidget(infos)

        if d.get("notes_decideur"):
            lbl_notes = QLabel(f"Note décideur : {d['notes_decideur']}")
            lbl_notes.setStyleSheet("font-size: 12px; font-style: italic; color: #44403c;")
            lbl_notes.setWordWrap(True)
            layout.addWidget(lbl_notes)

        btn = QPushButton("Confirmer l'application →")
        btn.setFixedHeight(36)
        btn.setStyleSheet("""
            QPushButton { background: #7ED321; color: white;
                border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background: #6ABE10; }
        """)
        btn.clicked.connect(self._confirmer)
        layout.addWidget(btn)

    def _confirmer(self):
        debug.debug(f"[carnet] Confirmer application décision {self.decision.get('id')}")
        dlg = DialogConfirmerTraitement(
            decision=self.decision,
            current_user=self.current_user,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            debug.debug("[carnet] Application confirmée → rechargement")
            self.on_refresh()

    @staticmethod
    def _fmt_date(d: str) -> str:
        if not d:
            return "—"
        try:
            from datetime import datetime
            return datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return d


# ─────────────────────────────────────────────────────────────
# Dialog : Nouvelle décision (CON/DESA/DENSA)
# ─────────────────────────────────────────────────────────────
class DialogDecision(QDialog):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setWindowTitle("Nouvelle décision de traitement")
        self.setMinimumWidth(520)
        self._peut_appliquer = (
            peut(current_user, "carnet_ecriture")
            or current_user.get("role") == "admin")
        self.prod_info = {}
        debug.debug(f"[DialogDecision] Init peut_appliquer={self._peut_appliquer}")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_amm = QLineEdit()
        self.inp_amm.setPlaceholderText("N° AMM ou nom du produit...")
        self.inp_amm.textChanged.connect(self._rechercher_produit)
        form.addRow("Produit * (AMM/nom) :", self.inp_amm)

        self.combo_produit = QComboBox()
        self.combo_produit.addItem("— Résultats de recherche —", None)
        form.addRow("Sélectionner :", self.combo_produit)

        # Le combo stocke le culture_parcelle_id (cp.id), pas le parcelle_id
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("— Sélectionnez —", None)
        form.addRow("Parcelle / Culture *", self.combo_parcelle)

        self.inp_culture = QLineEdit()
        self.inp_culture.setPlaceholderText("Culture concernée")
        form.addRow("Culture *", self.inp_culture)

        self.inp_bio_agr = QLineEdit()
        self.inp_bio_agr.setPlaceholderText("Bio-agresseur ciblé")
        form.addRow("Bio-agresseur", self.inp_bio_agr)

        dose_w = QWidget()
        dose_lay = QHBoxLayout(dose_w)
        dose_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_dose = QDoubleSpinBox()
        self.inp_dose.setRange(0.01, 9999)
        self.inp_dose.setDecimals(2)
        self.inp_unite = QLineEdit("L/ha")
        self.inp_unite.setFixedWidth(60)
        dose_lay.addWidget(self.inp_dose)
        dose_lay.addWidget(self.inp_unite)
        form.addRow("Dose prescrite *", dose_w)

        self.inp_date = QDateEdit(QDate.currentDate().addDays(1))
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date prévue", self.inp_date)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        self.inp_notes.setPlaceholderText("Instructions pour l'opérateur...")
        form.addRow("Notes", self.inp_notes)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        form.addRow(self.lbl_err)

        layout.addLayout(form)

        if self._peut_appliquer:
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            layout.addWidget(sep)
            self.chk_appliquer_maintenant = QCheckBox(
                "Appliquer immédiatement ce traitement (je suis l'opérateur)")
            self.chk_appliquer_maintenant.setStyleSheet("font-weight: bold;")
            layout.addWidget(self.chk_appliquer_maintenant)
            debug.debug("[DialogDecision] Checkbox 'appliquer maintenant' ajoutée")

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._charger_parcelles()

    def _charger_parcelles(self):
        """Charge une entrée par CULTURE (pas par parcelle) afin de
        pouvoir distinguer Abricot et Tomate sur une même parcelle.
        Stocke cp.id (culture_parcelle_id) comme data du combo."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT cp.id, p.id AS parcelle_id, p.nom, cp.espece, cp.variete
                FROM parcelles p
                JOIN cultures_parcelle cp ON cp.parcelle_id = p.id
                WHERE p.actif = 1 AND cp.actif = 1
                  AND cp.categorie IN ('maraichage', 'arbo')
                ORDER BY p.nom, cp.espece
            """)
            for row in cur.fetchall():
                culture_id, parcelle_id, nom_parcelle, espece, variete = row
                label = f"{nom_parcelle} — {espece or '—'}"
                if variete:
                    label += f" ({variete})"
                self.combo_parcelle.addItem(label, culture_id)
                idx = self.combo_parcelle.count() - 1
                self.combo_parcelle.setItemData(idx, espece, Qt.UserRole + 1)
                self.combo_parcelle.setItemData(idx, parcelle_id, Qt.UserRole + 2)
            cur.close()
            debug.debug(f"[DialogDecision] {self.combo_parcelle.count()-1} culture(s) chargée(s)")
        except Exception as e:
            debug.debug(f"[DialogDecision] Erreur parcelles : {e}")
            traceback.print_exc()
        self.combo_parcelle.currentIndexChanged.connect(self._on_parcelle_changed)

    def _on_parcelle_changed(self):
        idx = self.combo_parcelle.currentIndex()
        culture = self.combo_parcelle.itemData(idx, Qt.UserRole + 1)
        if culture:
            self.inp_culture.setText(culture)

    def _rechercher_produit(self):
        terme = self.inp_amm.text().strip().lower()
        if len(terme) < 2:
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nom_commercial, num_amm FROM ppp_produits
                WHERE LOWER(nom_commercial) LIKE ? OR LOWER(num_amm) LIKE ?
                ORDER BY nom_commercial LIMIT 20
            """, [f"%{terme}%", f"%{terme}%"])
            rows = cur.fetchall()
            cur.close()
            self.combo_produit.blockSignals(True)
            self.combo_produit.clear()
            self.combo_produit.addItem("— Sélectionnez —", None)
            for row in rows:
                self.combo_produit.addItem(f"{row[1]} (AMM {row[2]})", row[0])
            self.combo_produit.blockSignals(False)
            debug.debug(f"[DialogDecision] {len(rows)} produit(s) trouvé(s) pour '{terme}'")
        except Exception as e:
            debug.debug(f"[DialogDecision] Erreur recherche produit : {e}")
            traceback.print_exc()

    def _valider(self):
        produit_id          = self.combo_produit.currentData()
        culture_parcelle_id = self.combo_parcelle.currentData()
        culture             = self.inp_culture.text().strip()
        dose                = self.inp_dose.value()

        debug.debug(f"[DialogDecision] _valider produit={produit_id} "
                    f"culture_parcelle={culture_parcelle_id} culture={culture} dose={dose}")

        if not produit_id:
            self.lbl_err.setText("Sélectionnez un produit."); return
        if not culture_parcelle_id:
            self.lbl_err.setText("Sélectionnez une parcelle."); return
        if not culture:
            self.lbl_err.setText("Renseignez la culture."); return
        if dose <= 0:
            self.lbl_err.setText("Dose invalide."); return

        idx = self.combo_parcelle.currentIndex()
        parcelle_id = self.combo_parcelle.itemData(idx, Qt.UserRole + 2)

        bio_agr = self.inp_bio_agr.text().strip() or None
        unite   = self.inp_unite.text().strip() or "L/ha"
        date_p  = self.inp_date.date().toString("yyyy-MM-dd")
        notes   = self.inp_notes.toPlainText().strip() or None

        from db import produit_homologue_pour_culture
        if not produit_homologue_pour_culture(produit_id, culture_parcelle_id):
            debug.debug("[DialogDecision] Produit non homologué pour cette culture")
            rep = QMessageBox.warning(
                self, "Produit non homologué pour cette culture",
                "Aucune catégorie PPP de cette culture ne correspond "
                "aux usages homologués de ce produit.\n\nContinuer quand même ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep == QMessageBox.No:
                return

        from db import est_exploitation_bio
        if est_exploitation_bio():
            cur_bio = get_connection().cursor()
            cur_bio.execute(
                "SELECT bio_compatible FROM ppp_produits WHERE id=?",
                (produit_id,))
            row_bio = cur_bio.fetchone()
            cur_bio.close()
            if row_bio and not row_bio[0]:
                rep = QMessageBox.warning(
                    self, "⚠ Produit non autorisé en agriculture biologique",
                    "Votre exploitation est déclarée en agriculture biologique, "
                    "mais ce produit n'est PAS certifié bio-compatible.\n\n"
                    "Réglementairement, son usage peut être toléré uniquement si "
                    "sa substance active figure sur la liste des dérogations "
                    "(annexe II du règlement bio / « dérogations 120 jours »), "
                    "et SOUS RÉSERVE d'en informer préalablement votre organisme "
                    "certificateur en précisant les parcelles concernées.\n\n"
                    "Confirmer malgré tout ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if rep == QMessageBox.No:
                    return

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ppp_decisions
                (decideur_id, produit_id, parcelle_id, culture,
                 bio_agresseur, dose_prescrite, unite, date_prevue, notes_decideur)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.current_user["id"], produit_id, parcelle_id,
                  culture, bio_agr, dose, unite, date_p, notes))
            conn.commit()
            decision_id = cur.lastrowid
            cur.close()
            debug.debug(f"[DialogDecision] Décision {decision_id} créée")

            appliquer = (
                self._peut_appliquer
                and hasattr(self, "chk_appliquer_maintenant")
                and self.chk_appliquer_maintenant.isChecked())
            debug.debug(f"[DialogDecision] appliquer_maintenant={appliquer}")

            if appliquer:
                conn2 = get_connection()
                cur2 = conn2.cursor()
                cur2.execute(
                    "SELECT nom_commercial, num_amm, substance_active "
                    "FROM ppp_produits WHERE id = ?", (produit_id,))
                prod_row = cur2.fetchone()
                cur2.close()

                decision_dict = {
                    "id":               decision_id,
                    "nom_commercial":   prod_row[0] if prod_row else "—",
                    "num_amm":          prod_row[1] if prod_row else "—",
                    "substance_active": prod_row[2] if prod_row else None,
                    "parcelle_nom":     self.combo_parcelle.currentText().split(" — ")[0],
                    "culture":          culture,
                    "bio_agresseur":    bio_agr,
                    "dose_prescrite":   dose,
                    "unite":            unite,
                    "date_prevue":      date_p,
                    "notes_decideur":   notes,
                    "decideur_nom":     (self.current_user.get("prenom", "") + " " +
                                        self.current_user.get("nom", "")).strip(),
                    "produit_id":       produit_id,
                    "parcelle_id":      parcelle_id,
                }
                debug.debug(f"[DialogDecision] Ouverture DialogConfirmerTraitement")
                self.accept()
                dlg_appli = DialogConfirmerTraitement(
                    decision=decision_dict,
                    current_user=self.current_user,
                    parent=self.parent())
                dlg_appli.exec()
            else:
                self.accept()

        except Exception as e:
            debug.debug(f"[DialogDecision] Erreur insertion : {e}")
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")


# ─────────────────────────────────────────────────────────────
# Dialog : Confirmer application (OPE)
# ─────────────────────────────────────────────────────────────
class DialogConfirmerTraitement(QDialog):
    def __init__(self, decision: dict, current_user: dict, parent=None):
        super().__init__(parent)
        self.decision = decision
        self.current_user = current_user
        self.setWindowTitle("Confirmer l'application du traitement")
        self.setMinimumWidth(480)
        debug.debug(f"[DialogConfirmerTraitement] Init décision={decision.get('id')}")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        recap = QGroupBox("Décision de traitement")
        recap_lay = QFormLayout(recap)
        d = self.decision
        recap_lay.addRow("Produit :",
            QLabel(f"{d.get('nom_commercial','—')} (AMM {d.get('num_amm','—')})"))
        recap_lay.addRow("Parcelle :", QLabel(d.get("parcelle_nom") or "—"))
        recap_lay.addRow("Culture :", QLabel(d.get("culture", "—")))
        recap_lay.addRow("Bio-agresseur :", QLabel(d.get("bio_agresseur") or "—"))
        recap_lay.addRow("Dose prescrite :",
            QLabel(f"{d.get('dose_prescrite','—')} {d.get('unite','')}"))
        recap_lay.addRow("Décideur :", QLabel(d.get("decideur_nom", "—")))
        layout.addWidget(recap)

        form_group = QGroupBox("Données d'application réelle")
        form = QFormLayout(form_group)
        form.setSpacing(8)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date réelle *", self.inp_date)

        dose_w = QWidget()
        dose_lay = QHBoxLayout(dose_w)
        dose_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_dose = QDoubleSpinBox()
        self.inp_dose.setRange(0.01, 9999)
        self.inp_dose.setDecimals(2)
        self.inp_dose.setValue(d.get("dose_prescrite") or 1)
        self.inp_unite = QLabel(d.get("unite", "L/ha"))
        dose_lay.addWidget(self.inp_dose)
        dose_lay.addWidget(self.inp_unite)
        form.addRow("Dose appliquée *", dose_w)

        self.inp_surface = QDoubleSpinBox()
        self.inp_surface.setRange(0, 9999)
        self.inp_surface.setDecimals(4)
        self.inp_surface.setSuffix(" ha")
        form.addRow("Surface traitée", self.inp_surface)

        meteo_w = QWidget()
        meteo_lay = QHBoxLayout(meteo_w)
        meteo_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_temp = QDoubleSpinBox()
        self.inp_temp.setRange(-20, 50)
        self.inp_temp.setSuffix(" °C")
        self.combo_vent = QComboBox()
        self.combo_vent.addItems(["Calme", "Faible", "Modéré", "Fort"])
        self.combo_neb = QComboBox()
        self.combo_neb.addItems(["Dégagé", "Peu nuageux", "Nuageux", "Couvert"])
        meteo_lay.addWidget(QLabel("T°:")); meteo_lay.addWidget(self.inp_temp)
        meteo_lay.addWidget(QLabel("Vent:")); meteo_lay.addWidget(self.combo_vent)
        meteo_lay.addWidget(QLabel("Neb:")); meteo_lay.addWidget(self.combo_neb)
        form.addRow("Météo", meteo_w)

        self.chk_epi = QCheckBox("EPI portés")
        form.addRow("EPI", self.chk_epi)

        self.inp_sig_nom = QLineEdit()
        self.inp_sig_nom.setText(
            f"{self.current_user.get('prenom','')} {self.current_user.get('nom','')}".strip())
        form.addRow("Signature (nom) *", self.inp_sig_nom)

        self.inp_notes = QLineEdit()
        self.inp_notes.setPlaceholderText("Observations...")
        form.addRow("Notes", self.inp_notes)

        layout.addWidget(form_group)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        layout.addWidget(self.lbl_err)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Confirmer l'application")
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _valider(self):
        sig_nom = self.inp_sig_nom.text().strip()
        if not sig_nom:
            self.lbl_err.setText("La signature est obligatoire.")
            return

        date_app    = self.inp_date.date().toString("yyyy-MM-dd")
        dose        = self.inp_dose.value()
        unite       = self.decision.get("unite", "L/ha")
        surface     = self.inp_surface.value() or None
        temp        = self.inp_temp.value()
        vent        = self.combo_vent.currentText()
        neb         = self.combo_neb.currentText()
        epi         = 1 if self.chk_epi.isChecked() else 0
        notes       = self.inp_notes.text().strip() or None
        decision_id = self.decision["id"]
        produit_id  = self.decision.get("produit_id") or self._get_produit_id()
        parcelle_id = self.decision.get("parcelle_id") or self._get_parcelle_id()

        debug.debug(f"[DialogConfirmerTraitement] _valider décision={decision_id} "
                    f"produit={produit_id} parcelle={parcelle_id}")

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ppp_traitements
                (decision_id, operateur_id, parcelle_id, produit_id,
                 culture, bio_agresseur, dose_appliquee, unite,
                 surface_traitee_ha, date_traitement,
                 meteo_temperature, meteo_vent, meteo_nebulosite,
                 epi_utilises, signature_nom, signature_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (decision_id, self.current_user["id"], parcelle_id,
                  produit_id,
                  self.decision.get("culture"), self.decision.get("bio_agresseur"),
                  dose, unite, surface, date_app,
                  temp, vent, neb, epi, sig_nom, date_app, notes))
            cur.execute(
                "UPDATE ppp_decisions SET statut = 'fait' WHERE id = ?",
                (decision_id,))
            conn.commit()
            cur.close()
            debug.debug(f"[DialogConfirmerTraitement] Traitement enregistré OK")
            self.accept()
        except Exception as e:
            debug.debug(f"[DialogConfirmerTraitement] Erreur : {e}")
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")

    def _get_produit_id(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT produit_id FROM ppp_decisions WHERE id = ?",
                        (self.decision["id"],))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        except Exception:
            return None

    def _get_parcelle_id(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT parcelle_id FROM ppp_decisions WHERE id = ?",
                        (self.decision["id"],))
            row = cur.fetchone()
            cur.close()
            return row[0] if row else None
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────
# Pré-remplissage depuis l'aide à la décision
# ─────────────────────────────────────────────────────────────
def _pre_remplir_carnet(carnet_page, produit_id: int, usage_id: int,
                         culture: str, bio_agresseur: str):
    debug.debug(f"[carnet] _pre_remplir_carnet produit={produit_id} "
                f"usage={usage_id} culture={culture}")
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.nom_commercial, p.num_amm, p.substance_active,
                   u.dose, u.dose_unite, u.dar, u.nma, u.condition_usage
            FROM ppp_produits p
            LEFT JOIN ppp_usages u ON u.id = ?
            WHERE p.id = ?
        """, (usage_id, produit_id))
        row = cur.fetchone()
        cur.close()

        if not row:
            debug.debug("[carnet] Produit introuvable")
            QMessageBox.warning(None, "Produit introuvable",
                "Impossible de récupérer les informations du produit.")
            return

        prod_info = dict(zip(
            ["nom_commercial", "num_amm", "substance_active",
             "dose_max", "dose_unite", "dar", "nma", "condition_usage"],
            row))
        debug.debug(f"[carnet] prod_info={prod_info}")

    except Exception as e:
        debug.debug(f"[carnet] Erreur récup produit : {e}")
        traceback.print_exc()
        return

    if hasattr(carnet_page, "tabs") and hasattr(carnet_page, "tab_decisions"):
        carnet_page.tabs.setCurrentWidget(carnet_page.tab_decisions)

    dlg = DialogDecisionPreRempli(
        produit_id=produit_id,
        usage_id=usage_id,
        culture=culture,
        bio_agresseur=bio_agresseur,
        prod_info=prod_info,
        current_user=carnet_page.current_user,
        parent=carnet_page,
    )
    if dlg.exec() == QDialog.Accepted:
        debug.debug("[carnet] DialogDecisionPreRempli accepté → rechargement")
        carnet_page._charger()


# ─────────────────────────────────────────────────────────────
# Dialog : Nouvelle décision pré-remplie (depuis Aide à la décision)
# ─────────────────────────────────────────────────────────────
class DialogDecisionPreRempli(QDialog):
    def __init__(self, produit_id: int, usage_id: int,
                 culture: str, bio_agresseur: str,
                 prod_info: dict, current_user: dict, parent=None):
        super().__init__(parent)
        self.produit_id    = produit_id
        self.usage_id      = usage_id
        self.culture       = culture
        self.bio_agresseur = bio_agresseur
        self.prod_info     = prod_info
        self.current_user  = current_user
        self.dose_max      = prod_info.get("dose_max")
        self.setWindowTitle("Nouvelle décision de traitement")
        self.setMinimumWidth(520)
        debug.debug(f"[DialogDecisionPreRempli] Init culture={culture} dose_max={self.dose_max}")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        recap = QGroupBox("Produit sélectionné")
        recap_lay = QFormLayout(recap)
        recap_lay.setSpacing(6)
        p = self.prod_info
        recap_lay.addRow("Produit :",
            QLabel(f"{p.get('nom_commercial','—')} (AMM {p.get('num_amm','—')})"))
        recap_lay.addRow("Substance(s) :", QLabel(p.get("substance_active") or "—"))
        recap_lay.addRow("Culture :", QLabel(self.culture or "—"))
        recap_lay.addRow("Bio-agresseur :", QLabel(self.bio_agresseur or "—"))

        dose_max   = self.dose_max
        dose_unite = p.get("dose_unite") or "L/ha"
        if dose_max:
            lbl_dm = QLabel(f"{dose_max} {dose_unite}")
            lbl_dm.setStyleSheet("color: #D97706; font-weight: bold;")
            recap_lay.addRow("Dose max homologuée :", lbl_dm)
        if p.get("dar"):
            recap_lay.addRow("DAR :", QLabel(f"{p['dar']} jour(s)"))
        if p.get("nma"):
            recap_lay.addRow("Nb max applications :", QLabel(str(p["nma"])))
        if p.get("condition_usage"):
            lbl_cond = QLabel(p["condition_usage"])
            lbl_cond.setWordWrap(True)
            lbl_cond.setStyleSheet("font-size: 11px; color: #57534e;")
            recap_lay.addRow("Condition usage :", lbl_cond)
        layout.addWidget(recap)

        form_group = QGroupBox("Décision de traitement")
        form = QFormLayout(form_group)
        form.setSpacing(10)

        # Le combo stocke le culture_parcelle_id (cp.id), pas le parcelle_id
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("— Sélectionnez —", None)
        self._charger_parcelles()
        form.addRow("Parcelle / Culture *", self.combo_parcelle)

        info_filtre = QLabel(
            "ℹ Les cultures marquées ✓ ont une catégorie PPP correspondant "
            "au produit sélectionné.")
        info_filtre.setStyleSheet("color:palette(mid); font-size:10px;")
        info_filtre.setWordWrap(True)
        form.addRow(info_filtre)

        dose_w = QWidget()
        dose_lay = QHBoxLayout(dose_w)
        dose_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_dose = QDoubleSpinBox()
        self.inp_dose.setRange(0.01, 9999)
        self.inp_dose.setDecimals(2)
        if dose_max:
            self.inp_dose.setValue(dose_max)
        self.lbl_unite = QLabel(dose_unite)
        self.lbl_dose_warn = QLabel("")
        self.lbl_dose_warn.setStyleSheet("color: red; font-size: 11px;")
        self.inp_dose.valueChanged.connect(self._verifier_dose)
        dose_lay.addWidget(self.inp_dose)
        dose_lay.addWidget(self.lbl_unite)
        dose_lay.addWidget(self.lbl_dose_warn)
        form.addRow("Dose prescrite *", dose_w)

        self.inp_date = QDateEdit(QDate.currentDate().addDays(1))
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date prévue", self.inp_date)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        self.inp_notes.setPlaceholderText("Instructions pour l'opérateur...")
        form.addRow("Notes", self.inp_notes)

        layout.addWidget(form_group)

        self._peut_appliquer = (
            peut(self.current_user, "carnet_ecriture")
            or self.current_user.get("role") == "admin")
        if self._peut_appliquer:
            sep = QFrame(); sep.setFrameShape(QFrame.HLine)
            layout.addWidget(sep)
            self.chk_appliquer_maintenant = QCheckBox(
                "Appliquer immédiatement ce traitement (je suis l'opérateur)")
            self.chk_appliquer_maintenant.setStyleSheet("font-weight: bold;")
            layout.addWidget(self.chk_appliquer_maintenant)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        layout.addWidget(self.lbl_err)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Créer la décision")
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._verifier_dose()

    def _charger_parcelles(self):
        """Charge une entrée par culture, en mettant en évidence (✓)
        celles dont la catégorie PPP correspond exactement à self.culture."""
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT cp.id, p.id AS parcelle_id, p.nom, cp.espece, cp.variete
                FROM parcelles p
                JOIN cultures_parcelle cp ON cp.parcelle_id = p.id
                WHERE p.actif = 1 AND cp.actif = 1
                  AND cp.categorie IN ('maraichage', 'arbo')
                ORDER BY p.nom, cp.espece
            """)
            rows = cur.fetchall()
            cur.close()

            from db import get_categories_ppp_culture

            premiere_compatible = None
            for row in rows:
                culture_id, parcelle_id, nom_parcelle, espece, variete = row
                cats_ppp = get_categories_ppp_culture(culture_id)
                compatible = any(
                    c.lower() == (self.culture or "").lower() for c in cats_ppp)

                icone = "✓ " if compatible else ""
                label = f"{icone}{nom_parcelle} — {espece or '—'}"
                if variete:
                    label += f" ({variete})"
                self.combo_parcelle.addItem(label, culture_id)
                idx = self.combo_parcelle.count() - 1
                self.combo_parcelle.setItemData(idx, espece, Qt.UserRole + 1)
                self.combo_parcelle.setItemData(idx, parcelle_id, Qt.UserRole + 2)

                if compatible and premiere_compatible is None:
                    premiere_compatible = idx

            if premiere_compatible is not None:
                self.combo_parcelle.setCurrentIndex(premiere_compatible)
        except Exception as e:
            debug.debug(f"[DialogDecisionPreRempli] Erreur parcelles : {e}")
            traceback.print_exc()

    def _verifier_dose(self):
        dose = self.inp_dose.value()
        if self.dose_max and dose > self.dose_max:
            self.lbl_dose_warn.setText(f"⚠ Dépasse la dose max ({self.dose_max})")
            pal = self.inp_dose.palette()
            pal.setColor(QPalette.Base, QColor("#FEE2E2"))  # rouge
            self.inp_dose.setPalette(pal)
        else:
            self.lbl_dose_warn.setText("")
            pal = self.inp_dose.palette()
            pal.setColor(QPalette.Base, self.style().standardPalette().color(QPalette.Base))
            self.inp_dose.setPalette(pal)

    def _valider(self):
        culture_parcelle_id = self.combo_parcelle.currentData()
        dose = self.inp_dose.value()
        debug.debug(f"[DialogDecisionPreRempli] _valider culture_parcelle={culture_parcelle_id} dose={dose}")

        if not culture_parcelle_id:
            self.lbl_err.setText("Sélectionnez une parcelle.")
            return

        idx = self.combo_parcelle.currentIndex()
        parcelle_id = self.combo_parcelle.itemData(idx, Qt.UserRole + 2)

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM ppp_usages
                WHERE produit_id = ? AND culture = ? AND bio_agresseur = ?
            """, (self.produit_id, self.culture or "", self.bio_agresseur or ""))
            homol_count = cur.fetchone()[0]
            cur.close()
        except Exception as e:
            debug.debug(f"[DialogDecisionPreRempli] Erreur homol : {e}")
            homol_count = 0

        debug.debug(f"[DialogDecisionPreRempli] homol_count={homol_count}")

        if homol_count == 0:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    SELECT COUNT(*) FROM ppp_usages
                    WHERE produit_id = ? AND culture = ?
                """, (self.produit_id, self.culture or ""))
                culture_count = cur.fetchone()[0]
                cur.close()
            except Exception:
                culture_count = 0

            if culture_count == 0:
                QMessageBox.critical(self, "Produit non homologué",
                    f"Ce produit n'est pas homologué pour la culture "
                    f"« {self.culture} ».\nLa décision ne peut pas être créée.")
                return
            else:
                rep = QMessageBox.warning(self, "Bio-agresseur non confirmé",
                    f"Ce produit est homologué sur « {self.culture} » "
                    f"mais l'usage exact pour « {self.bio_agresseur} » "
                    f"n'est pas trouvé.\nContinuer quand même ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if rep == QMessageBox.No:
                    return

        from db import produit_homologue_pour_culture
        if not produit_homologue_pour_culture(self.produit_id, culture_parcelle_id):
            debug.debug("[DialogDecisionPreRempli] Culture non compatible PPP")
            rep = QMessageBox.warning(self, "Culture non compatible",
                "Aucune catégorie PPP de cette culture ne correspond "
                "aux usages homologués.\n\nContinuer quand même ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep == QMessageBox.No:
                return

        from db import est_exploitation_bio
        if est_exploitation_bio():
            cur_bio = get_connection().cursor()
            cur_bio.execute(
                "SELECT bio_compatible FROM ppp_produits WHERE id=?",
                (self.produit_id,))
            row_bio = cur_bio.fetchone()
            cur_bio.close()
            if row_bio and not row_bio[0]:
                rep = QMessageBox.warning(
                    self, "⚠ Produit non autorisé en agriculture biologique",
                    "Votre exploitation est déclarée en agriculture biologique, "
                    "mais ce produit n'est PAS certifié bio-compatible.\n\n"
                    "Réglementairement, son usage peut être toléré uniquement si "
                    "sa substance active figure sur la liste des dérogations "
                    "(annexe II du règlement bio / « dérogations 120 jours »), "
                    "et SOUS RÉSERVE d'en informer préalablement votre organisme "
                    "certificateur en précisant les parcelles concernées.\n\n"
                    "Confirmer malgré tout ?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if rep == QMessageBox.No:
                    return

        if self.dose_max and dose > self.dose_max:
            rep = QMessageBox.warning(self, "Dose supérieure au maximum",
                f"La dose saisie ({dose}) dépasse le maximum homologué "
                f"({self.dose_max} {self.prod_info.get('dose_unite','')}).\n\n"
                f"Continuer quand même ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if rep == QMessageBox.No:
                return

        unite  = self.prod_info.get("dose_unite") or "L/ha"
        date_p = self.inp_date.date().toString("yyyy-MM-dd")
        notes  = self.inp_notes.toPlainText().strip() or None

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ppp_decisions
                (decideur_id, produit_id, usage_id, parcelle_id, culture,
                 bio_agresseur, dose_prescrite, unite, date_prevue, notes_decideur)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.current_user["id"], self.produit_id, self.usage_id,
                  parcelle_id, self.culture, self.bio_agresseur,
                  dose, unite, date_p, notes))
            conn.commit()
            decision_id = cur.lastrowid
            cur.close()
            debug.debug(f"[DialogDecisionPreRempli] Décision {decision_id} créée")

            appliquer = (
                self._peut_appliquer
                and hasattr(self, "chk_appliquer_maintenant")
                and self.chk_appliquer_maintenant.isChecked())
            debug.debug(f"[DialogDecisionPreRempli] appliquer={appliquer}")

            if appliquer:
                self.accept()
                decision_dict = {
                    "id":               decision_id,
                    "nom_commercial":   self.prod_info.get("nom_commercial"),
                    "num_amm":          self.prod_info.get("num_amm"),
                    "substance_active": self.prod_info.get("substance_active"),
                    "parcelle_nom":     self.combo_parcelle.currentText().split(" — ")[0],
                    "culture":          self.culture,
                    "bio_agresseur":    self.bio_agresseur,
                    "dose_prescrite":   dose,
                    "unite":            unite,
                    "date_prevue":      date_p,
                    "notes_decideur":   notes,
                    "decideur_nom":     (self.current_user.get("prenom", "") + " " +
                                        self.current_user.get("nom", "")).strip(),
                    "produit_id":       self.produit_id,
                    "parcelle_id":      parcelle_id,
                }
                dlg_appli = DialogConfirmerTraitement(
                    decision=decision_dict,
                    current_user=self.current_user,
                    parent=self.parent())
                dlg_appli.exec()
            else:
                self.accept()

        except Exception as e:
            debug.debug(f"[DialogDecisionPreRempli] Erreur insertion : {e}")
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")