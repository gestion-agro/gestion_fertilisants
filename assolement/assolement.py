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

H_ENTETE   = 36
H_PARCELLE = 28
H_PLANCHE  = 28
L_NOM      = 200
L_SEMAINE  = 18
W_PALETTE  = 220

MOIS_COURTS = ["Jan","Fév","Mar","Avr","Mai","Jun",
                "Jul","Aoû","Sep","Oct","Nov","Déc"]


def semaine_to_x(semaine: float) -> int:
    return L_NOM + int((semaine - 1) * L_SEMAINE)


def date_to_semaine(d: str, annee: int) -> float:
    try:
        dt = datetime.strptime(d, "%Y-%m-%d").date()
    except Exception:
        return 1.0
    debut = date(annee, 1, 1)
    if dt.year < annee: return 1.0
    if dt.year > annee: return 53.0
    total = 366 if annee % 4 == 0 else 365
    return 1.0 + (dt - debut).days / total * 52.0


def semaine_to_date(semaine: float, annee: int) -> date:
    debut = date(annee, 1, 1)
    total = 366 if annee % 4 == 0 else 365
    jours = int((semaine - 1) / 52.0 * total)
    return debut + timedelta(days=jours)


def couleur_texte(hex_couleur: str) -> str:
    try:
        c = hex_couleur.lstrip("#")
        r, g, b = int(c[0:2],16), int(c[2:4],16), int(c[4:6],16)
        return "#ffffff" if 0.299*r + 0.587*g + 0.114*b < 140 else "#1f2937"
    except Exception:
        return "#ffffff"


