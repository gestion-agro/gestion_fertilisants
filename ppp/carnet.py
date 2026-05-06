# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
from views.login import peut
import traceback


# ─────────────────────────────────────────────────────────────
# Widget ligne dépliable pour le carnet
# ─────────────────────────────────────────────────────────────
class LigneTraitement(QWidget):
    """
    Ligne cliquable qui affiche un résumé et se déplie
    pour montrer tous les détails du traitement.
    """
    def __init__(self, traitement: dict, parent=None):
        super().__init__(parent)
        self.traitement = traitement
        self._expanded = False
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget { border-bottom: 1px solid palette(mid); }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)

        # ── Ligne résumé (toujours visible) ──
        header = QHBoxLayout()
        header.setSpacing(12)

        # Statut coloré
        statut = self.traitement.get("statut_decision", "fait")
        couleurs = {
            "en_attente": "#F5A623",
            "en_cours":   "#4A90E2",
            "fait":       "#7ED321",
            "annule":     "#D0021B",
        }
        lbl_statut = QLabel("●")
        lbl_statut.setStyleSheet(
            f"color: {couleurs.get(statut, '#888')}; font-size: 16px;")
        lbl_statut.setFixedWidth(20)
        header.addWidget(lbl_statut)

        # Date
        date = self.traitement.get("date_traitement") or \
               self.traitement.get("date_prevue") or "—"
        lbl_date = QLabel(self._fmt_date(date))
        lbl_date.setFixedWidth(90)
        lbl_date.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_date)

        # Produit
        lbl_produit = QLabel(self.traitement.get("nom_commercial", "—"))
        lbl_produit.setStyleSheet("font-weight: bold;")
        header.addWidget(lbl_produit, 2)

        # Culture
        lbl_culture = QLabel(self.traitement.get("culture", "—"))
        lbl_culture.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_culture, 1)

        # Parcelle
        lbl_parcelle = QLabel(self.traitement.get("parcelle_nom") or "—")
        lbl_parcelle.setStyleSheet("color: palette(mid);")
        header.addWidget(lbl_parcelle, 1)

        # Bio-agresseur
        lbl_bio = QLabel(self.traitement.get("bio_agresseur") or "—")
        lbl_bio.setStyleSheet("color: palette(mid); font-size: 12px;")
        header.addWidget(lbl_bio, 1)

        # Opérateur
        ope = self.traitement.get("operateur_nom") or "—"
        lbl_ope = QLabel(f"OPE: {ope}")
        lbl_ope.setStyleSheet("font-size: 11px; color: palette(mid);")
        header.addWidget(lbl_ope)

        # Flèche dépliage
        self.lbl_arrow = QLabel("▶")
        self.lbl_arrow.setFixedWidth(16)
        header.addWidget(self.lbl_arrow)

        header_widget = QWidget()
        header_widget.setLayout(header)
        header_widget.setCursor(Qt.PointingHandCursor)
        header_widget.mousePressEvent = lambda e: self._toggle()
        layout.addWidget(header_widget)

        # ── Détail (caché par défaut) ──────────
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
             f"{t.get('nom_commercial', '—')} (AMM {t.get('num_amm', '—')})")
        row += 1
        _row(layout, row, "Substance(s) :", t.get("substance_active"))
        row += 1
        _row(layout, row, "Culture :", t.get("culture"))
        row += 1
        _row(layout, row, "Bio-agresseur :", t.get("bio_agresseur"))
        row += 1
        _row(layout, row, "Parcelle :", t.get("parcelle_nom"))
        row += 1

        dose = t.get("dose_appliquee")
        unite = t.get("unite", "L/ha")
        surf = t.get("surface_traitee_ha")
        dose_txt = f"{dose} {unite}" if dose else "—"
        if surf:
            dose_txt += f" — surface : {surf} ha"
        _row(layout, row, "Dose appliquée :", dose_txt)
        row += 1

        _row(layout, row, "Date traitement :",
             self._fmt_date(t.get("date_traitement")))
        row += 1
        _row(layout, row, "Décideur :", t.get("decideur_nom"))
        row += 1
        _row(layout, row, "Opérateur :", t.get("operateur_nom"))
        row += 1

        # Météo
        meteo_parts = []
        if t.get("meteo_temperature") is not None:
            meteo_parts.append(f"{t['meteo_temperature']}°C")
        if t.get("meteo_vent"):
            meteo_parts.append(f"Vent : {t['meteo_vent']}")
        if t.get("meteo_nebulosite"):
            meteo_parts.append(t["meteo_nebulosite"])
        _row(layout, row, "Météo :",
             " | ".join(meteo_parts) if meteo_parts else None)
        row += 1

        epi = "Oui" if t.get("epi_utilises") else "Non"
        _row(layout, row, "EPI utilisés :", epi)
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
        # Peut décider = créer une décision de traitement
        self._is_decideur = peut(current_user, "peut_decider") or                             current_user.get("role") == "admin"
        # Peut appliquer = confirmer/exécuter un traitement
        self._is_applicateur = peut(current_user, "peut_appliquer") or                                current_user.get("role") == "admin"
        # OPE = peut appliquer mais ne décide pas
        self._is_ope = self._is_applicateur and not self._is_decideur
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Titre
        titre = QLabel("Carnet de traitements phytosanitaires")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        # Onglets selon le rôle
        self.tabs = QTabWidget()

        if self._is_decideur:
            # Onglet décisions en attente
            self.tab_decisions = self._build_tab_decisions()
            self.tabs.addTab(self.tab_decisions, "Décisions en attente")

        # Onglet "Traitements à effectuer" : OPE + DESA/DENSA (qui peuvent appliquer)
        if self._is_applicateur:
            self.tab_a_faire = self._build_tab_a_faire()
            label_afaire = "Traitements à effectuer"
            if self._is_decideur:
                label_afaire = "Traitements en attente"
            self.tabs.addTab(self.tab_a_faire, label_afaire)

        # Historique — tout le monde avec carnet_lecture
        if peut(self.current_user, "carnet_lecture"):
            self.tab_historique = self._build_tab_historique()
            self.tabs.addTab(self.tab_historique, "Historique")

        root.addWidget(self.tabs, 1)

    # ──────────────────────────────────────────
    # Tab : Décisions (CON/DESA/DENSA/admin)
    # ──────────────────────────────────────────
    def _build_tab_decisions(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QHBoxLayout()
        lbl = QLabel("Créez une décision de traitement — l'OPE la recevra et confirmera l'application.")
        lbl.setStyleSheet("color: palette(mid); font-size: 12px;")
        lbl.setWordWrap(True)
        top.addWidget(lbl, 1)
        btn_new = QPushButton("+ Nouvelle décision")
        btn_new.clicked.connect(self._dialog_decision)
        top.addWidget(btn_new)
        layout.addLayout(top)

        # Filtres
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

    # ──────────────────────────────────────────
    # Tab : À faire (OPE)
    # ──────────────────────────────────────────
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

    # ──────────────────────────────────────────
    # Tab : Historique
    # ──────────────────────────────────────────
    def _build_tab_historique(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Filtres
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

        filtre.addWidget(QLabel("Du :"))
        filtre.addWidget(self.inp_histo_debut)
        filtre.addWidget(QLabel("au :"))
        filtre.addWidget(self.inp_histo_fin)
        filtre.addWidget(QLabel("Culture :"))
        filtre.addWidget(self.combo_histo_culture)
        filtre.addStretch()
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
        if self._is_decideur:
            self._charger_decisions()
        if self._is_applicateur:
            self._charger_a_faire()
        if peut(self.current_user, "carnet_lecture"):
            self._charger_cultures_filtre()
            self._charger_historique()

    def _charger_decisions(self):
        statuts = self.combo_statut_dec.currentData()
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
            traceback.print_exc()

    def _charger_a_faire(self):
        """Décisions en attente assignées à l'OPE (toutes de l'exploitation)."""
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
                       ud.prenom || ' ' || ud.nom AS decideur_nom
                FROM ppp_decisions d
                JOIN ppp_produits p  ON p.id  = d.produit_id
                LEFT JOIN parcelles parc ON parc.id = d.parcelle_id
                JOIN users ud        ON ud.id = d.decideur_id
                WHERE d.statut IN ('en_attente', 'en_cours')
                ORDER BY d.date_prevue ASC
            """)
            rows = [dict(r) for r in cur.fetchall()]
            cur.close()

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
            traceback.print_exc()

    def _charger_historique(self):
        date_debut = self.inp_histo_debut.date().toString("yyyy-MM-dd")
        date_fin   = self.inp_histo_fin.date().toString("yyyy-MM-dd")
        culture    = self.combo_histo_culture.currentData()

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
            traceback.print_exc()

    def _annuler_decision(self, decision_id: int):
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
                self._charger_decisions()
            except Exception as e:
                traceback.print_exc()

    def _dialog_decision(self):
        dlg = DialogDecision(current_user=self.current_user, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger()

    @staticmethod
    def pre_remplir(self, produit_id: int, usage_id: int,
                    culture: str, bio_agresseur: str):
        """
        Appelée depuis l'aide à la décision via le signal creer_traitement.
        - CON : crée une décision (sans appliquer)
        - DESA/DENSA : crée une décision ET peut l'appliquer immédiatement
        - OPE : ne peut pas accéder ici (bouton masqué dans aide_decision)
        """
        if not self._is_decideur and not self._is_applicateur:
            QMessageBox.information(
                self, "Accès limité",
                "Vous n'avez pas les droits pour créer un traitement.")
            return

        if self._is_decideur:
            # CON/DESA/DENSA : crée une décision
            _pre_remplir_carnet(self, produit_id, usage_id, culture, bio_agresseur)
        else:
            QMessageBox.information(
                self, "Accès limité",
                "Seuls les CON, DESA, DENSA et admins peuvent créer une décision.\n"
                "Contactez votre décideur pour planifier ce traitement.")

    @staticmethod
    def _vider_layout(layout: QVBoxLayout):
        while layout.count() > 1:  # Garder le stretch
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


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

        # Header cliquable
        header = QHBoxLayout()

        badge = QLabel(f" {labels_statut.get(statut, statut)} ")
        badge.setStyleSheet(
            f"background: {couleurs.get(statut, '#888')}; color: white; "
            f"border-radius: 3px; padding: 2px 6px; font-size: 11px;")
        header.addWidget(badge)

        date_prev = d.get("date_prevue")
        date_txt = self._fmt_date(date_prev) if date_prev else "Sans date"
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

        # Détail
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
            ("Produit :", f"{d.get('nom_commercial', '—')} — AMM {d.get('num_amm', '—')}"),
            ("Parcelle :", d.get("parcelle_nom")),
            ("Culture :", d.get("culture")),
            ("Bio-agresseur :", d.get("bio_agresseur")),
            ("Dose prescrite :", f"{d.get('dose_prescrite', '—')} {d.get('unite', '')}"),
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

        # Boutons action
        if d.get("statut") in ("en_attente", "en_cours"):
            btns = QHBoxLayout()
            btn_annuler = QPushButton("Annuler")
            btn_annuler.clicked.connect(
                lambda: self.on_annuler(d["id"]))
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
# Carte "à faire" (vue OPE)
# ─────────────────────────────────────────────────────────────
class CarteAFaire(QFrame):
    def __init__(self, decision: dict, current_user: dict,
                 on_refresh, parent=None):
        super().__init__(parent)
        self.decision = decision
        self.current_user = current_user
        self.on_refresh = on_refresh
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #F5A623;
                border-radius: 6px;
                margin-bottom: 6px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        d = self.decision

        # Résumé
        titre = QLabel(
            f"{d.get('nom_commercial', '—')} — {d.get('culture', '—')} "
            f"/ {d.get('bio_agresseur', '—')}")
        f = QFont(); f.setBold(True); f.setPointSize(12)
        titre.setFont(f)
        layout.addWidget(titre)

        infos = QLabel(
            f"Parcelle : {d.get('parcelle_nom') or '—'}  |  "
            f"Dose : {d.get('dose_prescrite', '—')} {d.get('unite', '')}  |  "
            f"Date prévue : {self._fmt_date(d.get('date_prevue'))}  |  "
            f"Décidé par : {d.get('decideur_nom', '—')}")
        infos.setStyleSheet("font-size: 12px; color: palette(mid);")
        infos.setWordWrap(True)
        layout.addWidget(infos)

        if d.get("notes_decideur"):
            lbl_notes = QLabel(f"Note décideur : {d['notes_decideur']}")
            lbl_notes.setStyleSheet("font-size: 12px; font-style: italic;")
            lbl_notes.setWordWrap(True)
            layout.addWidget(lbl_notes)

        # Bouton confirmer
        btn = QPushButton("Confirmer l'application →")
        btn.setFixedHeight(36)
        btn.setStyleSheet("""
            QPushButton {
                background: #7ED321; color: white;
                border-radius: 4px; font-weight: bold;
            }
            QPushButton:hover { background: #6ABE10; }
        """)
        btn.clicked.connect(self._confirmer)
        layout.addWidget(btn)

    def _confirmer(self):
        dlg = DialogConfirmerTraitement(
            decision=self.decision,
            current_user=self.current_user,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
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
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        # Produit (recherche par AMM ou nom)
        self.inp_amm = QLineEdit()
        self.inp_amm.setPlaceholderText("N° AMM ou nom du produit...")
        self.inp_amm.textChanged.connect(self._rechercher_produit)
        form.addRow("Produit * (AMM/nom) :", self.inp_amm)

        self.combo_produit = QComboBox()
        self.combo_produit.addItem("— Résultats de recherche —", None)
        form.addRow("Sélectionner :", self.combo_produit)

        # Parcelle
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("— Sélectionnez —", None)
        form.addRow("Parcelle *", self.combo_parcelle)

        # Culture
        self.inp_culture = QLineEdit()
        self.inp_culture.setPlaceholderText("Culture concernée")
        form.addRow("Culture *", self.inp_culture)

        # Bio-agresseur
        self.inp_bio_agr = QLineEdit()
        self.inp_bio_agr.setPlaceholderText("Bio-agresseur ciblé")
        form.addRow("Bio-agresseur", self.inp_bio_agr)

        # Dose
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

        # Date prévue
        self.inp_date = QDateEdit(QDate.currentDate().addDays(1))
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date prévue", self.inp_date)

        # Notes
        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        self.inp_notes.setPlaceholderText("Instructions pour l'opérateur...")
        form.addRow("Notes", self.inp_notes)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        form.addRow(self.lbl_err)

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
            cur.execute("SELECT id, nom, culture FROM parcelles WHERE actif=1 ORDER BY nom")
            for row in cur.fetchall():
                label = row[1]
                if row[2]:
                    label += f" ({row[2]})"
                self.combo_parcelle.addItem(label, row[0])
                # Auto-remplir culture
                self.combo_parcelle.setItemData(
                    self.combo_parcelle.count() - 1, row[2], Qt.UserRole + 1)
            cur.close()
        except Exception as e:
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
                self.combo_produit.addItem(
                    f"{row[1]} (AMM {row[2]})", row[0])
            self.combo_produit.blockSignals(False)
        except Exception as e:
            traceback.print_exc()

    def _valider(self):
        produit_id  = self.combo_produit.currentData()
        parcelle_id = self.combo_parcelle.currentData()
        culture     = self.inp_culture.text().strip()
        dose        = self.inp_dose.value()

        if not produit_id:
            self.lbl_err.setText("Sélectionnez un produit.")
            return
        if not parcelle_id:
            self.lbl_err.setText("Sélectionnez une parcelle.")
            return
        if not culture:
            self.lbl_err.setText("Renseignez la culture.")
            return
        if dose <= 0:
            self.lbl_err.setText("Dose invalide.")
            return

        bio_agr = self.inp_bio_agr.text().strip() or None
        unite   = self.inp_unite.text().strip() or "L/ha"
        date_p  = self.inp_date.date().toString("yyyy-MM-dd")
        notes   = self.inp_notes.toPlainText().strip() or None

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

            # Si DESA/DENSA veut appliquer immédiatement
            if (self._peut_appliquer and
                    hasattr(self, 'chk_appliquer_maintenant') and
                    self.chk_appliquer_maintenant.isChecked()):
                # Récupérer les infos pour pré-remplir le dialog d'application
                decision_dict = {
                    "id":            decision_id,
                    "nom_commercial": self.prod_info.get("nom_commercial"),
                    "num_amm":        self.prod_info.get("num_amm"),
                    "substance_active": self.prod_info.get("substance_active"),
                    "parcelle_nom":   self.combo_parcelle.currentText().split(" (")[0],
                    "culture":        self.culture,
                    "bio_agresseur":  self.bio_agresseur,
                    "dose_prescrite": dose,
                    "unite":          unite,
                    "date_prevue":    date_p,
                    "notes_decideur": notes,
                    "decideur_nom":   (self.current_user.get("prenom","") + " " +
                                      self.current_user.get("nom","")).strip(),
                    "produit_id":     self.produit_id,
                }
                dlg_appli = DialogConfirmerTraitement(
                    decision=decision_dict,
                    current_user=self.current_user,
                    parent=self.parent())
                dlg_appli.exec()

            self.accept()
        except Exception as e:
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
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Rappel décision
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

        # Formulaire application
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

        # Météo
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
        meteo_lay.addWidget(QLabel("T°:"))
        meteo_lay.addWidget(self.inp_temp)
        meteo_lay.addWidget(QLabel("Vent:"))
        meteo_lay.addWidget(self.combo_vent)
        meteo_lay.addWidget(QLabel("Neb:"))
        meteo_lay.addWidget(self.combo_neb)
        form.addRow("Météo", meteo_w)

        self.chk_epi = QCheckBox("EPI portés")
        form.addRow("EPI", self.chk_epi)

        # Signature
        self.inp_sig_nom = QLineEdit()
        prenom = self.current_user.get("prenom", "")
        nom    = self.current_user.get("nom", "")
        self.inp_sig_nom.setText(f"{prenom} {nom}".strip())
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

        date_app  = self.inp_date.date().toString("yyyy-MM-dd")
        dose      = self.inp_dose.value()
        unite     = self.decision.get("unite", "L/ha")
        surface   = self.inp_surface.value() or None
        temp      = self.inp_temp.value()
        vent      = self.combo_vent.currentText()
        neb       = self.combo_neb.currentText()
        epi       = 1 if self.chk_epi.isChecked() else 0
        notes     = self.inp_notes.text().strip() or None
        decision_id = self.decision["id"]
        produit_id  = self.decision.get("produit_id") or self._get_produit_id()
        parcelle_id = self._get_parcelle_id()

        try:
            conn = get_connection()
            cur = conn.cursor()

            # Enregistrer le traitement
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

            # Marquer la décision comme faite
            cur.execute(
                "UPDATE ppp_decisions SET statut = 'fait' WHERE id = ?",
                (decision_id,))

            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
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
# Méthode appelée depuis l'aide à la décision
# ─────────────────────────────────────────────────────────────
def _pre_remplir_carnet(carnet_page, produit_id: int, usage_id: int,
                         culture: str, bio_agresseur: str):
    """
    Pré-remplit le dialog de nouvelle décision depuis l'aide à la décision.
    Vérifie que la dose prescrite est ≤ dose max homologuée pour cette culture.
    Appelée via CarnetPage.pre_remplir().
    """
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Récupérer les infos du produit + usage
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
            QMessageBox.warning(None, "Produit introuvable",
                "Impossible de récupérer les informations du produit.")
            return

        prod_info = dict(zip(
            ["nom_commercial", "num_amm", "substance_active",
             "dose_max", "dose_unite", "dar", "nma", "condition_usage"],
            row))

    except Exception as e:
        traceback.print_exc()
        return

    # Naviguer vers l'onglet "Décisions en attente" si décideur
    if hasattr(carnet_page, "tabs") and hasattr(carnet_page, "tab_decisions"):
        carnet_page.tabs.setCurrentWidget(carnet_page.tab_decisions)

    # Ouvrir le dialog pré-rempli
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
        carnet_page._charger()


class DialogDecisionPreRempli(QDialog):
    """
    Dialog de nouvelle décision pré-rempli depuis l'aide à la décision.
    Bloque les champs produit/culture/bio-agresseur (déjà choisis).
    Vérifie que dose ≤ dose_max homologuée.
    """
    def __init__(self, produit_id: int, usage_id: int,
                 culture: str, bio_agresseur: str,
                 prod_info: dict, current_user: dict, parent=None):
        super().__init__(parent)
        self.produit_id   = produit_id
        self.usage_id     = usage_id
        self.culture      = culture
        self.bio_agresseur = bio_agresseur
        self.prod_info    = prod_info
        self.current_user = current_user
        self.dose_max     = prod_info.get("dose_max")

        self.setWindowTitle("Nouvelle décision de traitement")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Récap produit (lecture seule)
        recap = QGroupBox("Produit sélectionné")
        recap_lay = QFormLayout(recap)
        recap_lay.setSpacing(6)

        p = self.prod_info
        recap_lay.addRow("Produit :",
            QLabel(f"{p.get('nom_commercial','—')} (AMM {p.get('num_amm','—')})"))
        recap_lay.addRow("Substance(s) :", QLabel(p.get("substance_active") or "—"))
        recap_lay.addRow("Culture :", QLabel(self.culture or "—"))
        recap_lay.addRow("Bio-agresseur :", QLabel(self.bio_agresseur or "—"))

        dose_max = self.dose_max
        dose_unite = p.get("dose_unite") or "L/ha"
        if dose_max:
            lbl_dose_max = QLabel(f"{dose_max} {dose_unite}")
            lbl_dose_max.setStyleSheet("color: #D97706; font-weight: bold;")
            recap_lay.addRow("Dose max homologuée :", lbl_dose_max)
        if p.get("dar"):
            recap_lay.addRow("DAR :", QLabel(f"{p['dar']} jour(s)"))
        if p.get("nma"):
            recap_lay.addRow("Nb max applications :", QLabel(str(p["nma"])))
        if p.get("condition_usage"):
            lbl_cond = QLabel(p["condition_usage"])
            lbl_cond.setWordWrap(True)
            lbl_cond.setStyleSheet("font-size: 11px; color: palette(mid);")
            recap_lay.addRow("Condition usage :", lbl_cond)
        layout.addWidget(recap)

        # Formulaire décision
        form_group = QGroupBox("Décision de traitement")
        form = QFormLayout(form_group)
        form.setSpacing(10)

        # Parcelle
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("— Sélectionnez —", None)
        self._charger_parcelles()
        form.addRow("Parcelle *", self.combo_parcelle)

        # Dose prescrite avec vérification temps réel
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

        # Date prévue
        self.inp_date = QDateEdit(QDate.currentDate().addDays(1))
        self.inp_date.setDisplayFormat("dd/MM/yyyy")
        self.inp_date.setCalendarPopup(True)
        form.addRow("Date prévue", self.inp_date)

        # Notes
        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(70)
        self.inp_notes.setPlaceholderText("Instructions pour l'opérateur...")
        form.addRow("Notes", self.inp_notes)

        layout.addWidget(form_group)

        # Option "appliquer maintenant" pour DESA/DENSA uniquement
        self._peut_appliquer = peut(self.current_user, "peut_appliquer") or                                self.current_user.get("role") == "admin"
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

        # Vérification initiale
        self._verifier_dose()

    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, nom, culture FROM parcelles
                WHERE actif = 1 ORDER BY nom
            """)
            for row in cur.fetchall():
                label = row[1]
                if row[2]:
                    label += f" ({row[2]})"
                self.combo_parcelle.addItem(label, row[0])
                # Auto-sélectionner si la culture correspond
                if row[2] and row[2].lower() == (self.culture or "").lower():
                    self.combo_parcelle.setCurrentIndex(
                        self.combo_parcelle.count() - 1)
            cur.close()
        except Exception as e:
            traceback.print_exc()

    def _verifier_dose(self):
        dose = self.inp_dose.value()
        if self.dose_max and dose > self.dose_max:
            self.lbl_dose_warn.setText(
                f"⚠ Dépasse la dose max ({self.dose_max})")
            self.inp_dose.setStyleSheet("border: 2px solid red;")
        else:
            self.lbl_dose_warn.setText("")
            self.inp_dose.setStyleSheet("")

    def _valider(self):
        parcelle_id = self.combo_parcelle.currentData()
        dose        = self.inp_dose.value()

        if not parcelle_id:
            self.lbl_err.setText("Sélectionnez une parcelle.")
            return

        # Vérification homologation culture + bio-agresseur
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM ppp_usages
                WHERE produit_id = ? AND culture = ? AND bio_agresseur = ?
            """, (self.produit_id,
                  self.culture or "",
                  self.bio_agresseur or ""))
            homol_count = cur.fetchone()[0]
            cur.close()
        except Exception as e:
            traceback.print_exc()
            homol_count = 0

        if homol_count == 0:
            # Vérifier si homologué sur la culture seule (sans bio-agresseur exact)
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
                QMessageBox.critical(
                    self, "Produit non homologué",
                    f"Ce produit n'est pas homologué pour la culture "
                    f"« {self.culture} »."
                    f"La décision ne peut pas être créée.")
                return
            else:
                # Homologué sur la culture mais pas pour ce bio-agresseur exact
                rep = QMessageBox.warning(
                    self, "Bio-agresseur non confirmé",
                    f"Ce produit est homologué sur « {self.culture} » "
                    f"mais l'usage exact pour « {self.bio_agresseur} » "
                    f"n'est pas trouvé dans la base e-phy."
                    f"Voulez-vous quand même créer la décision ?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No)
                if rep == QMessageBox.No:
                    return

        # Bloquer si dose > dose_max (avec confirmation si dépassement)
        if self.dose_max and dose > self.dose_max:
            rep = QMessageBox.warning(
                self, "Dose supérieure au maximum homologué",
                f"La dose saisie ({dose}) dépasse la dose maximum "
                f"homologuée ({self.dose_max} {self.prod_info.get('dose_unite','')}).\n\n"
                f"Êtes-vous sûr de vouloir continuer ?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
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
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")