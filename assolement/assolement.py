# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from datetime import date, datetime, timedelta

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import (get_connection, peut_action,
                get_familles, get_cultures_ref,
                get_planches_parcelle, get_assolement_annee,
                get_couleur_culture)
import utils.debug as debug
import traceback

# ── Constantes de rendu ───────────────────────
H_ENTETE    = 36   # hauteur en-tête semaines
H_PARCELLE  = 28   # hauteur ligne titre parcelle
H_PLANCHE   = 28   # hauteur ligne planche
L_NOM       = 200  # largeur colonne noms
L_SEMAINE   = 18   # largeur d'une colonne semaine (52 × 18 = 936px)
W_PALETTE   = 220  # largeur du panneau gauche cultures

MOIS_COURTS = ["Jan","Fév","Mar","Avr","Mai","Jun",
                "Jul","Aoû","Sep","Oct","Nov","Déc"]


def semaine_to_x(semaine: int) -> int:
    """Position X de la semaine (1-52) dans la grille."""
    return L_NOM + (semaine - 1) * L_SEMAINE


def date_to_semaine(d: str, annee: int) -> float:
    """Convertit 'YYYY-MM-DD' en numéro de semaine (1.0-52.0) dans l'année."""
    try:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return 1.0
    debut_annee = date(annee, 1, 1)
    if dt.year < annee:
        return 1.0
    if dt.year > annee:
        return 53.0
    jours = (dt - debut_annee).days
    total = 366 if annee % 4 == 0 else 365
    return 1.0 + jours / total * 52.0


def semaine_to_date(semaine: float, annee: int) -> date:
    """Convertit un numéro de semaine (1-52) en date."""
    debut = date(annee, 1, 1)
    total = 366 if annee % 4 == 0 else 365
    jours = int((semaine - 1) / 52.0 * total)
    return debut + timedelta(days=jours)