# ── Page principale ───────────────────────────
class AssolementPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user    = current_user
        self._peut_ecrire    = peut_action(current_user, "parcelles", "ecriture")
        self._peut_supprimer = peut_action(current_user, "parcelles", "suppression")
        self._annee          = datetime.now().year
        self._culture_active = None
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        barre = QHBoxLayout()
        titre = QLabel("Plan d'assolement")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        titre.setFont(f)
        barre.addWidget(titre)
        barre.addStretch()

        barre.addWidget(QLabel("Année :"))
        self.combo_annee = QComboBox()
        for a in range(self._annee - 4, self._annee + 3):
            self.combo_annee.addItem(str(a), a)
        self.combo_annee.setCurrentText(str(self._annee))
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
            btn_planches.setStyleSheet(
                "QPushButton{background:#2563EB;color:white;"
                "border-radius:4px;padding:4px 10px;}"
                "QPushButton:hover{background:#1d4ed8;}")
            barre.addWidget(btn_planches)

        root.addLayout(barre)

        corps = QHBoxLayout(); corps.setSpacing(0)

        self.palette = PaletteCultures(
            peut_ecrire=self._peut_ecrire,
            on_select=self._on_culture_selectionnee,
            on_nouvelle_culture=self._dialog_nouvelle_culture)
        self.palette.setFixedWidth(W_PALETTE)
        corps.addWidget(self.palette)

        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#e5e7eb;")
        corps.addWidget(sep)

        droite = QWidget()
        dl = QVBoxLayout(droite)
        dl.setContentsMargins(0,0,0,0); dl.setSpacing(0)

        self.grille_scroll = QScrollArea()
        self.grille_scroll.setWidgetResizable(False)
        self.grille_scroll.setFrameShape(QFrame.NoFrame)
        self.grille_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.canvas = GrilleCanvas(
            annee=self._annee,
            peut_ecrire=self._peut_ecrire,
            peut_supprimer=self._peut_supprimer,
            on_modifier=self._dialog_modifier,
            on_supprimer=self._supprimer_culture,
            on_drop_serie=self._placer_serie,
            on_detail=self._afficher_detail_culture,
        )
        self.grille_scroll.setWidget(self.canvas)
        dl.addWidget(self.grille_scroll, 1)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color:#e5e7eb;")
        dl.addWidget(sep2)

        lbl_ser = QLabel("📋 Séries — glisser vers le calendrier")
        lbl_ser.setStyleSheet(
            "font-size:10px;color:#6b7280;padding:2px 4px;background:#f8fafc;")
        dl.addWidget(lbl_ser)

        self.series_scroll = QScrollArea()
        self.series_scroll.setFrameShape(QFrame.NoFrame)
        self.series_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.series_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.zone_series = ZoneSeries()
        self.series_scroll.setWidget(self.zone_series)
        self.series_scroll.setMaximumHeight(200)
        dl.addWidget(self.series_scroll)

        self.grille_scroll.horizontalScrollBar().valueChanged.connect(
            self.series_scroll.horizontalScrollBar().setValue)
        self.series_scroll.horizontalScrollBar().valueChanged.connect(
            self.grille_scroll.horizontalScrollBar().setValue)

        corps.addWidget(droite, 1)

        # Panneau détail à droite
        self.panneau_detail = PanneauDetail()
        self.panneau_detail.setFixedWidth(240)
        self.panneau_detail.hide()
        corps.addWidget(self.panneau_detail)

        root.addLayout(corps, 1)
        
        self.lbl_statut = QLabel(
            "💡 Glissez une série depuis la zone du bas vers une planche")
        self.lbl_statut.setStyleSheet("color:#6b7280;font-size:11px;")
        root.addWidget(self.lbl_statut)

    def _on_culture_selectionnee(self, culture: dict):
        self._culture_active = culture

    def _on_annee_changed(self):
        self._annee = self.combo_annee.currentData()
        self.canvas.annee = self._annee
        self._charger_grille()

    def _dialog_nouvelle_culture(self):
        dlg = DialogCultureAssolement(annee=self._annee, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.palette.recharger()
            self._charger_grille()

    def _dialog_modifier(self, assolement_id: int):
        dlg = DialogCultureAssolement(
            annee=self._annee, assolement_id=assolement_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_grille()

    def _supprimer_culture(self, assolement_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer cette culture de l'assolement ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection(); cur = conn.cursor()
                cur.execute("DELETE FROM assolement WHERE id=?", (assolement_id,))
                conn.commit(); cur.close()
                self._charger_grille()
            except Exception:
                traceback.print_exc()

    def _placer_serie(self, assol_id: int, planche_id, semaine: float):
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("UPDATE assolement SET planche_id=? WHERE id=?",
                        (planche_id, assol_id))
            conn.commit(); cur.close()
            self._charger_grille()
        except Exception:
            traceback.print_exc()
    def _dialog_gerer_planches(self):
        dlg = DialogGererPlanches(parent=self)
        dlg.exec()
        self._charger()

    def _charger(self):
        self._charger_combo_parcelles()
        self.palette.recharger()
        self._charger_grille()

    def _charger_combo_parcelles(self):
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
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
        annee = self._annee
        parcelle_id = self.combo_parcelle.currentData()
        try:
            conn = get_connection(); cur = conn.cursor()
            if parcelle_id:
                cur.execute("""
                    SELECT pl.*, p.nom AS parcelle_nom, p.id AS parcelle_id
                    FROM planches pl JOIN parcelles p ON p.id=pl.parcelle_id
                    WHERE pl.parcelle_id=? ORDER BY p.nom, pl.numero
                """, (parcelle_id,))
            else:
                cur.execute("""
                    SELECT pl.*, p.nom AS parcelle_nom, p.id AS parcelle_id
                    FROM planches pl JOIN parcelles p ON p.id=pl.parcelle_id
                    WHERE p.actif=1 ORDER BY p.nom, pl.numero
                """)
            planches = [dict(r) for r in cur.fetchall()]
            cur.close()
        except Exception:
            traceback.print_exc()
            planches = []

        placees = [a for a in get_assolement_annee(annee, parcelle_id)
                   if a.get("planche_id")]

        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("""
                SELECT a.*, cr.nom AS culture_nom,
                       cr.couleur_perso AS culture_couleur_perso,
                       fb.nom AS famille_nom, fb.couleur_hex AS famille_couleur
                FROM assolement a
                JOIN cultures_ref cr ON cr.id=a.culture_ref_id
                LEFT JOIN familles_botaniques fb ON fb.id=cr.famille_id
                WHERE a.annee=? AND a.planche_id IS NULL
                ORDER BY a.date_semis
            """, (annee,))
            non_placees = [dict(r) for r in cur.fetchall()]
            cur.close()
        except Exception:
            traceback.print_exc()
            non_placees = []

        self.canvas.charger(planches, placees)
        self.zone_series.charger(non_placees, annee)
        self.zone_series.setMinimumWidth(L_NOM + 52*L_SEMAINE + 20)
        nb = max(len(non_placees), 1)
        self.series_scroll.setFixedHeight(min(nb * 28, 200))

    def _afficher_detail_culture(self, a: dict):
        self.panneau_detail.charger(a)
        self.panneau_detail.show()

    def recharger(self):
        self._charger()

# ── Zone séries ───────────────────────────────
class ZoneSeries(QWidget):
    MIME_TYPE = "application/x-assol-id"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series = []
        self._annee  = datetime.now().year
        self._hover  = None
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumWidth(L_NOM + 52*L_SEMAINE + 20)
        self.setMinimumHeight(H_PLANCHE)

    def charger(self, series: list, annee: int):
        self._series = series
        self._annee  = annee
        nb = max(len(series), 1)
        self.setFixedHeight(nb * H_PLANCHE)
        self.update()

    def _rects(self):
        rects = []
        for idx, a in enumerate(self._series):
            s1 = date_to_semaine(
                a.get("date_semis") or f"{self._annee}-01-01", self._annee)
            s2 = date_to_semaine(
                a.get("date_derniere_recolte") or f"{self._annee}-12-31",
                self._annee)
            if s2 <= s1: s2 = s1+8
            x1 = semaine_to_x(s1); x2 = semaine_to_x(min(s2, 53))
            if x2-x1 < 14: x2 = x1+14
            y = idx * H_PLANCHE
            rects.append((QRect(x1+1, y+2, x2-x1-2, H_PLANCHE-4), a))
        return rects

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = L_NOM + 52*L_SEMAINE
        h = max(len(self._series), 1) * H_PLANCHE
        painter.fillRect(0, 0, w, h, QColor("#f8fafc"))

        # Col nom
        painter.fillRect(0, 0, L_NOM, h, QColor("#f3f4f6"))
        f = QFont(); f.setPointSize(8); painter.setFont(f)
        painter.setPen(QColor("#6b7280"))
        if not self._series:
            painter.drawText(QRect(0,0,L_NOM,H_PLANCHE),
                             Qt.AlignCenter, "Non placées")

        # Grille semaines
        painter.setPen(QPen(QColor("#f0f0f0"), 1))
        for s in range(1, 53):
            painter.drawLine(semaine_to_x(s), 0, semaine_to_x(s), h)

        # Séparateurs lignes
        painter.setPen(QPen(QColor("#e5e7eb"), 1))
        for idx in range(len(self._series)):
            y = idx * H_PLANCHE
            painter.drawLine(0, y, w, y)
            # Label "Non placée" dans la col nom
            painter.setPen(QColor("#9ca3af"))
            painter.drawText(QRect(4, y, L_NOM-8, H_PLANCHE),
                             Qt.AlignVCenter|Qt.AlignLeft, "◌ En attente")
            painter.setPen(QPen(QColor("#e5e7eb"), 1))

        # Badges
        fb = QFont(); fb.setPointSize(8); painter.setFont(fb)
        for rect, a in self._rects():
            hex_c = get_couleur_culture(a)
            couleur = QColor(hex_c)
            if self._hover and self._hover.get("id") == a.get("id"):
                couleur = couleur.lighter(115)
            painter.fillRect(rect, couleur)
            painter.setPen(QPen(QColor(hex_c).darker(130), 1))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(QColor(couleur_texte(hex_c)))
            nom = a.get("culture_nom","")
            if a.get("variete"): nom += f" · {a['variete']}"
            if a.get("longueur_planche_m"):
                nom += f" ({a['longueur_planche_m']:.0f}m)"
            nom = painter.fontMetrics().elidedText(
                nom, Qt.ElideRight, rect.width()-6)
            painter.drawText(rect.adjusted(3,0,-3,0),
                             Qt.AlignVCenter|Qt.AlignLeft, nom)
        painter.end()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        hover = None
        for rect, a in self._rects():
            if rect.contains(pos): hover = a; break
        if hover != self._hover:
            self._hover = hover
            self.setCursor(Qt.OpenHandCursor if hover else Qt.ArrowCursor)
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            for rect, a in self._blocs:
                if rect.contains(pos):
                    if self.peut_ecrire:
                        self.on_modifier(a["id"])
                    return
    
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        pos = event.pos()
        for rect, a in self._rects():
            if rect.contains(pos):
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData(self.MIME_TYPE, str(a["id"]).encode())
                drag.setMimeData(mime)
                hex_c = get_couleur_culture(a)
                pm = QPixmap(rect.width(), rect.height())
                pm.fill(Qt.transparent)
                p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
                p.fillRect(pm.rect(), QColor(hex_c))
                p.setPen(QColor(couleur_texte(hex_c)))
                fnt = QFont(); fnt.setPointSize(8); p.setFont(fnt)
                p.drawText(pm.rect().adjusted(3,0,-3,0),
                           Qt.AlignVCenter|Qt.AlignLeft, a.get("culture_nom",""))
                p.end()
                drag.setPixmap(pm)
                drag.setHotSpot(pos - rect.topLeft())
                drag.exec(Qt.MoveAction)
                return

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.MIME_TYPE): return
        try:
            assol_id = int(event.mimeData().data(self.MIME_TYPE).data())
        except Exception: return
        # Remettre en attente → planche_id = NULL
        try:
            from db import get_connection
            conn = get_connection(); cur = conn.cursor()
            cur.execute("UPDATE assolement SET planche_id=NULL WHERE id=?",
                        (assol_id,))
            conn.commit(); cur.close()
            # Déclencher rechargement via le parent
            p = self.parent()
            while p:
                if hasattr(p, '_charger_grille'):
                    p._charger_grille()
                    break
                p = p.parent() if hasattr(p, 'parent') else None
        except Exception:
            import traceback; traceback.print_exc()
        event.acceptProposedAction()


# ── Palette cultures ──────────────────────────
class PaletteCultures(QWidget):
    def __init__(self, peut_ecrire: bool, on_select,
                 on_nouvelle_culture, parent=None):
        super().__init__(parent)
        self.peut_ecrire         = peut_ecrire
        self.on_select           = on_select
        self.on_nouvelle_culture = on_nouvelle_culture
        self._build_ui()
        self.recharger()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6,6,6,6); lay.setSpacing(6)
        lbl = QLabel("Cultures")
        f = QFont(); f.setBold(True); f.setPointSize(11); lbl.setFont(f)
        lay.addWidget(lbl)
        self.inp_recherche = QLineEdit()
        self.inp_recherche.setPlaceholderText("🔍 Rechercher...")
        self.inp_recherche.textChanged.connect(self._filtrer)
        lay.addWidget(self.inp_recherche)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        self._liste_widget = QWidget()
        self._liste_lay = QVBoxLayout(self._liste_widget)
        self._liste_lay.setSpacing(3); self._liste_lay.setContentsMargins(0,0,0,0)
        self._liste_lay.addStretch()
        scroll.setWidget(self._liste_widget)
        lay.addWidget(scroll, 1)
        if self.peut_ecrire:
            btn_new = QPushButton("+ Nouvelle culture")
            btn_new.setStyleSheet(
                "QPushButton{background:#16a34a;color:white;"
                "border-radius:4px;padding:4px;font-size:11px;}"
                "QPushButton:hover{background:#15803d;}")
            btn_new.clicked.connect(self.on_nouvelle_culture)
            lay.addWidget(btn_new)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine); lay.addWidget(sep)
        lbl_fam = QLabel("Familles botaniques :")
        lbl_fam.setStyleSheet("font-size:10px;color:#6b7280;")
        lay.addWidget(lbl_fam)
        self._legende_lay = QVBoxLayout()
        self._legende_lay.setSpacing(2)
        lay.addLayout(self._legende_lay)

    def recharger(self):
        self._cultures = get_cultures_ref()
        self._filtrer(self.inp_recherche.text())
        self._build_legende()

    def _filtrer(self, texte: str = ""):
        while self._liste_lay.count() > 1:
            item = self._liste_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        filtre = texte.lower().strip()
        for c in self._cultures:
            if filtre and filtre not in c["nom"].lower(): continue
            btn = self._make_btn(c)
            self._liste_lay.insertWidget(self._liste_lay.count()-1, btn)

    def _make_btn(self, c: dict) -> QPushButton:
        hex_c = c.get("couleur_perso") or c.get("famille_couleur") or "#95A5A6"
        nom = c["nom"]
        if c.get("famille_nom"): nom += f"\n{c['famille_nom']}"
        btn = QPushButton(nom)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{hex_c}22; border:2px solid {hex_c};
                border-radius:4px; color:#1f2937;
                text-align:left; padding:4px 8px; font-size:11px;
            }}
            QPushButton:hover {{ background:{hex_c}33; }}
        """)
        btn.setCursor(Qt.ArrowCursor)
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(
            lambda pos, cult=c, b=btn: self._menu(cult, b, pos))
        return btn

    def _menu(self, c: dict, btn, pos):
        if not self.peut_ecrire: return
        menu = QMenu(self)
        menu.addAction("✏ Modifier", lambda: self._modifier(c))
        menu.exec(btn.mapToGlobal(pos))

    def _modifier(self, c: dict):
        dlg = DialogCultureRef(culture_id=c["id"], parent=self)
        if dlg.exec() == QDialog.Accepted: self.recharger()

    def _build_legende(self):
        while self._legende_lay.count():
            item = self._legende_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for fam in get_familles():
            w = QWidget(); hl = QHBoxLayout(w)
            hl.setContentsMargins(0,0,0,0); hl.setSpacing(4)
            carre = QLabel("■")
            carre.setStyleSheet(f"color:{fam['couleur_hex']};font-size:14px;")
            lbl = QLabel(fam["nom"])
            lbl.setStyleSheet("font-size:10px;color:#374151;")
            hl.addWidget(carre); hl.addWidget(lbl); hl.addStretch()
            self._legende_lay.addWidget(w)

class PanneauDetail(QWidget):
    """Panneau latéral droit affichant les infos d'une culture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#f8fafc; border-left:1px solid #e5e7eb;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # En-tête
        self.lbl_titre = QLabel("—")
        f = QFont(); f.setBold(True); f.setPointSize(11)
        self.lbl_titre.setFont(f)
        self.lbl_titre.setWordWrap(True)
        lay.addWidget(self.lbl_titre)

        self.lbl_couleur = QLabel()
        self.lbl_couleur.setFixedHeight(6)
        lay.addWidget(self.lbl_couleur)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#e5e7eb;")
        lay.addWidget(sep)

        # Infos
        form = QFormLayout()
        form.setSpacing(6)
        form.setContentsMargins(0,0,0,0)
        self._labels = {}
        for key, label in [
            ("famille_nom",       "Famille"),
            ("variete",           "Variété"),
            ("mode_plantation",   "Mode"),
            ("date_semis",        "Semis"),
            ("date_premiere_recolte", "1ère récolte"),
            ("date_derniere_recolte", "Fin récolte"),
            ("longueur_planche_m","Longueur"),
            ("espacement_cm",     "Espacement"),
            ("nb_rangs",          "Rangs"),
            ("densite_m2",        "Densité"),
            ("rendement_ml",      "Rendement"),
            ("prix_kg",           "Prix"),
        ]:
            lbl = QLabel("—")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size:11px;")
            form.addRow(f"<b>{label}</b>", lbl)
            self._labels[key] = lbl

        lay.addLayout(form)

        # CA estimé
        self.lbl_ca = QLabel("")
        self.lbl_ca.setStyleSheet(
            "color:#16a34a;font-weight:bold;font-size:13px;"
            "padding:6px;background:#f0fdf4;border-radius:4px;")
        self.lbl_ca.setWordWrap(True)
        lay.addWidget(self.lbl_ca)

        lay.addStretch()

        # Bouton fermer
        btn_fermer = QPushButton("✕ Fermer")
        btn_fermer.setStyleSheet(
            "QPushButton{background:transparent;color:#6b7280;"
            "border:1px solid #e5e7eb;border-radius:4px;padding:4px;}"
            "QPushButton:hover{background:#f3f4f6;}")
        btn_fermer.clicked.connect(self.hide)
        lay.addWidget(btn_fermer)

    def charger(self, a: dict):
        nom = a.get("culture_nom","—")
        if a.get("variete"): nom += f" · {a['variete']}"
        self.lbl_titre.setText(nom)

        hex_c = get_couleur_culture(a)
        self.lbl_couleur.setStyleSheet(
            f"background:{hex_c};border-radius:3px;")

        modes = {"semis_direct":"Semis direct",
                 "plant_fait":"Plant fait",
                 "plant_achete":"Plant acheté"}

        vals = {
            "famille_nom":           a.get("famille_nom") or "—",
            "variete":               a.get("variete") or "—",
            "mode_plantation":       modes.get(a.get("mode_plantation",""), "—"),
            "date_semis":            a.get("date_semis") or "—",
            "date_premiere_recolte": a.get("date_premiere_recolte") or "—",
            "date_derniere_recolte": a.get("date_derniere_recolte") or "—",
            "longueur_planche_m":    f"{a['longueur_planche_m']:.0f} m"
                                     if a.get("longueur_planche_m") else "—",
            "espacement_cm":         f"{a['espacement_cm']:.0f} cm"
                                     if a.get("espacement_cm") else "—",
            "nb_rangs":              str(a.get("nb_rangs") or "—"),
            "densite_m2":            f"{a['densite_m2']:.1f} pl/m"
                                     if a.get("densite_m2") else "—",
            "rendement_ml":          f"{a['rendement_ml']:.2f} {a.get('unite_rendement','kg')}/m"
                                     if a.get("rendement_ml") else "—",
            "prix_kg":               f"{a['prix_kg']:.2f} €/{a.get('unite_rendement','kg')}"
                                     if a.get("prix_kg") else "—",
        }
        for key, lbl in self._labels.items():
            lbl.setText(vals.get(key,"—"))

        # CA
        rend = a.get("rendement_ml") or 0
        prix = a.get("prix_kg") or 0
        lon  = a.get("longueur_planche_m") or 0
        ca   = rend * prix * lon
        self.lbl_ca.setText(f"CA estimé : {ca:.2f} €" if ca > 0 else "")
        self.lbl_ca.setVisible(ca > 0)

# ── Grille canvas ─────────────────────────────
class GrilleCanvas(QWidget):
    MIME_TYPE = "application/x-assol-id"

    def __init__(self, annee: int, peut_ecrire: bool, peut_supprimer: bool,
                 on_modifier, on_supprimer, on_drop_serie,
                 on_detail=None, parent=None):
        super().__init__(parent)
        self.annee           = annee
        self.peut_ecrire     = peut_ecrire
        self.peut_supprimer  = peut_supprimer
        self.on_modifier     = on_modifier
        self.on_supprimer    = on_supprimer
        self.on_drop_serie   = on_drop_serie
        self.on_detail       = on_detail

        self._planches      = []
        self._assolement    = []
        self._lignes        = []
        self._hauteurs      = []
        self._slots         = {}
        self._blocs         = []
        self._collapsed     = set()
        self._hover_bloc    = None
        self._drag_candidat = None
        self._drag_origin   = None

        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumWidth(L_NOM + 52*L_SEMAINE + 20)

    def charger(self, planches: list, assolement: list):
        self._planches   = planches
        self._assolement = assolement
        self._build_lignes()
        self._update_size()
        self.update()
        # Forcer le recalcul après affichage
        QTimer.singleShot(0, self._update_size)
        QTimer.singleShot(0, self.update)

    def _build_lignes(self):
        self._lignes   = []
        self._hauteurs = []
        self._slots    = {}
        vus_parc = {}
        vus_sp   = {}  # (parcelle_id, sous_parcelle) → vu

        for pl in self._planches:
            pid  = pl.get("parcelle_id")
            sp   = pl.get("sous_parcelle") or None

            # Titre parcelle
            if pid not in vus_parc:
                vus_parc[pid] = pl.get("parcelle_nom", f"P{pid}")
                self._lignes.append(("parcelle", {
                    "parcelle_id": pid, "nom": vus_parc[pid]}))
                self._hauteurs.append(H_PARCELLE)

            if pid in self._collapsed:
                continue

            # Titre sous-parcelle si elle existe
            sp_key = (pid, sp)
            if sp and sp_key not in vus_sp:
                vus_sp[sp_key] = sp
                self._lignes.append(("sous_parcelle", {
                    "parcelle_id": pid, "sp_key": sp_key, "nom": sp}))
                self._hauteurs.append(H_PARCELLE)

            if sp and sp_key in self._collapsed:
                continue

            # Planche
            planche_id  = pl["id"]
            lon_planche = pl.get("longueur_m") or 0
            cultures = sorted(
                [a for a in self._assolement
                 if a["planche_id"] == planche_id],
                key=lambda a: a.get("date_semis") or "")
            slots = []
            for a in cultures:
                s1 = date_to_semaine(
                    a.get("date_semis") or f"{self.annee}-01-01", self.annee)
                s2 = date_to_semaine(
                    a.get("date_derniere_recolte") or f"{self.annee}-12-31",
                    self.annee)
                slot_idx = 0
                while slot_idx < 10:
                    if not any(s["slot"] == slot_idx for s in slots):
                        break
                    slot_idx += 1
                slots.append({"assol": a, "slot": slot_idx,
                              "s1": s1, "s2": s2,
                              "lon": a.get("longueur_planche_m") or lon_planche})
            self._slots[planche_id] = slots
            nb_slots = max((s["slot"] for s in slots), default=0) + 1 if slots else 1
            self._lignes.append(("planche", pl))
            self._hauteurs.append(H_PLANCHE * nb_slots)

    def _update_size(self):
        h = max(H_ENTETE + sum(self._hauteurs) + 20, 100)
        w = L_NOM + 52*L_SEMAINE + 20
        self.setMinimumSize(w, h)

    def _y_ligne(self, idx: int) -> int:
        return H_ENTETE + sum(self._hauteurs[:idx])

    def paintEvent(self, event):
        if not self._hauteurs:
            return
           
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = L_NOM + 52*L_SEMAINE
        h = H_ENTETE + sum(self._hauteurs)
        painter.fillRect(0, 0, w+20, h+20, Qt.white)
        self._draw_header(painter, w)
        self._draw_lignes(painter, w)
        self._draw_blocs(painter)
        self._draw_today(painter, h)
        painter.end()

    def _draw_header(self, painter: QPainter, w: int):
        painter.fillRect(0, 0, w, H_ENTETE, QColor("#f3f4f6"))
        fB = QFont(); fB.setPointSize(8); fB.setBold(True)
        painter.setFont(fB); painter.setPen(QColor("#374151"))
        painter.drawText(QRect(0,0,L_NOM,H_ENTETE), Qt.AlignCenter, "Planche")
        fM = QFont(); fM.setPointSize(7); fM.setBold(True); painter.setFont(fM)
        sem = 1
        for m in range(12):
            nb = 4
            if m in (0,2,4,6,7,9,11) and sem+4 <= 52: nb = 5 if m!=11 else 4
            x1 = semaine_to_x(sem); x2 = semaine_to_x(min(sem+nb,53))
            r = QRect(x1, 0, x2-x1, H_ENTETE//2)
            painter.fillRect(r, QColor("#e5e7eb"))
            painter.setPen(QColor("#374151"))
            painter.drawText(r, Qt.AlignCenter, MOIS_COURTS[m])
            painter.setPen(QPen(QColor("#d1d5db"),1))
            painter.drawLine(x1, 0, x1, H_ENTETE)
            sem += nb
        fS = QFont(); fS.setPointSize(6); painter.setFont(fS)
        painter.setPen(QColor("#9ca3af"))
        for s in range(1, 53):
            x = semaine_to_x(s)
            if s % 2 == 0:
                painter.drawText(QRect(x,H_ENTETE//2,L_SEMAINE,H_ENTETE//2),
                                 Qt.AlignCenter, str(s))
            painter.setPen(QPen(QColor("#e5e7eb"),1))
            painter.drawLine(x, H_ENTETE//2, x, H_ENTETE)
            painter.setPen(QColor("#9ca3af"))
        painter.setPen(QPen(QColor("#d1d5db"),1))
        painter.drawLine(0, H_ENTETE, w, H_ENTETE)

    def _draw_lignes(self, painter: QPainter, w: int):
        fP = QFont(); fP.setPointSize(9); fP.setBold(True)
        fN = QFont(); fN.setPointSize(8)
        total_h = 0
        for i, ligne in enumerate(self._lignes):
            typ  = ligne[0]
            data = ligne[1]
            y    = self._y_ligne(i)
            h_i  = self._hauteurs[i]

            if typ == "parcelle":
                painter.fillRect(QRect(0,y,w,h_i), QColor("#fef9c3"))
                painter.setFont(fP); painter.setPen(QColor("#713F12"))
                pid = data["parcelle_id"]
                icone = "▼ " if pid not in self._collapsed else "▶ "
                painter.drawText(QRect(8,y,L_NOM-8,h_i),
                                 Qt.AlignVCenter, icone+data["nom"])
                painter.fillRect(QRect(L_NOM,y,w-L_NOM,h_i), QColor("#fefce8"))

            elif typ == "sous_parcelle":
                painter.fillRect(QRect(0,y,w,h_i), QColor("#fde68a"))
                painter.setFont(fN); painter.setPen(QColor("#92400e"))
                sp_key = data["sp_key"]
                icone = "  ▼ " if sp_key not in self._collapsed else "  ▶ "
                painter.drawText(QRect(8,y,L_NOM-8,h_i),
                                 Qt.AlignVCenter, icone+data["nom"])
                painter.fillRect(QRect(L_NOM,y,w-L_NOM,h_i), QColor("#fef3c7"))

            else:
                nb_slots_total = self._hauteurs[i] // H_PLANCHE
                a_slot_vide    = False
                fond = QColor("#f9fafb") if i%2==0 else Qt.white
                painter.fillRect(QRect(0,y,w,h_i), fond)
                painter.setFont(fN); painter.setPen(QColor("#374151"))
                label = f"Planche {data['numero']}"
                if data.get("longueur_m"): label += f"  {data['longueur_m']}m"
                if data.get("sous_abris"): label += " 🏠"
                painter.drawText(QRect(16,y,L_NOM-20,h_i),
                                 Qt.AlignVCenter, label)

                # Séparateurs de slots
                for slot in range(1, nb_slots_total):
                    sy = y + slot*H_PLANCHE
                    if a_slot_vide and slot == nb_slots_total-1:
                        # Slot vide → pointillé vert clair
                        painter.setPen(QPen(QColor("#86efac"), 1, Qt.DashLine))
                        painter.fillRect(QRect(L_NOM, sy, w-L_NOM, H_PLANCHE),
                                         QColor("#f0fdf4"))
                        painter.setPen(QColor("#86efac"))
                        painter.setFont(QFont())
                        f_tiny = QFont(); f_tiny.setPointSize(7)
                        painter.setFont(f_tiny)
                        painter.drawText(
                            QRect(L_NOM+4, sy, w-L_NOM-8, H_PLANCHE),
                            Qt.AlignVCenter|Qt.AlignLeft,
                            "· · · espace disponible · · ·")
                    else:
                        painter.setPen(QPen(QColor("#d1d5db"), 1, Qt.DashLine))
                        painter.drawLine(L_NOM, sy, w, sy)

            painter.setPen(QPen(QColor("#f0f0f0"),1))
            for s in range(1, 53):
                x = semaine_to_x(s)
                painter.drawLine(x, y, x, y+h_i)
            painter.setPen(QPen(QColor("#e5e7eb"),1))
            painter.drawLine(0, y+h_i-1, w, y+h_i-1)
            total_h += h_i

        painter.setPen(QPen(QColor("#d1d5db"),2))
        painter.drawLine(L_NOM, H_ENTETE, L_NOM, H_ENTETE+total_h)

    def _draw_blocs(self, painter: QPainter):
        self._blocs = []
        fB = QFont(); fB.setPointSize(8); painter.setFont(fB)
        for i, ligne in enumerate(self._lignes):
            if ligne[0] != "planche": continue
            data = ligne[1]
            y    = self._y_ligne(i)
            plid = data["id"]
            for s_info in self._slots.get(plid, []):
                a        = s_info["assol"]
                slot_idx = s_info["slot"]
                s1       = s_info["s1"]
                s2       = s_info["s2"]
                if s2 <= s1: s2 = s1+2
                x1 = semaine_to_x(s1); x2 = semaine_to_x(min(s2,53))
                if x2 <= x1: x2 = x1+L_SEMAINE
                y_slot  = y + slot_idx*H_PLANCHE
                hex_c   = get_couleur_culture(a)
                couleur = QColor(hex_c)
                hover   = (self._hover_bloc and
                           self._hover_bloc.get("id") == a.get("id"))
                if hover: couleur = couleur.lighter(115)
                rect = QRect(x1+1, y_slot+2, x2-x1-2, H_PLANCHE-4)
                painter.fillRect(rect, couleur)
                painter.setPen(QPen(couleur.darker(140),1))
                painter.drawRoundedRect(rect, 3, 3)
                painter.setPen(QColor(couleur_texte(hex_c)))
                nom = a.get("culture_nom","")
                if a.get("variete"): nom += f" · {a['variete']}"
                if a.get("longueur_planche_m"): nom += f" ({a['longueur_planche_m']:.0f}m)"
                nom = painter.fontMetrics().elidedText(
                    nom, Qt.ElideRight, rect.width()-6)
                painter.drawText(rect.adjusted(3,0,-3,0),
                                 Qt.AlignVCenter|Qt.AlignLeft, nom)
                self._blocs.append((rect, a))

    def _draw_today(self, painter: QPainter, h: int):
        today = date.today()
        if today.year != self.annee: return
        s = date_to_semaine(today.strftime("%Y-%m-%d"), self.annee)
        x = semaine_to_x(s)
        painter.setPen(QPen(QColor("#DC2626"), 2, Qt.DashLine))
        painter.drawLine(x, 0, x, h)
        fT = QFont(); fT.setPointSize(7); painter.setFont(fT)
        painter.setPen(QColor("#DC2626"))
        painter.drawText(x+2, H_ENTETE-4, "auj.")

    def _planche_at(self, pos: QPoint):
        for i, ligne in enumerate(self._lignes):
            if ligne[0] != "planche": continue
            y   = self._y_ligne(i)
            h_i = self._hauteurs[i]
            if y <= pos.y() < y+h_i and pos.x() > L_NOM:
                return i, ligne[1]
        return None, None

    # ──────────────────────────────────────────
    # Interactions souris
    # ──────────────────────────────────────────
    def mousePressEvent(self, event):
        pos = event.pos()
        for i, ligne in enumerate(self._lignes):
            y = self._y_ligne(i)
            if ligne[0] == "parcelle" and y <= pos.y() < y+H_PARCELLE:
                pid = ligne[1]["parcelle_id"]
                if pid in self._collapsed: self._collapsed.discard(pid)
                else: self._collapsed.add(pid)
                self._build_lignes(); self._update_size(); self.update()
                return
            if ligne[0] == "sous_parcelle" and y <= pos.y() < y+H_PARCELLE:
                sp_key = ligne[1]["sp_key"]
                if sp_key in self._collapsed: self._collapsed.discard(sp_key)
                else: self._collapsed.add(sp_key)
                self._build_lignes(); self._update_size(); self.update()
                return

    def mouseMoveEvent(self, event):
        pos = event.pos()
        if (self._drag_candidat and self._drag_origin and
                event.buttons() & Qt.LeftButton):
            if (pos - self._drag_origin).manhattanLength() > 8:
                self._lancer_drag_bloc(self._drag_candidat)
                self._drag_candidat = None
                self._drag_origin   = None
                return
        hover = None
        for rect, a in self._blocs:
            if rect.contains(pos): hover = a; break
        if hover != self._hover_bloc:
            self._hover_bloc = hover
            self.setCursor(Qt.OpenHandCursor if hover else Qt.ArrowCursor)
            self.update()
            if hover:
                QToolTip.showText(self.mapToGlobal(pos), self._tooltip(hover))

    def mouseReleaseEvent(self, event):
        if (event.button() == Qt.LeftButton and
                self._drag_candidat and self._drag_origin):
            if (event.pos() - self._drag_origin).manhattanLength() <= 8:
                if self.on_detail:
                    self.on_detail(self._drag_candidat)
        self._drag_candidat = None
        self._drag_origin   = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            for rect, a in self._blocs:
                if rect.contains(pos):
                    if self.peut_ecrire:
                        self.on_modifier(a["id"])
                    return

    def _lancer_drag_bloc(self, a: dict):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self.MIME_TYPE, str(a["id"]).encode())
        drag.setMimeData(mime)
        hex_c = get_couleur_culture(a)
        s1 = date_to_semaine(a.get("date_semis") or
                              f"{self.annee}-01-01", self.annee)
        s2 = date_to_semaine(a.get("date_derniere_recolte") or
                              f"{self.annee}-12-31", self.annee)
        w = max(60, int((s2-s1)*L_SEMAINE))
        pm = QPixmap(w, H_PLANCHE-4); pm.fill(Qt.transparent)
        p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(pm.rect(), QColor(hex_c))
        p.setPen(QColor(couleur_texte(hex_c)))
        fnt = QFont(); fnt.setPointSize(8); p.setFont(fnt)
        p.drawText(pm.rect().adjusted(3,0,-3,0),
                   Qt.AlignVCenter|Qt.AlignLeft, a.get("culture_nom",""))
        p.end()
        drag.setPixmap(pm)
        drag.exec(Qt.MoveAction)
        self._drag_candidat = None
        self._drag_origin   = None

    def _menu_bloc(self, a: dict, pos: QPoint):
        menu = QMenu(self)
        if self.peut_ecrire:
            menu.addAction("✏ Modifier", lambda: self.on_modifier(a["id"]))
            menu.addAction("↩ Remettre en attente",
                lambda: self.on_drop_serie(a["id"], None, 0))
        if self.peut_supprimer:
            menu.addAction("🗑 Supprimer", lambda: self.on_supprimer(a["id"]))
        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(pos))

    # ──────────────────────────────────────────
    # Drop
    # ──────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self.MIME_TYPE): return
        try:
            assol_id = int(event.mimeData().data(self.MIME_TYPE).data())
        except Exception: return

        pos = event.position().toPoint() if hasattr(
            event, 'position') else event.pos()
        _, planche = self._planche_at(pos)
        if not planche:
            event.ignore(); return

        s = (pos.x() - L_NOM) / L_SEMAINE + 1
        s = max(1.0, min(52.0, s))

        # Vérification longueur disponible
        lon_planche = planche.get("longueur_m") or 0
        if lon_planche > 0:
            try:
                conn = get_connection(); cur = conn.cursor()
                cur.execute(
                    "SELECT longueur_planche_m, date_semis, date_derniere_recolte "
                    "FROM assolement WHERE id=?", (assol_id,))
                row = cur.fetchone(); cur.close()
                lon_nouvelle = row[0] if row and row[0] else lon_planche
                s1_new = date_to_semaine(
                    row[1] or f"{self.annee}-01-01", self.annee) if row else s
                s2_new = date_to_semaine(
                    row[2] or f"{self.annee}-12-31", self.annee) if row else s+8
            except Exception:
                lon_nouvelle = lon_planche; s1_new = s; s2_new = s+8

            lon_occupee = sum(
                s_i.get("lon", 0)
                for s_i in self._slots.get(planche["id"], [])
                if s_i["assol"]["id"] != assol_id
                and s_i["s1"] < s2_new and s_i["s2"] > s1_new)

            if lon_occupee + lon_nouvelle > lon_planche:
                restant = lon_planche - lon_occupee
                msg = (f"⚠ Longueur insuffisante :\n"
                       f"{lon_nouvelle:.0f}m nécessaires, "
                       f"seulement {max(restant,0):.0f}m disponibles "
                       f"sur {lon_planche:.0f}m.\n\n"
                       f"Réduisez la longueur de la culture dans le dialog "
                       f"ou choisissez une autre planche.")
                QMessageBox.warning(self, "Impossible de placer", msg)
                event.ignore(); return

        self.on_drop_serie(assol_id, planche["id"], s)
        event.acceptProposedAction()

    @staticmethod
    def _tooltip(a: dict) -> str:
        lines = [f"<b>{a.get('culture_nom','—')}</b>"]
        if a.get("variete"): lines.append(f"Variété : {a['variete']}")
        if a.get("famille_nom"): lines.append(f"Famille : {a['famille_nom']}")
        if a.get("date_semis"): lines.append(f"Semis : {a['date_semis']}")
        if a.get("date_derniere_recolte"):
            lines.append(f"Fin : {a['date_derniere_recolte']}")
        if a.get("longueur_planche_m"):
            lines.append(f"Longueur : {a['longueur_planche_m']}m")
        return "<br>".join(lines)


# ── Dialog Gérer planches ─────────────────────
class DialogGererPlanches(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gérer les planches")
        self.setMinimumWidth(560); self.setMinimumHeight(460)
        self._build_ui(); self._charger_parcelles()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Parcelle :"))
        self.combo_parcelle = QComboBox()
        self.combo_parcelle.currentIndexChanged.connect(self._charger_planches)
        top.addWidget(self.combo_parcelle, 1)
        lay.addLayout(top)
        gen = QGroupBox("Génération automatique")
        gl = QFormLayout(gen); gl.setSpacing(8)
        nb_w = QWidget(); nl = QHBoxLayout(nb_w)
        nl.setContentsMargins(0,0,0,0); nl.setSpacing(6)
        self.inp_nb  = QSpinBox(); self.inp_nb.setRange(1,200); self.inp_nb.setValue(10)
        self.inp_lon = QDoubleSpinBox()
        self.inp_lon.setRange(0,200); self.inp_lon.setDecimals(1)
        self.inp_lon.setSuffix(" m"); self.inp_lon.setValue(30)
        self.inp_lar = QDoubleSpinBox()
        self.inp_lar.setRange(0,10); self.inp_lar.setDecimals(2)
        self.inp_lar.setSuffix(" m"); self.inp_lar.setValue(1.20)
        nl.addWidget(QLabel("N° :")); nl.addWidget(self.inp_nb)
        nl.addWidget(QLabel("L :")); nl.addWidget(self.inp_lon)
        nl.addWidget(QLabel("l :")); nl.addWidget(self.inp_lar)
        gl.addRow("Planches :", nb_w)
        self.chk_sous_abris = QCheckBox("Sous abris")
        gl.addRow(self.chk_sous_abris)
        self.inp_sous_parc = QLineEdit()
        self.inp_sous_parc.setPlaceholderText("Ex: Serre A - Chapelle 1")
        gl.addRow("Sous-zone :", self.inp_sous_parc)
        btn_gen = QPushButton("⚡ Générer"); btn_gen.clicked.connect(self._generer)
        gl.addRow(btn_gen); lay.addWidget(gen)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["N°","Longueur (m)","Largeur (m)","Sous-abris","Sous-zone","Notes"])
        hh = self.table.horizontalHeader()
        for i in range(4): hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        hh.setSectionResizeMode(5, QHeaderView.Stretch)
        lay.addWidget(self.table, 1)
        btns_t = QHBoxLayout()
        btn_add = QPushButton("+ Ligne"); btn_add.clicked.connect(self._add_ligne)
        btn_del = QPushButton("− Supprimer"); btn_del.clicked.connect(self._del_ligne)
        btns_t.addWidget(btn_add); btns_t.addWidget(btn_del); btns_t.addStretch()
        lay.addLayout(btns_t)
        btns = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Close)
        btns.button(QDialogButtonBox.Save).setText("💾 Enregistrer")
        btns.accepted.connect(self._sauver); btns.rejected.connect(self.accept)
        lay.addWidget(btns)

    def _charger_parcelles(self):
        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute("SELECT id, nom FROM parcelles WHERE actif=1 ORDER BY nom")
            self.combo_parcelle.clear()
            for r in cur.fetchall(): self.combo_parcelle.addItem(r[1], r[0])
            cur.close()
        except Exception: traceback.print_exc()

    def _charger_planches(self):
        pid = self.combo_parcelle.currentData()
        if not pid: return
        self.table.setRowCount(0)
        for pl in get_planches_parcelle(pid): self._add_row(pl)

    def _add_row(self, pl: dict = None):
        r = self.table.rowCount(); self.table.insertRow(r)
        num = pl["numero"] if pl else r+1
        self.table.setItem(r, 0, QTableWidgetItem(str(num)))
        self.table.setItem(r, 1, QTableWidgetItem(
            str(pl.get("longueur_m") or "") if pl else ""))
        self.table.setItem(r, 2, QTableWidgetItem(
            str(pl.get("largeur_m") or "") if pl else ""))
        chk = QCheckBox(); chk.setChecked(bool(pl.get("sous_abris")) if pl else False)
        self.table.setCellWidget(r, 3, chk)
        self.table.setItem(r, 4, QTableWidgetItem(
            pl.get("sous_parcelle") or "" if pl else ""))
        self.table.setItem(r, 5, QTableWidgetItem(
            pl.get("notes") or "" if pl else ""))
        if pl: self.table.item(r,0).setData(Qt.UserRole, pl["id"])

    def _add_ligne(self): self._add_row()

    def _del_ligne(self):
        for r in sorted(set(i.row() for i in self.table.selectedItems()),
                        reverse=True):
            self.table.removeRow(r)

    def _generer(self):
        nb=self.inp_nb.value(); lon=self.inp_lon.value(); lar=self.inp_lar.value()
        sa=self.chk_sous_abris.isChecked(); sp=self.inp_sous_parc.text().strip() or None
        # Calculer le prochain numéro à partir des lignes existantes
        nums_existants = []
        for r in range(self.table.rowCount()):
            try:
                nums_existants.append(int(self.table.item(r,0).text()))
            except Exception:
                pass
        prochain = max(nums_existants, default=0) + 1
        for i in range(nb):
            r=self.table.rowCount(); self.table.insertRow(r)
            self.table.setItem(r,0,QTableWidgetItem(str(prochain+i)))
            self.table.setItem(r,1,QTableWidgetItem(str(lon)))
            self.table.setItem(r,2,QTableWidgetItem(str(lar)))
            chk=QCheckBox(); chk.setChecked(sa); self.table.setCellWidget(r,3,chk)
            self.table.setItem(r,4,QTableWidgetItem(sp or ""))
            self.table.setItem(r,5,QTableWidgetItem(""))

    def _sauver(self):
        pid=self.combo_parcelle.currentData()
        if not pid: return
        try:
            conn=get_connection(); cur=conn.cursor()
            cur.execute("SELECT id, numero FROM planches WHERE parcelle_id=?",(pid,))
            existants={r[1]:r[0] for r in cur.fetchall()}; gardes=set()
            for r in range(self.table.rowCount()):
                try: num=int(self.table.item(r,0).text())
                except Exception: continue
                lon=float(self.table.item(r,1).text() or 0) or None
                lar=float(self.table.item(r,2).text() or 0) or None
                chk=self.table.cellWidget(r,3); sa=1 if (chk and chk.isChecked()) else 0
                sp=(self.table.item(r,4).text() or "") or None
                nts=(self.table.item(r,5).text() or "") or None
                gardes.add(num)
                if num in existants:
                    cur.execute("""UPDATE planches SET longueur_m=?,largeur_m=?,
                        sous_abris=?,sous_parcelle=?,notes=? WHERE id=?""",
                        (lon,lar,sa,sp,nts,existants[num]))
                else:
                    cur.execute("""INSERT INTO planches
                        (parcelle_id,numero,longueur_m,largeur_m,
                         sous_abris,sous_parcelle,notes)
                        VALUES (?,?,?,?,?,?,?)""",(pid,num,lon,lar,sa,sp,nts))
            for num,plid in existants.items():
                if num not in gardes:
                    cur.execute("SELECT COUNT(*) FROM assolement WHERE planche_id=?",(plid,))
                    if cur.fetchone()[0]==0:
                        cur.execute("DELETE FROM planches WHERE id=?",(plid,))
                    else:
                        QMessageBox.warning(self,"Impossible",
                            f"Planche {num} a des cultures — supprimez-les d'abord.")
            conn.commit(); cur.close(); self._charger_planches()
        except Exception: traceback.print_exc()