# ── Page principale ───────────────────────────
class AssolementPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user    = current_user
        self._peut_ecrire    = peut_action(current_user, "parcelles", "ecriture")
        self._peut_supprimer = peut_action(current_user, "parcelles", "suppression")
        self._annee          = datetime.now().year
        self._culture_active = None  # dict culture_ref sélectionnée dans palette
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Barre du haut ─────────────────────
        barre = QHBoxLayout()

        titre = QLabel("Plan d'assolement")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        titre.setFont(f)
        barre.addWidget(titre)
        barre.addStretch()

        barre.addWidget(QLabel("Année :"))
        self.combo_annee = QComboBox()
        annee_act = self._annee
        for a in range(annee_act - 4, annee_act + 3):
            self.combo_annee.addItem(str(a), a)
        self.combo_annee.setCurrentText(str(annee_act))
        self.combo_annee.currentIndexChanged.connect(self._on_annee_changed)
        barre.addWidget(self.combo_annee)

        barre.addWidget(QLabel("Parcelle :"))
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.addItem("Toutes", None)
        self.combo_parcelle.currentIndexChanged.connect(self._charger_grille)
        barre.addWidget(self.combo_parcelle)

        if self._peut_ecrire:
            btn_planches = QPushButton("⚙ Planches")
            btn_planches.clicked.connect(self._dialog_gerer_planches)
            btn_planches.setStyleSheet("""
                QPushButton { background:#2563EB; color:white;
                    border-radius:4px; padding:4px 10px; }
                QPushButton:hover { background:#1d4ed8; }
            """)
            barre.addWidget(btn_planches)

        root.addLayout(barre)

        # ── Corps principal : palette | grille ─
        corps = QHBoxLayout()
        corps.setSpacing(0)

        # Panneau gauche : palette de cultures
        self.palette = PaletteCultures(
            peut_ecrire=self._peut_ecrire,
            on_select=self._on_culture_selectionnee)
        self.palette.setFixedWidth(W_PALETTE)
        corps.addWidget(self.palette)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #e5e7eb;")
        corps.addWidget(sep)

        # Grille d'assolement
        self.grille_scroll = QScrollArea()
        self.grille_scroll.setWidgetResizable(True)
        self.grille_scroll.setFrameShape(QFrame.NoFrame)
        self.canvas = GrilleCanvas(
            annee=self._annee,
            peut_ecrire=self._peut_ecrire,
            peut_supprimer=self._peut_supprimer,
            on_assigner=self._assigner_culture,
            on_modifier=self._dialog_modifier,
            on_supprimer=self._supprimer_culture,
            get_culture_active=lambda: self._culture_active,
        )
        self.grille_scroll.setWidget(self.canvas)
        corps.addWidget(self.grille_scroll, 1)

        root.addLayout(corps, 1)

        # Barre de statut
        self.lbl_statut = QLabel(
            "💡 Sélectionnez une culture à gauche puis cliquez sur une planche")
        self.lbl_statut.setStyleSheet(
            "color: #6b7280; font-size: 11px; padding: 2px 4px;")
        root.addWidget(self.lbl_statut)

    # ──────────────────────────────────────────
    # Callbacks
    # ──────────────────────────────────────────
    def _on_culture_selectionnee(self, culture: dict):
        self._culture_active = culture
        nom = culture["nom"] if culture else "—"
        self.lbl_statut.setText(
            f"✅ Culture sélectionnée : {nom} — "
            "cliquez sur une planche pour l'assigner")
        self.canvas.update()

    def _on_annee_changed(self):
        self._annee = self.combo_annee.currentData()
        self.canvas.annee = self._annee
        self._charger_grille()

    def _assigner_culture(self, planche_id: int,
                           semaine_debut: float, semaine_fin: float):
        """Appelé quand l'utilisateur clique/drag sur une planche."""
        if not self._culture_active:
            QMessageBox.information(self, "Aucune culture sélectionnée",
                "Sélectionnez d'abord une culture dans le panneau de gauche.")
            return

        date_semis = semaine_to_date(semaine_debut, self._annee)
        date_fin   = semaine_to_date(semaine_fin,   self._annee)

        dlg = DialogCultureAssolement(
            annee=self._annee,
            planche_id_preselect=planche_id,
            culture_ref_id_preselect=self._culture_active["id"],
            date_semis_preselect=date_semis,
            date_fin_preselect=date_fin,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_grille()

    def _dialog_modifier(self, assolement_id: int):
        dlg = DialogCultureAssolement(
            annee=self._annee,
            assolement_id=assolement_id,
            parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_grille()

    def _supprimer_culture(self, assolement_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer cette culture de l'assolement ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur  = conn.cursor()
                cur.execute("DELETE FROM assolement WHERE id=?",
                            (assolement_id,))
                conn.commit()
                cur.close()
                self._charger_grille()
            except Exception:
                traceback.print_exc()

    def _dialog_gerer_planches(self):
        dlg = DialogGererPlanches(parent=self)
        dlg.exec()
        self._charger()

    # ──────────────────────────────────────────
    # Chargement
    # ──────────────────────────────────────────
    def _charger(self):
        self._charger_combo_parcelles()
        self.palette.recharger()
        self._charger_grille()

    def _charger_combo_parcelles(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            self.combo_parcelle.blockSignals(True)
            self.combo_parcelle.clear()
            self.combo_parcelle.addItem("Toutes", None)
            for row in cur.fetchall():
                self.combo_parcelle.addItem(row[1], row[0])
            self.combo_parcelle.blockSignals(False)
            cur.close()
        except Exception:
            traceback.print_exc()

    def _charger_grille(self):
        annee       = self._annee
        parcelle_id = self.combo_parcelle.currentData()
        try:
            conn = get_connection()
            cur  = conn.cursor()
            if parcelle_id:
                cur.execute("""
                    SELECT pl.*, p.nom AS parcelle_nom,
                           p.id AS parcelle_id
                    FROM planches pl
                    JOIN parcelles p ON p.id = pl.parcelle_id
                    WHERE pl.parcelle_id = ?
                    ORDER BY p.nom, pl.numero
                """, (parcelle_id,))
            else:
                cur.execute("""
                    SELECT pl.*, p.nom AS parcelle_nom,
                           p.id AS parcelle_id
                    FROM planches pl
                    JOIN parcelles p ON p.id = pl.parcelle_id
                    WHERE p.actif = 1
                    ORDER BY p.nom, pl.numero
                """)
            planches = [dict(r) for r in cur.fetchall()]
            cur.close()
        except Exception:
            traceback.print_exc()
            planches = []

        assolement = get_assolement_annee(annee, parcelle_id)
        self.canvas.charger(planches, assolement)
        debug.debug(f"[assolement] {len(planches)} planche(s), "
                    f"{len(assolement)} culture(s) en {annee}")

    def recharger(self):
        self._charger()


# ── Panneau gauche : palette de cultures ──────
class PaletteCultures(QWidget):
    def __init__(self, peut_ecrire: bool, on_select, parent=None):
        super().__init__(parent)
        self.peut_ecrire = peut_ecrire
        self.on_select   = on_select
        self._culture_active_id = None
        self._build_ui()
        self.recharger()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(6)

        lbl = QLabel("Cultures")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        lbl.setFont(f)
        lay.addWidget(lbl)

        # Recherche
        self.inp_recherche = QLineEdit()
        self.inp_recherche.setPlaceholderText("🔍 Rechercher...")
        self.inp_recherche.textChanged.connect(self._filtrer)
        lay.addWidget(self.inp_recherche)

        # Liste scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._liste_widget = QWidget()
        self._liste_lay = QVBoxLayout(self._liste_widget)
        self._liste_lay.setSpacing(3)
        self._liste_lay.setContentsMargins(0, 0, 0, 0)
        self._liste_lay.addStretch()
        scroll.setWidget(self._liste_widget)
        lay.addWidget(scroll, 1)

        # Boutons
        if self.peut_ecrire:
            btn_new = QPushButton("+ Nouvelle culture")
            btn_new.setStyleSheet("""
                QPushButton { background:#16a34a; color:white;
                    border-radius:4px; padding:4px; font-size:11px; }
                QPushButton:hover { background:#15803d; }
            """)
            btn_new.clicked.connect(self._creer_culture)
            lay.addWidget(btn_new)

        # Légende familles
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        lay.addWidget(sep)
        lbl_fam = QLabel("Familles botaniques :")
        lbl_fam.setStyleSheet("font-size: 10px; color: #6b7280;")
        lay.addWidget(lbl_fam)
        self._legende_lay = QVBoxLayout()
        self._legende_lay.setSpacing(2)
        lay.addLayout(self._legende_lay)

    def recharger(self):
        self._cultures = get_cultures_ref()
        self._filtrer(self.inp_recherche.text())
        self._build_legende()

    def _filtrer(self, texte: str = ""):
        # Vider
        while self._liste_lay.count() > 1:
            item = self._liste_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtre = texte.lower().strip()
        for c in self._cultures:
            if filtre and filtre not in c["nom"].lower():
                continue
            btn = self._make_culture_btn(c)
            self._liste_lay.insertWidget(
                self._liste_lay.count() - 1, btn)

    def _make_culture_btn(self, c: dict) -> QPushButton:
        couleur = (c.get("couleur_perso") or
                   c.get("famille_couleur") or "#95A5A6")
        nom = c["nom"]
        if c.get("famille_nom"):
            nom += f"\n{c['famille_nom']}"

        btn = QPushButton(nom)
        btn.setCheckable(True)
        btn.setChecked(c["id"] == self._culture_active_id)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {couleur}22;
                border: 2px solid {couleur};
                border-radius: 4px;
                color: #1f2937;
                text-align: left;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:checked {{
                background: {couleur};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {couleur}55;
            }}
        """)
        btn.clicked.connect(lambda checked, cult=c: self._select(cult))

        # Clic droit pour modifier/supprimer
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, cult=c, b=btn: self._menu_culture(cult, b, pos))

        return btn

    def _select(self, culture: dict):
        self._culture_active_id = culture["id"]
        self.on_select(culture)
        self._filtrer(self.inp_recherche.text())

    def _menu_culture(self, culture: dict, btn: QPushButton, pos):
        if not self.peut_ecrire:
            return
        menu = QMenu(self)
        menu.addAction("✏ Modifier",
            lambda: self._modifier_culture(culture))
        menu.exec(btn.mapToGlobal(pos))

    def _creer_culture(self):
        dlg = DialogCultureRef(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.recharger()

    def _modifier_culture(self, culture: dict):
        dlg = DialogCultureRef(culture_id=culture["id"], parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.recharger()

    def _build_legende(self):
        while self._legende_lay.count():
            item = self._legende_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        familles = get_familles()
        for fam in familles:
            w = QWidget()
            hl = QHBoxLayout(w)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(4)
            carre = QLabel("■")
            carre.setStyleSheet(f"color: {fam['couleur_hex']}; font-size: 14px;")
            lbl = QLabel(fam["nom"])
            lbl.setStyleSheet("font-size: 10px; color: #374151;")
            hl.addWidget(carre)
            hl.addWidget(lbl)
            hl.addStretch()
            self._legende_lay.addWidget(w)


# ── Grille d'assolement (canvas QPainter) ─────
class GrilleCanvas(QWidget):
    """Canvas interactif : 52 colonnes semaines × N lignes planches.
    Supporte le clic + drag pour assigner une culture."""

    def __init__(self, annee: int, peut_ecrire: bool, peut_supprimer: bool,
                 on_assigner, on_modifier, on_supprimer,
                 get_culture_active, parent=None):
        super().__init__(parent)
        self.annee             = annee
        self.peut_ecrire       = peut_ecrire
        self.peut_supprimer    = peut_supprimer
        self.on_assigner       = on_assigner
        self.on_modifier       = on_modifier
        self.on_supprimer      = on_supprimer
        self.get_culture_active = get_culture_active

        self._planches   = []
        self._assolement = []
        self._lignes     = []   # [(type, data)]
        self._blocs      = []   # [(QRect, assol_dict)]
        self._collapsed  = set()
        self._hover_bloc = None

        # Drag state
        self._drag_planche_id = None
        self._drag_x_start    = None
        self._drag_x_current  = None
        self._drag_y          = None

        self.setMouseTracking(True)
        self.setAcceptDrops(False)
        self.setMinimumWidth(L_NOM + 52 * L_SEMAINE + 20)

    def charger(self, planches: list, assolement: list):
        self._planches   = planches
        self._assolement = assolement
        self._build_lignes()
        self._update_size()
        self.update()

    def _build_lignes(self):
        self._lignes = []
        parcelles_vues = {}
        for pl in self._planches:
            pid = pl.get("parcelle_id")
            if pid not in parcelles_vues:
                parcelles_vues[pid] = pl.get("parcelle_nom", f"Parcelle {pid}")
                self._lignes.append(("parcelle", {
                    "parcelle_id": pid,
                    "nom": parcelles_vues[pid]
                }))
            if pid not in self._collapsed:
                self._lignes.append(("planche", pl))

    def _update_size(self):
        nb = len(self._lignes)
        h = H_ENTETE + nb * H_PLANCHE + 20
        w = L_NOM + 52 * L_SEMAINE + 20
        self.setMinimumSize(w, h)

    def _y_ligne(self, idx: int) -> int:
        return H_ENTETE + idx * H_PLANCHE

    # ──────────────────────────────────────────
    # Rendu
    # ──────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w_total = L_NOM + 52 * L_SEMAINE
        h_total = H_ENTETE + len(self._lignes) * H_PLANCHE

        # Fond
        painter.fillRect(0, 0, w_total + 20, h_total + 20, Qt.white)

        self._dessiner_entete(painter, w_total)
        self._dessiner_lignes(painter, w_total)
        self._dessiner_blocs(painter)
        self._dessiner_drag(painter)
        self._dessiner_aujourd_hui(painter, h_total)

        painter.end()

    def _dessiner_entete(self, painter: QPainter, w_total: int):
        painter.fillRect(0, 0, w_total, H_ENTETE, QColor("#f3f4f6"))

        # Colonne nom
        font_bold = QFont(); font_bold.setPointSize(8); font_bold.setBold(True)
        painter.setFont(font_bold)
        painter.setPen(QColor("#374151"))
        painter.drawText(QRect(0, 0, L_NOM, H_ENTETE),
                         Qt.AlignCenter, "Planche")

        # Mois au-dessus des semaines
        font_mois = QFont(); font_mois.setPointSize(7); font_mois.setBold(True)
        painter.setFont(font_mois)
        semaine = 1
        for m in range(12):
            # Semaines dans ce mois (approx)
            nb_sem = 4 if m < 11 else 4
            if m == 1:
                nb_sem = 4
            elif m in (0, 2, 4, 6, 7, 9, 11):
                nb_sem = 5 if (semaine - 1 + nb_sem) <= 52 else 4
            x1 = semaine_to_x(semaine)
            x2 = semaine_to_x(min(semaine + nb_sem, 53))
            rect_mois = QRect(x1, 0, x2 - x1, H_ENTETE // 2)
            painter.fillRect(rect_mois, QColor("#e5e7eb"))
            painter.setPen(QColor("#374151"))
            painter.drawText(rect_mois, Qt.AlignCenter, MOIS_COURTS[m])
            painter.setPen(QPen(QColor("#d1d5db"), 1))
            painter.drawLine(x1, 0, x1, H_ENTETE)
            semaine += nb_sem

        # Numéros de semaine
        font_sem = QFont(); font_sem.setPointSize(6)
        painter.setFont(font_sem)
        painter.setPen(QColor("#6b7280"))
        for s in range(1, 53):
            x = semaine_to_x(s)
            rect_s = QRect(x, H_ENTETE // 2, L_SEMAINE, H_ENTETE // 2)
            if s % 2 == 0:  # Afficher 1 semaine sur 2 pour lisibilité
                painter.drawText(rect_s, Qt.AlignCenter, str(s))
            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(x, H_ENTETE // 2, x, H_ENTETE)
            painter.setPen(QColor("#6b7280"))

        # Bordure bas entête
        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawLine(0, H_ENTETE, w_total, H_ENTETE)

    def _dessiner_lignes(self, painter: QPainter, w_total: int):
        font_parc  = QFont(); font_parc.setPointSize(9); font_parc.setBold(True)
        font_planc = QFont(); font_planc.setPointSize(8)

        for i, (typ, data) in enumerate(self._lignes):
            y = self._y_ligne(i)

            if typ == "parcelle":
                painter.fillRect(QRect(0, y, w_total, H_PARCELLE),
                                 QColor("#fef9c3"))
                painter.setFont(font_parc)
                painter.setPen(QColor("#713F12"))
                pid = data["parcelle_id"]
                icone = "▼ " if pid not in self._collapsed else "▶ "
                painter.drawText(
                    QRect(8, y, L_NOM - 8, H_PARCELLE),
                    Qt.AlignVCenter, icone + data["nom"])

                # Fond hachuré sur la partie grille pour indiquer "groupe"
                painter.fillRect(
                    QRect(L_NOM, y, w_total - L_NOM, H_PARCELLE),
                    QColor("#fefce8"))

            else:
                couleur_fond = QColor("#f9fafb") if i % 2 == 0 else Qt.white
                painter.fillRect(QRect(0, y, w_total, H_PLANCHE), couleur_fond)
                painter.setFont(font_planc)
                painter.setPen(QColor("#374151"))

                label = f"Planche {data['numero']}"
                if data.get("longueur_m"):
                    label += f"  {data['longueur_m']}m"
                if data.get("largeur_m"):
                    label += f" × {data['largeur_m']}m"
                if data.get("sous_abris"):
                    label += " 🏠"

                painter.drawText(
                    QRect(16, y, L_NOM - 20, H_PLANCHE),
                    Qt.AlignVCenter, label)

            # Grille verticale (semaines)
            painter.setPen(QPen(QColor("#f0f0f0"), 1))
            for s in range(1, 53):
                x = semaine_to_x(s)
                painter.drawLine(x, y, x, y + H_PLANCHE)

            # Séparateur horizontal
            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(0, y + H_PLANCHE - 1,
                             w_total, y + H_PLANCHE - 1)

        # Séparateur colonne nom
        painter.setPen(QPen(QColor("#d1d5db"), 2))
        painter.drawLine(L_NOM, H_ENTETE,
                         L_NOM, H_ENTETE + len(self._lignes) * H_PLANCHE)

    def _dessiner_blocs(self, painter: QPainter):
        self._blocs = []
        font_bloc = QFont(); font_bloc.setPointSize(8)
        painter.setFont(font_bloc)

        for i, (typ, data) in enumerate(self._lignes):
            if typ != "planche":
                continue
            y = self._y_ligne(i)
            planche_id = data["id"]

            for a in self._assolement:
                if a["planche_id"] != planche_id:
                    continue

                s1 = date_to_semaine(
                    a.get("date_semis") or f"{self.annee}-01-01", self.annee)
                s2 = date_to_semaine(
                    a.get("date_derniere_recolte") or
                    f"{self.annee}-12-31", self.annee)
                if s2 <= s1:
                    s2 = s1 + 2

                x1 = semaine_to_x(s1)
                x2 = semaine_to_x(min(s2, 53))
                if x2 <= x1:
                    x2 = x1 + L_SEMAINE

                couleur = QColor(get_couleur_culture(a))
                hover = (self._hover_bloc and
                         self._hover_bloc.get("id") == a.get("id"))
                if hover:
                    couleur = couleur.lighter(115)

                rect = QRect(x1 + 1, y + 2, x2 - x1 - 2, H_PLANCHE - 4)
                painter.fillRect(rect, couleur)

                # Bordure
                pen = QPen(couleur.darker(140), 1)
                painter.setPen(pen)
                painter.drawRoundedRect(rect, 3, 3)

                # Texte
                painter.setPen(QColor("#ffffff"))
                txt = a.get("culture_nom", "")
                if a.get("variete"):
                    txt += f" · {a['variete']}"
                metrics = painter.fontMetrics()
                txt = metrics.elidedText(txt, Qt.ElideRight, rect.width() - 6)
                painter.drawText(rect.adjusted(3, 0, -3, 0),
                                 Qt.AlignVCenter | Qt.AlignLeft, txt)

                self._blocs.append((rect, a))

    def _dessiner_drag(self, painter: QPainter):
        """Dessine le bloc fantôme pendant le drag."""
        if (self._drag_planche_id is None or
                self._drag_x_start is None or
                self._drag_x_current is None):
            return

        culture = self.get_culture_active()
        if not culture:
            return

        x1 = min(self._drag_x_start, self._drag_x_current)
        x2 = max(self._drag_x_start, self._drag_x_current)
        y  = self._drag_y

        couleur = QColor(culture.get("couleur_perso") or
                         culture.get("famille_couleur") or "#95A5A6")
        couleur.setAlpha(160)

        rect = QRect(x1 + 1, y + 2, x2 - x1 - 2, H_PLANCHE - 4)
        painter.fillRect(rect, couleur)
        pen = QPen(couleur.darker(130), 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect, 3, 3)

        painter.setPen(Qt.white)
        painter.drawText(rect.adjusted(3, 0, -3, 0),
                         Qt.AlignVCenter | Qt.AlignLeft,
                         culture.get("nom", ""))

    def _dessiner_aujourd_hui(self, painter: QPainter, h_total: int):
        today = date.today()
        if today.year != self.annee:
            return
        sem = date_to_semaine(today.strftime("%Y-%m-%d"), self.annee)
        x = semaine_to_x(sem)
        painter.setPen(QPen(QColor("#DC2626"), 2, Qt.DashLine))
        painter.drawLine(x, 0, x, h_total)
        font_tiny = QFont(); font_tiny.setPointSize(7)
        painter.setFont(font_tiny)
        painter.setPen(QColor("#DC2626"))
        painter.drawText(x + 2, H_ENTETE - 4, "auj.")

    # ──────────────────────────────────────────
    # Interactions souris
    # ──────────────────────────────────────────
    def _planche_at(self, pos: QPoint):
        """Retourne (index_ligne, planche_dict) si la pos est sur une planche."""
        for i, (typ, data) in enumerate(self._lignes):
            if typ != "planche":
                continue
            y = self._y_ligne(i)
            if y <= pos.y() < y + H_PLANCHE and pos.x() > L_NOM:
                return i, data
        return None, None

    def mousePressEvent(self, event):
        pos = event.pos()

        # Clic sur titre parcelle → replier/déplier
        for i, (typ, data) in enumerate(self._lignes):
            y = self._y_ligne(i)
            if typ == "parcelle" and y <= pos.y() < y + H_PARCELLE:
                pid = data["parcelle_id"]
                if pid in self._collapsed:
                    self._collapsed.discard(pid)
                else:
                    self._collapsed.add(pid)
                self._build_lignes()
                self._update_size()
                self.update()
                return

        # Clic droit sur un bloc → menu
        if event.button() == Qt.RightButton:
            for rect, a in self._blocs:
                if rect.contains(pos):
                    self._menu_bloc(a, pos)
                    return

        # Clic gauche sur un bloc → modifier
        if event.button() == Qt.LeftButton:
            for rect, a in self._blocs:
                if rect.contains(pos):
                    if self.peut_ecrire:
                        self.on_modifier(a["id"])
                    return

        # Clic gauche sur une planche vide → début de drag
        if event.button() == Qt.LeftButton and self.peut_ecrire:
            _, planche = self._planche_at(pos)
            if planche:
                self._drag_planche_id = planche["id"]
                self._drag_x_start    = pos.x()
                self._drag_x_current  = pos.x()
                idx, _ = self._planche_at(pos)
                self._drag_y = self._y_ligne(idx)
                self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()

        # Mise à jour hover
        hover = None
        for rect, a in self._blocs:
            if rect.contains(pos):
                hover = a
                break
        if hover != self._hover_bloc:
            self._hover_bloc = hover
            self.setCursor(
                Qt.PointingHandCursor if hover else Qt.CrossCursor
                if (self._drag_planche_id or self.get_culture_active())
                else Qt.ArrowCursor)
            self.update()
            if hover:
                QToolTip.showText(
                    self.mapToGlobal(pos), self._tooltip(hover))

        # Mise à jour drag
        if self._drag_planche_id is not None:
            self._drag_x_current = max(L_NOM, pos.x())
            self.update()

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.LeftButton and
                self._drag_planche_id is not None):
            x1 = min(self._drag_x_start, self._drag_x_current)
            x2 = max(self._drag_x_start, self._drag_x_current)

            # Convertir en semaines
            s1 = (x1 - L_NOM) / L_SEMAINE + 1
            s2 = (x2 - L_NOM) / L_SEMAINE + 1
            s1 = max(1.0, min(52.0, s1))
            s2 = max(s1 + 1, min(53.0, s2))

            planche_id = self._drag_planche_id
            self._drag_planche_id = None
            self._drag_x_start    = None
            self._drag_x_current  = None
            self._drag_y          = None
            self.update()

            self.on_assigner(planche_id, s1, s2)

    def _menu_bloc(self, a: dict, pos: QPoint):
        menu = QMenu(self)
        if self.peut_ecrire:
            menu.addAction("✏ Modifier",
                lambda: self.on_modifier(a["id"]))
        if self.peut_supprimer:
            menu.addAction("🗑 Supprimer",
                lambda: self.on_supprimer(a["id"]))
        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(pos))

    @staticmethod
    def _tooltip(a: dict) -> str:
        lines = [f"<b>{a.get('culture_nom', '—')}</b>"]
        if a.get("variete"):
            lines.append(f"Variété : {a['variete']}")
        if a.get("famille_nom"):
            lines.append(f"Famille : {a['famille_nom']}")
        if a.get("date_semis"):
            lines.append(f"Semis : {a['date_semis']}")
        if a.get("date_premiere_recolte"):
            lines.append(f"1ère récolte : {a['date_premiere_recolte']}")
        if a.get("date_derniere_recolte"):
            lines.append(f"Fin récolte : {a['date_derniere_recolte']}")
        if a.get("rendement_ml"):
            lines.append(f"Rend. : {a['rendement_ml']} kg/ml")
        if a.get("prix_kg"):
            lines.append(f"Prix : {a['prix_kg']} €/kg")
        return "<br>".join(lines)


# ── Dialog : Gérer les planches ───────────────
class DialogGererPlanches(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gérer les planches")
        self.setMinimumWidth(560)
        self.setMinimumHeight(460)
        self._build_ui()
        self._charger_parcelles()

    def _build_ui(self):
        lay = QVBoxLayout(self)

        # Sélection parcelle
        top = QHBoxLayout()
        top.addWidget(QLabel("Parcelle :"))
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.currentIndexChanged.connect(self._charger_planches)
        top.addWidget(self.combo_parcelle, 1)
        lay.addLayout(top)

        # Options génération
        gen_group = QGroupBox("Génération automatique")
        gen_lay = QFormLayout(gen_group)
        gen_lay.setSpacing(8)

        nb_w = QWidget()
        nb_lay = QHBoxLayout(nb_w)
        nb_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_nb_planches = QSpinBox()
        self.inp_nb_planches.setRange(1, 200)
        self.inp_nb_planches.setValue(10)
        self.inp_longueur = QDoubleSpinBox()
        self.inp_longueur.setRange(0, 200)
        self.inp_longueur.setDecimals(1)
        self.inp_longueur.setSuffix(" m")
        self.inp_longueur.setValue(30)
        self.inp_largeur = QDoubleSpinBox()
        self.inp_largeur.setRange(0, 10)
        self.inp_largeur.setDecimals(2)
        self.inp_largeur.setSuffix(" m")
        self.inp_largeur.setValue(1.20)
        nb_lay.addWidget(QLabel("N° :"))
        nb_lay.addWidget(self.inp_nb_planches)
        nb_lay.addWidget(QLabel("L :"))
        nb_lay.addWidget(self.inp_longueur)
        nb_lay.addWidget(QLabel("l :"))
        nb_lay.addWidget(self.inp_largeur)
        gen_lay.addRow("Planches :", nb_w)

        self.chk_sous_abris = QCheckBox("Sous abris (serre, tunnel...)")
        gen_lay.addRow(self.chk_sous_abris)

        self.inp_sous_parcelle = QLineEdit()
        self.inp_sous_parcelle.setPlaceholderText(
            "Ex: Serre A - Chapelle 1 (optionnel)")
        gen_lay.addRow("Sous-zone :", self.inp_sous_parcelle)

        btn_gen = QPushButton("⚡ Générer")
        btn_gen.setStyleSheet("""
            QPushButton { background:#2563EB; color:white;
                border-radius:4px; padding:4px 14px; }
        """)
        btn_gen.clicked.connect(self._generer)
        gen_lay.addRow(btn_gen)
        lay.addWidget(gen_group)

        # Tableau planches
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "N°", "Longueur (m)", "Largeur (m)",
            "Sous-abris", "Sous-zone", "Notes"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        for i in range(4):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        lay.addWidget(self.table, 1)

        btns_tab = QHBoxLayout()
        btn_add = QPushButton("+ Ajouter ligne")
        btn_add.clicked.connect(self._ajouter_ligne)
        btn_del = QPushButton("− Supprimer")
        btn_del.clicked.connect(self._supprimer_ligne)
        btns_tab.addWidget(btn_add)
        btns_tab.addWidget(btn_del)
        btns_tab.addStretch()
        lay.addLayout(btns_tab)

        btns = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Close)
        btns.button(QDialogButtonBox.Save).setText("💾 Enregistrer")
        btns.accepted.connect(self._sauver)
        btns.rejected.connect(self.accept)
        lay.addWidget(btns)

    def _charger_parcelles(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            self.combo_parcelle.clear()
            for row in cur.fetchall():
                self.combo_parcelle.addItem(row[1], row[0])
            cur.close()
        except Exception:
            traceback.print_exc()

    def _charger_planches(self):
        pid = self.combo_parcelle.currentData()
        if not pid:
            return
        planches = get_planches_parcelle(pid)
        self.table.setRowCount(0)
        for pl in planches:
            self._ajouter_ligne_data(pl)

    def _ajouter_ligne_data(self, pl: dict = None):
        r = self.table.rowCount()
        self.table.insertRow(r)

        num = pl["numero"] if pl else r + 1
        self.table.setItem(r, 0, QTableWidgetItem(str(num)))
        self.table.setItem(r, 1,
            QTableWidgetItem(str(pl.get("longueur_m") or "") if pl else ""))
        self.table.setItem(r, 2,
            QTableWidgetItem(str(pl.get("largeur_m") or "") if pl else ""))

        chk = QCheckBox()
        chk.setChecked(bool(pl.get("sous_abris")) if pl else False)
        self.table.setCellWidget(r, 3, chk)

        self.table.setItem(r, 4,
            QTableWidgetItem(pl.get("sous_parcelle") or "" if pl else ""))
        self.table.setItem(r, 5,
            QTableWidgetItem(pl.get("notes") or "" if pl else ""))

        if pl:
            self.table.item(r, 0).setData(Qt.UserRole, pl["id"])

    def _ajouter_ligne(self):
        self._ajouter_ligne_data()

    def _supprimer_ligne(self):
        rows = sorted(
            set(i.row() for i in self.table.selectedItems()),
            reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _generer(self):
        nb  = self.inp_nb_planches.value()
        lon = self.inp_longueur.value()
        lar = self.inp_largeur.value()
        sous_abris    = self.chk_sous_abris.isChecked()
        sous_parcelle = self.inp_sous_parcelle.text().strip() or None

        self.table.setRowCount(0)
        for i in range(nb):
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(i + 1)))
            self.table.setItem(r, 1, QTableWidgetItem(str(lon)))
            self.table.setItem(r, 2, QTableWidgetItem(str(lar)))
            chk = QCheckBox()
            chk.setChecked(sous_abris)
            self.table.setCellWidget(r, 3, chk)
            self.table.setItem(r, 4,
                QTableWidgetItem(sous_parcelle or ""))
            self.table.setItem(r, 5, QTableWidgetItem(""))

    def _sauver(self):
        pid = self.combo_parcelle.currentData()
        if not pid:
            return
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, numero FROM planches WHERE parcelle_id=?", (pid,))
            existants = {row[1]: row[0] for row in cur.fetchall()}
            numeros_gardes = set()

            for r in range(self.table.rowCount()):
                try:
                    num = int(self.table.item(r, 0).text())
                except Exception:
                    continue

                lon_txt = (self.table.item(r, 1).text()
                           if self.table.item(r, 1) else "")
                lar_txt = (self.table.item(r, 2).text()
                           if self.table.item(r, 2) else "")
                chk = self.table.cellWidget(r, 3)
                sous_abris = 1 if (chk and chk.isChecked()) else 0
                sous_parcelle = (self.table.item(r, 4).text()
                                 if self.table.item(r, 4) else "") or None
                notes = (self.table.item(r, 5).text()
                         if self.table.item(r, 5) else "") or None
                lon = float(lon_txt) if lon_txt else None
                lar = float(lar_txt) if lar_txt else None
                numeros_gardes.add(num)

                if num in existants:
                    cur.execute("""
                        UPDATE planches
                        SET longueur_m=?, largeur_m=?, sous_abris=?,
                            sous_parcelle=?, notes=?
                        WHERE id=?
                    """, (lon, lar, sous_abris, sous_parcelle,
                          notes, existants[num]))
                else:
                    cur.execute("""
                        INSERT INTO planches
                            (parcelle_id, numero, longueur_m, largeur_m,
                             sous_abris, sous_parcelle, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (pid, num, lon, lar, sous_abris,
                          sous_parcelle, notes))

            # Supprimer planches retirées (si pas d'assolement lié)
            for num, planche_id in existants.items():
                if num not in numeros_gardes:
                    cur.execute(
                        "SELECT COUNT(*) FROM assolement WHERE planche_id=?",
                        (planche_id,))
                    if cur.fetchone()[0] == 0:
                        cur.execute(
                            "DELETE FROM planches WHERE id=?", (planche_id,))
                    else:
                        QMessageBox.warning(self, "Planche non supprimée",
                            f"La planche {num} a des cultures — "
                            "supprimez-les d'abord.")

            conn.commit()
            cur.close()
            self._charger_planches()
        except Exception:
            traceback.print_exc()


# ── Dialog : Ajouter/modifier une culture ─────
class DialogCultureAssolement(QDialog):
    def __init__(self, annee: int,
                 planche_id_preselect: int = None,
                 culture_ref_id_preselect: int = None,
                 date_semis_preselect: date = None,
                 date_fin_preselect: date = None,
                 assolement_id: int = None,
                 parent=None):
        super().__init__(parent)
        self.annee                  = annee
        self.planche_id_preselect   = planche_id_preselect
        self.culture_ref_id_preselect = culture_ref_id_preselect
        self.date_semis_preselect   = date_semis_preselect
        self.date_fin_preselect     = date_fin_preselect
        self.assolement_id          = assolement_id
        self.setWindowTitle(
            "Modifier la culture" if assolement_id else "Ajouter une culture")
        self.setMinimumWidth(480)
        self._build_ui()
        self._charger_combos()
        if assolement_id:
            self._charger_existant(assolement_id)
        else:
            self._preselectionner()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)

        # Planche
        self.combo_planche = QComboBox()
        form.addRow("Planche *", self.combo_planche)

        # Culture
        cult_w = QWidget()
        cl = QHBoxLayout(cult_w)
        cl.setContentsMargins(0, 0, 0, 0)
        self.combo_culture = QComboBox()
        self.combo_culture.setMinimumWidth(200)
        btn_new = QPushButton("+")
        btn_new.setFixedWidth(28)
        btn_new.setToolTip("Créer une culture dans le référentiel")
        btn_new.clicked.connect(self._creer_culture)
        cl.addWidget(self.combo_culture, 1)
        cl.addWidget(btn_new)
        form.addRow("Culture *", cult_w)

        # Variété
        self.inp_variete = QLineEdit()
        self.inp_variete.setPlaceholderText("Optionnel")
        form.addRow("Variété", self.inp_variete)

        # Mode de plantation
        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Semis direct", "semis_direct")
        self.combo_mode.addItem("Plant fait maison", "plant_fait")
        self.combo_mode.addItem("Plant acheté", "plant_achete")
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        form.addRow("Mode plantation", self.combo_mode)

        # Dates — label dynamique selon mode
        self.lbl_date_debut = QLabel("Date de semis")
        self.inp_date_debut = QDateEdit(QDate(self.annee, 3, 1))
        self.inp_date_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_debut.setCalendarPopup(True)
        form.addRow(self.lbl_date_debut, self.inp_date_debut)

        self.inp_prem_recolte = QDateEdit(QDate(self.annee, 6, 1))
        self.inp_prem_recolte.setDisplayFormat("dd/MM/yyyy")
        self.inp_prem_recolte.setCalendarPopup(True)
        form.addRow("1ère récolte", self.inp_prem_recolte)

        self.inp_dern_recolte = QDateEdit(QDate(self.annee, 9, 30))
        self.inp_dern_recolte.setDisplayFormat("dd/MM/yyyy")
        self.inp_dern_recolte.setCalendarPopup(True)
        form.addRow("Dernière récolte", self.inp_dern_recolte)

        # Séries
        ser_w = QWidget()
        sl = QHBoxLayout(ser_w)
        sl.setContentsMargins(0, 0, 0, 0)
        self.inp_nb_series = QSpinBox()
        self.inp_nb_series.setRange(1, 52)
        self.inp_nb_series.setValue(1)
        self.inp_intervalle = QSpinBox()
        self.inp_intervalle.setRange(0, 52)
        self.inp_intervalle.setSuffix(" sem.")
        self.inp_intervalle.setSpecialValueText("Série unique")
        sl.addWidget(QLabel("Nb :"))
        sl.addWidget(self.inp_nb_series)
        sl.addWidget(QLabel("Intervalle :"))
        sl.addWidget(self.inp_intervalle)
        form.addRow("Séries", ser_w)

        # Rendement & prix
        rend_w = QWidget()
        rl = QHBoxLayout(rend_w)
        rl.setContentsMargins(0, 0, 0, 0)
        self.inp_rendement = QDoubleSpinBox()
        self.inp_rendement.setRange(0, 99999)
        self.inp_rendement.setDecimals(2)
        self.inp_rendement.setSuffix(" kg/ml")
        self.inp_prix = QDoubleSpinBox()
        self.inp_prix.setRange(0, 9999)
        self.inp_prix.setDecimals(2)
        self.inp_prix.setSuffix(" €/kg")
        rl.addWidget(self.inp_rendement)
        rl.addWidget(QLabel("  Prix :"))
        rl.addWidget(self.inp_prix)
        form.addRow("Rendement", rend_w)

        self.inp_notes = QTextEdit()
        self.inp_notes.setMaximumHeight(55)
        form.addRow("Notes", self.inp_notes)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        form.addRow(self.lbl_err)

        lay.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _on_mode_changed(self):
        mode = self.combo_mode.currentData()
        if mode == "semis_direct":
            self.lbl_date_debut.setText("Date de semis")
        else:
            self.lbl_date_debut.setText("Date de mise en place")

    def _charger_combos(self):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                SELECT pl.id, pl.numero, pl.longueur_m,
                       pl.sous_parcelle, p.nom
                FROM planches pl
                JOIN parcelles p ON p.id = pl.parcelle_id
                WHERE p.actif = 1
                ORDER BY p.nom, pl.numero
            """)
            self.combo_planche.clear()
            for row in cur.fetchall():
                label = f"{row[4]} — Planche {row[1]}"
                if row[3]:
                    label = f"{row[4]} — {row[3]} — Planche {row[1]}"
                if row[2]:
                    label += f" ({row[2]}m)"
                self.combo_planche.addItem(label, row[0])
            cur.close()
        except Exception:
            traceback.print_exc()

        cultures = get_cultures_ref()
        self.combo_culture.clear()
        for c in cultures:
            label = c["nom"]
            if c.get("famille_nom"):
                label += f"  ({c['famille_nom']})"
            self.combo_culture.addItem(label, c["id"])

    def _preselectionner(self):
        if self.planche_id_preselect:
            for i in range(self.combo_planche.count()):
                if self.combo_planche.itemData(i) == self.planche_id_preselect:
                    self.combo_planche.setCurrentIndex(i)
                    break
        if self.culture_ref_id_preselect:
            for i in range(self.combo_culture.count()):
                if self.combo_culture.itemData(i) == self.culture_ref_id_preselect:
                    self.combo_culture.setCurrentIndex(i)
                    break
        if self.date_semis_preselect:
            d = self.date_semis_preselect
            self.inp_date_debut.setDate(QDate(d.year, d.month, d.day))
        if self.date_fin_preselect:
            d = self.date_fin_preselect
            self.inp_dern_recolte.setDate(QDate(d.year, d.month, d.day))

    def _charger_existant(self, aid: int):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT * FROM assolement WHERE id=?", (aid,))
            a = dict(cur.fetchone())
            cur.close()

            for i in range(self.combo_planche.count()):
                if self.combo_planche.itemData(i) == a["planche_id"]:
                    self.combo_planche.setCurrentIndex(i); break
            for i in range(self.combo_culture.count()):
                if self.combo_culture.itemData(i) == a["culture_ref_id"]:
                    self.combo_culture.setCurrentIndex(i); break

            self.inp_variete.setText(a.get("variete") or "")
            idx = self.combo_mode.findData(a.get("mode_plantation","semis_direct"))
            self.combo_mode.setCurrentIndex(max(0, idx))

            def _set_date(widget, val):
                if val:
                    try:
                        dt = datetime.strptime(val, "%Y-%m-%d")
                        widget.setDate(QDate(dt.year, dt.month, dt.day))
                    except Exception:
                        pass

            _set_date(self.inp_date_debut, a.get("date_semis"))
            _set_date(self.inp_prem_recolte, a.get("date_premiere_recolte"))
            _set_date(self.inp_dern_recolte, a.get("date_derniere_recolte"))
            self.inp_nb_series.setValue(a.get("nb_series") or 1)
            self.inp_intervalle.setValue(a.get("intervalle_semaines") or 0)
            self.inp_rendement.setValue(a.get("rendement_ml") or 0)
            self.inp_prix.setValue(a.get("prix_kg") or 0)
            self.inp_notes.setPlainText(a.get("notes") or "")
        except Exception:
            traceback.print_exc()

    def _creer_culture(self):
        dlg = DialogCultureRef(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_combos()

    def _valider(self):
        planche_id     = self.combo_planche.currentData()
        culture_ref_id = self.combo_culture.currentData()
        if not planche_id:
            self.lbl_err.setText("Sélectionnez une planche.")
            return
        if not culture_ref_id:
            self.lbl_err.setText("Sélectionnez une culture.")
            return

        variete    = self.inp_variete.text().strip() or None
        mode       = self.combo_mode.currentData()
        date_debut = self.inp_date_debut.date().toString("yyyy-MM-dd")
        date_prem  = self.inp_prem_recolte.date().toString("yyyy-MM-dd")
        date_dern  = self.inp_dern_recolte.date().toString("yyyy-MM-dd")
        nb_series  = self.inp_nb_series.value()
        intervalle = self.inp_intervalle.value() or None
        rendement  = self.inp_rendement.value() or None
        prix       = self.inp_prix.value() or None
        notes      = self.inp_notes.toPlainText().strip() or None

        try:
            conn = get_connection()
            cur  = conn.cursor()
            if self.assolement_id:
                cur.execute("""
                    UPDATE assolement SET
                        planche_id=?, culture_ref_id=?, variete=?, annee=?,
                        date_semis=?, date_premiere_recolte=?,
                        date_derniere_recolte=?, nb_series=?,
                        intervalle_semaines=?, mode_plantation=?,
                        rendement_ml=?, prix_kg=?, notes=?
                    WHERE id=?
                """, (planche_id, culture_ref_id, variete, self.annee,
                      date_debut, date_prem, date_dern,
                      nb_series, intervalle, mode,
                      rendement, prix, notes, self.assolement_id))
            else:
                cur.execute("""
                    INSERT INTO assolement
                        (planche_id, culture_ref_id, variete, annee,
                         date_semis, date_premiere_recolte,
                         date_derniere_recolte, nb_series,
                         intervalle_semaines, mode_plantation,
                         rendement_ml, prix_kg, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (planche_id, culture_ref_id, variete, self.annee,
                      date_debut, date_prem, date_dern,
                      nb_series, intervalle, mode,
                      rendement, prix, notes))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")


# ── Dialog : Référentiel cultures ─────────────
class DialogCultureRef(QDialog):
    def __init__(self, culture_id: int = None, parent=None):
        super().__init__(parent)
        self.culture_id = culture_id
        self.setWindowTitle(
            "Modifier la culture" if culture_id else "Nouvelle culture")
        self.setMinimumWidth(360)
        self._build_ui()
        if culture_id:
            self._charger(culture_id)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_nom = QLineEdit()
        self.inp_nom.setPlaceholderText("Ex: Tomate, Carotte, Poireau...")
        form.addRow("Nom *", self.inp_nom)

        self.combo_famille = QComboBox()
        self.combo_famille.addItem("— Non classé —", None)
        for fam in get_familles():
            self.combo_famille.addItem(fam["nom"], fam["id"])
        form.addRow("Famille botanique", self.combo_famille)

        coul_w = QWidget()
        cl = QHBoxLayout(coul_w)
        cl.setContentsMargins(0, 0, 0, 0)
        self.inp_couleur = QLineEdit()
        self.inp_couleur.setPlaceholderText("#RRGGBB (optionnel)")
        self.inp_couleur.setMaxLength(7)
        self.inp_couleur.setFixedWidth(90)
        self.btn_couleur = QPushButton("  ")
        self.btn_couleur.setFixedSize(28, 28)
        self.btn_couleur.clicked.connect(self._choisir_couleur)
        self.inp_couleur.textChanged.connect(self._maj_apercu)
        cl.addWidget(self.inp_couleur)
        cl.addWidget(self.btn_couleur)
        cl.addStretch()
        form.addRow("Couleur perso", coul_w)

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

    def _charger(self, cid: int):
        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("SELECT * FROM cultures_ref WHERE id=?", (cid,))
            c = dict(cur.fetchone())
            cur.close()
            self.inp_nom.setText(c.get("nom", ""))
            idx = self.combo_famille.findData(c.get("famille_id"))
            self.combo_famille.setCurrentIndex(max(0, idx))
            self.inp_couleur.setText(c.get("couleur_perso") or "")
            self.inp_notes.setText(c.get("notes") or "")
        except Exception:
            traceback.print_exc()

    def _choisir_couleur(self):
        c = QColorDialog.getColor(
            QColor(self.inp_couleur.text() or "#95A5A6"), self)
        if c.isValid():
            self.inp_couleur.setText(c.name())

    def _maj_apercu(self, txt: str):
        if len(txt) == 7 and txt.startswith("#"):
            self.btn_couleur.setStyleSheet(
                f"background: {txt}; border: 1px solid #d1d5db;")

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            self.lbl_err.setText("Le nom est obligatoire.")
            return
        famille_id = self.combo_famille.currentData()
        couleur    = self.inp_couleur.text().strip() or None
        notes      = self.inp_notes.text().strip() or None
        try:
            conn = get_connection()
            cur  = conn.cursor()
            if self.culture_id:
                cur.execute("""
                    UPDATE cultures_ref SET
                        nom=?, famille_id=?, couleur_perso=?, notes=?
                    WHERE id=?
                """, (nom, famille_id, couleur, notes, self.culture_id))
            else:
                cur.execute("""
                    INSERT INTO cultures_ref
                        (nom, famille_id, couleur_perso, notes)
                    VALUES (?, ?, ?, ?)
                """, (nom, famille_id, couleur, notes))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")