# ── Dialog culture assolement ─────────────────
class DialogCultureAssolement(QDialog):
    def __init__(self, annee: int,
                 culture_ref_id_preselect: int = None,
                 date_semis_preselect: date = None,
                 date_fin_preselect: date = None,
                 assolement_id: int = None,
                 parent=None):
        super().__init__(parent)
        self.annee                    = annee
        self.culture_ref_id_preselect = culture_ref_id_preselect
        self.date_semis_preselect     = date_semis_preselect
        self.date_fin_preselect       = date_fin_preselect
        self.assolement_id            = assolement_id
        self.setWindowTitle(
            "Modifier la culture" if assolement_id else "Nouvelle culture")
        self.setMinimumWidth(560); self.setMinimumHeight(680)
        self._build_ui(); self._charger_combos()
        if assolement_id:
            self._charger_existant(assolement_id)
        else:
            if culture_ref_id_preselect:
                for i in range(self.combo_culture.count()):
                    if self.combo_culture.itemData(i)==culture_ref_id_preselect:
                        self.combo_culture.setCurrentIndex(i); break
            if date_semis_preselect:
                d=date_semis_preselect
                self.inp_date_debut.setDate(QDate(d.year,d.month,d.day))
            if date_fin_preselect:
                d=date_fin_preselect
                self.inp_dern_recolte.setDate(QDate(d.year,d.month,d.day))
        self._on_mode_changed(); self._calc_densite()
        self._calc_semences(); self._calc_ca()

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget(); lay = QVBoxLayout(inner)
        lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)

        # 1. Culture
        g1=QGroupBox("Culture"); f1=QFormLayout(g1); f1.setSpacing(8)
        cw=QWidget(); cl=QHBoxLayout(cw); cl.setContentsMargins(0,0,0,0)
        self.combo_culture=QComboBox(); self.combo_culture.setEditable(True)
        self.combo_culture.setInsertPolicy(QComboBox.NoInsert)
        btn_nc=QPushButton("+"); btn_nc.setFixedWidth(28)
        btn_nc.setToolTip("Créer dans le référentiel")
        btn_nc.clicked.connect(self._creer_culture)
        cl.addWidget(self.combo_culture,1); cl.addWidget(btn_nc)
        f1.addRow("Culture *",cw)
        self.inp_variete=QLineEdit(); self.inp_variete.setPlaceholderText("Optionnel")
        f1.addRow("Variété",self.inp_variete)
        self.chk_sous_abris=QCheckBox("Sous abris"); f1.addRow("",self.chk_sous_abris)
        lay.addWidget(g1)

        # 2. Planche
        g2=QGroupBox("Planche"); f2=QFormLayout(g2); f2.setSpacing(8)
        self.inp_longueur=QDoubleSpinBox()
        self.inp_longueur.setRange(0.1,500); self.inp_longueur.setDecimals(1)
        self.inp_longueur.setSuffix(" m")
        self.inp_longueur.valueChanged.connect(self._calc_densite)
        self.inp_longueur.valueChanged.connect(self._calc_semences)
        self.inp_longueur.valueChanged.connect(self._calc_ca)
        f2.addRow("Longueur",self.inp_longueur)
        nb_pl_w=QWidget(); nb_pl_l=QHBoxLayout(nb_pl_w)
        nb_pl_l.setContentsMargins(0,0,0,0); nb_pl_l.setSpacing(6)
        self.inp_nb_planches=QSpinBox()
        self.inp_nb_planches.setRange(1,100); self.inp_nb_planches.setValue(1)
        self.inp_nb_planches.valueChanged.connect(self._calc_semences)
        self.inp_nb_planches.valueChanged.connect(self._calc_ca)
        nb_pl_l.addWidget(QLabel("Nb planches :")); nb_pl_l.addWidget(self.inp_nb_planches)
        nb_pl_l.addStretch(); f2.addRow("",nb_pl_w)
        erd_w=QWidget(); erd_l=QHBoxLayout(erd_w)
        erd_l.setContentsMargins(0,0,0,0); erd_l.setSpacing(6)
        self.inp_espacement=QDoubleSpinBox()
        self.inp_espacement.setRange(1,200); self.inp_espacement.setDecimals(0)
        self.inp_espacement.setSuffix(" cm"); self.inp_espacement.setValue(30)
        self.inp_espacement.valueChanged.connect(self._calc_densite)
        self.inp_espacement.valueChanged.connect(self._calc_semences)
        self.inp_nb_rangs=QSpinBox()
        self.inp_nb_rangs.setRange(1,20); self.inp_nb_rangs.setValue(1)
        self.inp_nb_rangs.valueChanged.connect(self._calc_densite)
        self.inp_nb_rangs.valueChanged.connect(self._calc_semences)
        self.lbl_densite=QLabel("0 plant/m")
        self.lbl_densite.setStyleSheet("color:#2563EB;font-weight:bold;")
        erd_l.addWidget(QLabel("Espacement :")); erd_l.addWidget(self.inp_espacement)
        erd_l.addWidget(QLabel("Rangs :")); erd_l.addWidget(self.inp_nb_rangs)
        erd_l.addWidget(QLabel("Densité :")); erd_l.addWidget(self.lbl_densite)
        f2.addRow("Espacement / Rangs",erd_w); lay.addWidget(g2)

        # 3. Séries
        g3=QGroupBox("Séries"); f3=QFormLayout(g3); f3.setSpacing(8)
        ser_w=QWidget(); sl=QHBoxLayout(ser_w)
        sl.setContentsMargins(0,0,0,0); sl.setSpacing(6)
        self.inp_nb_series=QSpinBox()
        self.inp_nb_series.setRange(1,52); self.inp_nb_series.setValue(1)
        self.inp_nb_series.valueChanged.connect(self._on_series_changed)
        self.inp_nb_series.valueChanged.connect(self._calc_semences)
        self.inp_nb_series.valueChanged.connect(self._calc_ca)
        self.inp_intervalle=QSpinBox()
        self.inp_intervalle.setRange(1,52); self.inp_intervalle.setValue(2)
        self.inp_intervalle.setSuffix(" sem."); self.inp_intervalle.setEnabled(False)
        sl.addWidget(QLabel("Nombre :")); sl.addWidget(self.inp_nb_series)
        sl.addWidget(QLabel("Intervalle :")); sl.addWidget(self.inp_intervalle)
        f3.addRow("Séries",ser_w)
        self.lbl_recap=QLabel("")
        self.lbl_recap.setStyleSheet("color:#16a34a;font-size:11px;")
        f3.addRow("",self.lbl_recap); lay.addWidget(g3)

        # 4. Mode & Dates
        g4=QGroupBox("Plantation & Dates"); f4=QFormLayout(g4); f4.setSpacing(8)
        mw=QWidget(); ml=QHBoxLayout(mw); ml.setContentsMargins(0,0,0,0); ml.setSpacing(4)
        self.radio_semis=QRadioButton("Semis direct")
        self.radio_fait=QRadioButton("Plant fait")
        self.radio_achete=QRadioButton("Plant acheté")
        self.radio_semis.setChecked(True)
        for r in (self.radio_semis,self.radio_fait,self.radio_achete):
            ml.addWidget(r); r.toggled.connect(self._on_mode_changed)
        f4.addRow("Mode",mw)
        self.lbl_date_debut=QLabel("Date de semis")
        self.inp_date_debut=QDateEdit(QDate(self.annee,3,1))
        self.inp_date_debut.setDisplayFormat("dd/MM/yyyy")
        self.inp_date_debut.setCalendarPopup(True)
        f4.addRow(self.lbl_date_debut,self.inp_date_debut)
        self.inp_prem_recolte=QDateEdit(QDate(self.annee,6,1))
        self.inp_prem_recolte.setDisplayFormat("dd/MM/yyyy")
        self.inp_prem_recolte.setCalendarPopup(True)
        f4.addRow("1ère récolte",self.inp_prem_recolte)
        self.inp_dern_recolte=QDateEdit(QDate(self.annee,9,30))
        self.inp_dern_recolte.setDisplayFormat("dd/MM/yyyy")
        self.inp_dern_recolte.setCalendarPopup(True)
        f4.addRow("Dernière récolte",self.inp_dern_recolte)
        lay.addWidget(g4)

        # 5. Semences
        self.g5=QGroupBox("Semences"); f5=QFormLayout(self.g5); f5.setSpacing(8)
        sw=QWidget(); sl2=QHBoxLayout(sw); sl2.setContentsMargins(0,0,0,0); sl2.setSpacing(6)
        self.inp_graines_trou=QSpinBox()
        self.inp_graines_trou.setRange(1,10); self.inp_graines_trou.setValue(1)
        self.inp_graines_trou.valueChanged.connect(self._calc_semences)
        self.inp_pct_sup=QDoubleSpinBox()
        self.inp_pct_sup.setRange(0,100); self.inp_pct_sup.setDecimals(0)
        self.inp_pct_sup.setSuffix(" %"); self.inp_pct_sup.setValue(10)
        self.inp_pct_sup.valueChanged.connect(self._calc_semences)
        self.inp_pmg=QDoubleSpinBox()
        self.inp_pmg.setRange(0,100000); self.inp_pmg.setDecimals(2)
        self.inp_pmg.setSuffix(" g")
        self.inp_pmg.setToolTip("Poids de Mille Graines (PMG) en grammes")
        self.inp_pmg.valueChanged.connect(self._calc_semences)
        sl2.addWidget(QLabel("Par trou :")); sl2.addWidget(self.inp_graines_trou)
        sl2.addWidget(QLabel("% sup. :")); sl2.addWidget(self.inp_pct_sup)
        sl2.addWidget(QLabel("PMG :")); sl2.addWidget(self.inp_pmg)
        f5.addRow("Graines",sw)
        self.lbl_nb_graines=QLabel("Nombre : 0")
        self.lbl_nb_graines.setStyleSheet("color:#6b7280;font-size:11px;")
        f5.addRow("",self.lbl_nb_graines)
        self.lbl_poids=QLabel("Quantité : — g")
        self.lbl_poids.setStyleSheet("color:#6b7280;font-size:11px;")
        f5.addRow("",self.lbl_poids); lay.addWidget(self.g5)

        # 6. Rendement
        g6=QGroupBox("Rendements et produits"); f6=QFormLayout(g6); f6.setSpacing(8)
        uw=QWidget(); ul=QHBoxLayout(uw); ul.setContentsMargins(0,0,0,0)
        self.combo_unite=QComboBox(); self.combo_unite.addItems(["kg","pce","bte"])
        self.combo_unite.currentTextChanged.connect(self._on_unite_changed)
        btn_nu=QPushButton("+ Unité"); btn_nu.setFixedWidth(70)
        btn_nu.clicked.connect(self._ajouter_unite)
        ul.addWidget(self.combo_unite); ul.addWidget(btn_nu); ul.addStretch()
        f6.addRow("Unité",uw)
        rw=QWidget(); rl=QHBoxLayout(rw); rl.setContentsMargins(0,0,0,0)
        self.inp_rendement=QDoubleSpinBox()
        self.inp_rendement.setRange(0,99999); self.inp_rendement.setDecimals(2)
        self.inp_rendement.valueChanged.connect(self._calc_ca)
        self.lbl_rend_u=QLabel("/ m de planche")
        rl.addWidget(self.inp_rendement); rl.addWidget(self.lbl_rend_u); rl.addStretch()
        f6.addRow("Rendement",rw)
        pw=QWidget(); pl=QHBoxLayout(pw); pl.setContentsMargins(0,0,0,0)
        self.inp_prix=QDoubleSpinBox()
        self.inp_prix.setRange(0,9999); self.inp_prix.setDecimals(2)
        self.inp_prix.setSuffix(" €")
        self.inp_prix.valueChanged.connect(self._calc_ca)
        self.lbl_prix_u=QLabel("/ kg")
        pl.addWidget(self.inp_prix); pl.addWidget(self.lbl_prix_u); pl.addStretch()
        f6.addRow("Prix",pw)
        self.lbl_ca=QLabel("CA estimé : —")
        self.lbl_ca.setStyleSheet("color:#16a34a;font-weight:bold;font-size:13px;")
        f6.addRow("",self.lbl_ca); lay.addWidget(g6)

        g7=QGroupBox("Notes"); f7=QFormLayout(g7)
        self.inp_notes=QTextEdit(); self.inp_notes.setMaximumHeight(55)
        f7.addRow(self.inp_notes); lay.addWidget(g7)

        self.lbl_err=QLabel(""); self.lbl_err.setStyleSheet("color:red;")
        lay.addWidget(self.lbl_err)
        scroll.setWidget(inner); root.addWidget(scroll,1)
        btns=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider); btns.rejected.connect(self.reject)
        root.addWidget(btns)

        # Désactiver molette sur spinbox
        widgets = (self.findChildren(QSpinBox) +
                   self.findChildren(QDoubleSpinBox) +
                   self.findChildren(QComboBox))
        for w in widgets:
            w.setFocusPolicy(Qt.StrongFocus)
            w.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            if (obj in self.findChildren(QSpinBox) or
                    obj in self.findChildren(QDoubleSpinBox) or
                    obj in self.findChildren(QComboBox)):
                event.ignore(); return True
        return super().eventFilter(obj, event)

    def _on_mode_changed(self):
        achete=self.radio_achete.isChecked()
        self.g5.setVisible(not achete)
        self.lbl_date_debut.setText(
            "Date de semis" if self.radio_semis.isChecked()
            else "Date de mise en place")

    def _on_series_changed(self, n: int):
        self.inp_intervalle.setEnabled(n>1)
        nb_pl=self.inp_nb_planches.value()
        if n==1:
            self.lbl_recap.setText(f"{nb_pl} planche(s), série unique")
        else:
            self.lbl_recap.setText(
                f"{n} séries × {nb_pl} planche(s), "
                f"toutes les {self.inp_intervalle.value()} semaines")

    def _on_unite_changed(self, u: str):
        self.lbl_prix_u.setText(f"/ {u}"); self._calc_ca()

    def _calc_densite(self):
        esp=self.inp_espacement.value()/100.0
        self.lbl_densite.setText(
            f"{self.inp_nb_rangs.value()/esp:.1f} plant/m" if esp>0 else "—")

    def _calc_semences(self):
        esp=self.inp_espacement.value()/100.0
        lon=self.inp_longueur.value()
        if esp<=0 or lon<=0:
            self.lbl_nb_graines.setText("Nombre : 0")
            self.lbl_poids.setText("Quantité : — g"); return
        nb_empl=int(lon/esp)*self.inp_nb_rangs.value() \
               *self.inp_nb_planches.value()*self.inp_nb_series.value()
        nb=int(nb_empl*self.inp_graines_trou.value()
               *(1+self.inp_pct_sup.value()/100.0))
        self.lbl_nb_graines.setText(f"Nombre : {nb}")
        pmg=self.inp_pmg.value()
        self.lbl_poids.setText(
            f"Quantité : {nb*pmg/1000:.1f} g" if pmg>0
            else "Quantité : — g (saisissez le PMG)")

    def _calc_ca(self):
        ca=(self.inp_rendement.value()*self.inp_longueur.value()
            *self.inp_prix.value()*self.inp_nb_planches.value()
            *self.inp_nb_series.value())
        self.lbl_ca.setText(
            f"CA estimé : {ca:.2f} €" if ca>0 else "CA estimé : —")

    def _ajouter_unite(self):
        u,ok=QInputDialog.getText(self,"Nouvelle unité","Nom de l'unité :")
        if ok and u.strip():
            self.combo_unite.addItem(u.strip()); self.combo_unite.setCurrentText(u.strip())

    def _creer_culture(self):
        dlg=DialogCultureRef(parent=self)
        if dlg.exec()==QDialog.Accepted:
            try:
                conn=get_connection(); cur=conn.cursor()
                cur.execute("SELECT id FROM cultures_ref ORDER BY id DESC LIMIT 1")
                row=cur.fetchone(); cur.close()
                new_id=row[0] if row else None
            except Exception:
                new_id=None
            self._charger_combos()
            if new_id:
                for i in range(self.combo_culture.count()):
                    if self.combo_culture.itemData(i)==new_id:
                        self.combo_culture.setCurrentIndex(i); break

    def _on_culture_changed(self, idx: int):
        if self.combo_culture.itemData(idx)==-1:
            dlg=DialogCultureRef(parent=self)
            if dlg.exec()==QDialog.Accepted:
                try:
                    conn=get_connection(); cur=conn.cursor()
                    cur.execute("SELECT id FROM cultures_ref ORDER BY id DESC LIMIT 1")
                    row=cur.fetchone(); cur.close()
                    new_id=row[0] if row else None
                except Exception:
                    new_id=None
                self._charger_combos()
                if new_id:
                    for i in range(self.combo_culture.count()):
                        if self.combo_culture.itemData(i)==new_id:
                            self.combo_culture.setCurrentIndex(i); break
            else:
                self.combo_culture.setCurrentIndex(
                    1 if self.combo_culture.count()>1 else 0)

    def _charger_combos(self):
        cultures=get_cultures_ref()
        self.combo_culture.blockSignals(True)
        self.combo_culture.clear()
        self.combo_culture.addItem("+ Nouvelle espèce...",-1)
        for c in cultures:
            label=c["nom"]
            if c.get("famille_nom"): label+=f"  ({c['famille_nom']})"
            self.combo_culture.addItem(label,c["id"])
        self.combo_culture.blockSignals(False)
        self.combo_culture.currentIndexChanged.connect(self._on_culture_changed)

    def _charger_existant(self, aid: int):
        try:
            conn=get_connection(); cur=conn.cursor()
            cur.execute("SELECT * FROM assolement WHERE id=?",(aid,))
            a=dict(cur.fetchone()); cur.close()
            for i in range(self.combo_culture.count()):
                if self.combo_culture.itemData(i)==a["culture_ref_id"]:
                    self.combo_culture.setCurrentIndex(i); break
            self.inp_variete.setText(a.get("variete") or "")
            self.chk_sous_abris.setChecked(bool(a.get("sous_abris")))
            mode=a.get("mode_plantation","semis_direct")
            if mode=="semis_direct": self.radio_semis.setChecked(True)
            elif mode=="plant_fait": self.radio_fait.setChecked(True)
            else: self.radio_achete.setChecked(True)
            if a.get("longueur_planche_m"):
                self.inp_longueur.setValue(a["longueur_planche_m"])
            if a.get("espacement_cm"):
                self.inp_espacement.setValue(a["espacement_cm"])
            if a.get("nb_rangs"):
                self.inp_nb_rangs.setValue(a["nb_rangs"])
            self.inp_nb_series.setValue(a.get("nb_series") or 1)
            self.inp_intervalle.setValue(a.get("intervalle_semaines") or 2)
            def _sd(w,v):
                if v:
                    try:
                        dt=datetime.strptime(v,"%Y-%m-%d")
                        w.setDate(QDate(dt.year,dt.month,dt.day))
                    except Exception: pass
            _sd(self.inp_date_debut,a.get("date_semis"))
            _sd(self.inp_prem_recolte,a.get("date_premiere_recolte"))
            _sd(self.inp_dern_recolte,a.get("date_derniere_recolte"))
            if a.get("graines_par_trou"):
                self.inp_graines_trou.setValue(a["graines_par_trou"])
            if a.get("pct_sup_graines"):
                self.inp_pct_sup.setValue(a["pct_sup_graines"])
            if a.get("graines_par_gramme") and a["graines_par_gramme"]>0:
                self.inp_pmg.setValue(1000.0/a["graines_par_gramme"])
            u=a.get("unite_rendement") or "kg"
            if self.combo_unite.findText(u)<0: self.combo_unite.addItem(u)
            self.combo_unite.setCurrentText(u)
            self.inp_rendement.setValue(a.get("rendement_ml") or 0)
            self.inp_prix.setValue(a.get("prix_kg") or 0)
            self.inp_notes.setPlainText(a.get("notes") or "")
        except Exception: traceback.print_exc()

    def _valider(self):
        culture_ref_id=self.combo_culture.currentData()
        if not culture_ref_id or culture_ref_id==-1:
            self.lbl_err.setText("Sélectionnez ou créez une culture."); return
        variete=self.inp_variete.text().strip() or None
        sous_abris=1 if self.chk_sous_abris.isChecked() else 0
        longueur=self.inp_longueur.value() or None
        espacement=self.inp_espacement.value() or None
        nb_rangs=self.inp_nb_rangs.value() or None
        densite=(nb_rangs/(espacement/100.0) if espacement and nb_rangs else None)
        nb_planches=self.inp_nb_planches.value()
        nb_series=self.inp_nb_series.value()
        intervalle=self.inp_intervalle.value() if nb_series>1 else None
        mode=("semis_direct" if self.radio_semis.isChecked()
              else "plant_fait" if self.radio_fait.isChecked()
              else "plant_achete")
        date_semis_base=self.inp_date_debut.date().toPython()
        date_prem=self.inp_prem_recolte.date().toString("yyyy-MM-dd")
        date_dern=self.inp_dern_recolte.date().toString("yyyy-MM-dd")
        g_trou=(self.inp_graines_trou.value()
                if not self.radio_achete.isChecked() else None)
        pct_sup=(self.inp_pct_sup.value()
                 if not self.radio_achete.isChecked() else None)
        pmg=self.inp_pmg.value()
        g_g=(1000.0/pmg) if pmg>0 else None
        unite=self.combo_unite.currentText() or "kg"
        rend=self.inp_rendement.value() or None
        prix=self.inp_prix.value() or None
        notes=self.inp_notes.toPlainText().strip() or None
        try:
            conn=get_connection(); cur=conn.cursor()
            if self.assolement_id:
                cur.execute("""UPDATE assolement SET
                    culture_ref_id=?,variete=?,annee=?,
                    date_semis=?,date_premiere_recolte=?,
                    date_derniere_recolte=?,nb_series=?,
                    intervalle_semaines=?,mode_plantation=?,
                    longueur_planche_m=?,espacement_cm=?,
                    nb_rangs=?,densite_m2=?,
                    graines_par_trou=?,pct_sup_graines=?,
                    graines_par_gramme=?,unite_rendement=?,
                    rendement_ml=?,prix_kg=?,sous_abris=?,notes=?
                    WHERE id=?""",
                    (culture_ref_id,variete,self.annee,
                     date_semis_base.strftime("%Y-%m-%d"),date_prem,date_dern,
                     nb_series,intervalle,mode,
                     longueur,espacement,nb_rangs,densite,
                     g_trou,pct_sup,g_g,unite,rend,prix,
                     sous_abris,notes,self.assolement_id))
            else:
                d_prem_base=datetime.strptime(date_prem,"%Y-%m-%d").date()
                d_dern_base=datetime.strptime(date_dern,"%Y-%m-%d").date()
                for s in range(nb_series):
                    delta=timedelta(days=s*(intervalle or 0)*7)
                    d_sem=date_semis_base+delta
                    d_pr=(d_prem_base+delta).strftime("%Y-%m-%d")
                    d_dr=(d_dern_base+delta).strftime("%Y-%m-%d")
                    for _ in range(nb_planches):
                        cur.execute("""INSERT INTO assolement
                            (planche_id,culture_ref_id,variete,annee,
                             date_semis,date_premiere_recolte,
                             date_derniere_recolte,nb_series,
                             intervalle_semaines,mode_plantation,
                             longueur_planche_m,espacement_cm,
                             nb_rangs,densite_m2,
                             graines_par_trou,pct_sup_graines,
                             graines_par_gramme,unite_rendement,
                             rendement_ml,prix_kg,sous_abris,notes)
                            VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (culture_ref_id,variete,self.annee,
                             d_sem.strftime("%Y-%m-%d"),d_pr,d_dr,
                             nb_series,intervalle,mode,
                             longueur,espacement,nb_rangs,densite,
                             g_trou,pct_sup,g_g,unite,rend,prix,
                             sous_abris,notes))
            conn.commit(); cur.close(); self.accept()
        except Exception as e:
            traceback.print_exc(); self.lbl_err.setText(f"Erreur : {e}")


# ── Dialog référentiel cultures ───────────────
class DialogCultureRef(QDialog):
    def __init__(self, culture_id: int = None, parent=None):
        super().__init__(parent)
        self.culture_id=culture_id
        self.setWindowTitle(
            "Modifier" if culture_id else "Nouvelle culture (référentiel)")
        self.setMinimumWidth(360); self._build_ui()
        if culture_id: self._charger(culture_id)

    def _build_ui(self):
        lay=QVBoxLayout(self); form=QFormLayout(); form.setSpacing(10)
        self.inp_nom=QLineEdit()
        self.inp_nom.setPlaceholderText("Ex: Tomate, Carotte...")
        form.addRow("Nom *",self.inp_nom)
        self.combo_famille=QComboBox()
        self.combo_famille.addItem("— Non classé —",None)
        for fam in get_familles():
            self.combo_famille.addItem(fam["nom"],fam["id"])
        form.addRow("Famille botanique",self.combo_famille)
        cw=QWidget(); cl=QHBoxLayout(cw); cl.setContentsMargins(0,0,0,0)
        self.inp_couleur=QLineEdit()
        self.inp_couleur.setPlaceholderText("#RRGGBB")
        self.inp_couleur.setMaxLength(7); self.inp_couleur.setFixedWidth(90)
        self.btn_c=QPushButton("  "); self.btn_c.setFixedSize(28,28)
        self.btn_c.clicked.connect(self._choisir_couleur)
        self.inp_couleur.textChanged.connect(self._maj_apercu)
        cl.addWidget(self.inp_couleur); cl.addWidget(self.btn_c); cl.addStretch()
        form.addRow("Couleur perso",cw)
        self.inp_notes=QLineEdit(); form.addRow("Notes",self.inp_notes)
        self.lbl_err=QLabel(""); self.lbl_err.setStyleSheet("color:red;")
        form.addRow(self.lbl_err); lay.addLayout(form)
        btns=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider); btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _charger(self, cid: int):
        try:
            conn=get_connection(); cur=conn.cursor()
            cur.execute("SELECT * FROM cultures_ref WHERE id=?",(cid,))
            c=dict(cur.fetchone()); cur.close()
            self.inp_nom.setText(c.get("nom",""))
            idx=self.combo_famille.findData(c.get("famille_id"))
            self.combo_famille.setCurrentIndex(max(0,idx))
            self.inp_couleur.setText(c.get("couleur_perso") or "")
            self.inp_notes.setText(c.get("notes") or "")
        except Exception: traceback.print_exc()

    def _choisir_couleur(self):
        c=QColorDialog.getColor(QColor(self.inp_couleur.text() or "#95A5A6"),self)
        if c.isValid(): self.inp_couleur.setText(c.name())

    def _maj_apercu(self, txt: str):
        if len(txt)==7 and txt.startswith("#"):
            self.btn_c.setStyleSheet(f"background:{txt};border:1px solid #d1d5db;")

    def _valider(self):
        nom=self.inp_nom.text().strip()
        if not nom: self.lbl_err.setText("Le nom est obligatoire."); return
        fam=self.combo_famille.currentData()
        c=self.inp_couleur.text().strip() or None
        nts=self.inp_notes.text().strip() or None
        try:
            conn=get_connection(); cur=conn.cursor()
            if self.culture_id:
                cur.execute(
                    "UPDATE cultures_ref SET nom=?,famille_id=?,couleur_perso=?,notes=? WHERE id=?",
                    (nom,fam,c,nts,self.culture_id))
            else:
                cur.execute(
                    "INSERT INTO cultures_ref (nom,famille_id,couleur_perso,notes) VALUES (?,?,?,?)",
                    (nom,fam,c,nts))
            conn.commit(); cur.close(); self.accept()
        except Exception as e:
            traceback.print_exc(); self.lbl_err.setText(f"Erreur : {e}")