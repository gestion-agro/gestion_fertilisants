# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug


# ── Étapes mode basique ───────────────────────
ETAPES_BASIQUE = [
    (None, "Bienvenue dans le didacticiel ! 👋",
     "Ce guide vous présente les fonctions principales de l'application. "
     "Utilisez ← → pour naviguer, ou 'Passer' pour quitter à tout moment. "
     "Un mode avancé est disponible pour explorer chaque bouton en détail.",
     None),

    ("page_exploit", "🏢 Entreprise — Informations",
     "Commencez ici en renseignant le nom, SIRET, adresse, téléphone et email "
     "de votre exploitation.\n\n"
     "Si vous êtes certifié AB, renseignez votre numéro d'agrément bio : "
     "l'application activera automatiquement les vérifications bio "
     "(alertes produits non-UAB, mode bio dans l'aide à la décision PPP...).",
     0),

    ("page_parcelles", "🌱 Parcelles — Gérer vos terres",
     "Créez vos parcelles avec '+ Ajouter une parcelle' (nom, type de sol, surface).\n\n"
     "Sélectionnez une parcelle pour y ajouter des cultures (maraîchage, arbo, "
     "engrais vert, jachère). Chaque culture peut avoir :\n"
     "• Ses besoins NPK (partagés avec le module Fertilisants)\n"
     "• Ses catégories PPP e-phy (pour l'homologation des traitements)\n"
     "• Ses systèmes d'irrigation\n\n"
     "Double-cliquez sur une parcelle ou culture pour la modifier.",
     1),

    ("page_irrigation", "💧 Irrigation — Suivi des apports",
     "Sélectionnez une parcelle puis un système d'irrigation pour enregistrer "
     "un apport (date, durée, volume).\n\n"
     "Les systèmes d'irrigation sont créés depuis l'onglet Parcelles "
     "(bouton '+ Ajouter un système'). Un système peut couvrir plusieurs cultures "
     "d'une même parcelle.",
     2),

    ("page_ruches", "🐝 Ruches — Apiculture",
     "Gérez vos ruches et leur suivi sanitaire.\n\n"
     "Pour chaque ruche, enregistrez vos visites (varroa %, état reine, couvain, "
     "population) et les interventions associées (sirop, candi, hausse, traitement "
     "varroa...).\n\n"
     "Le résumé de la dernière visite s'affiche automatiquement sous le bouton "
     "'+ Nouvelle visite' quand vous sélectionnez une ruche.",
     3),

    ("page_ppp_catalogue", "🌿 PPP — Catalogue e-phy",
     "Le catalogue contient tous les produits phytosanitaires homologués en France.\n\n"
     "Cliquez 'Importer depuis e-phy' pour télécharger les données officielles "
     "(connexion internet requise, opération de ~2 minutes).\n\n"
     "Filtrez par culture, bio-agresseur ou mode (bio/conventionnel). "
     "Double-cliquez sur un produit pour voir son détail complet.",
     4),

    ("page_ppp_aide", "🔍 PPP — Aide à la décision",
     "Sélectionnez une culture et un bio-agresseur, puis cliquez 'Rechercher'.\n\n"
     "Les produits homologués s'affichent avec leur dose max, DAR et conditions "
     "d'usage. En exploitation bio, le mode 'Bio uniquement' est sélectionné "
     "automatiquement.\n\n"
     "Cliquez 'Utiliser ce produit → Carnet' pour créer directement une décision "
     "de traitement pré-remplie.",
     5),

    ("page_ppp_carnet", "📋 PPP — Carnet de traitements",
     "Fonctionnement en deux temps :\n\n"
     "1. Le décideur (CON/DESA/DENSA) crée une décision (produit, dose, date, parcelle)\n"
     "2. L'opérateur (OPE) confirme l'application avec les données réelles "
     "(dose effective, météo, EPI, signature)\n\n"
     "L'historique des traitements peut être exporté en PDF pour votre "
     "contrôleur bio (colonnes configurables dans Paramètres).",
     6),

    ("page_ferti_catalogue", "🧪 Fertilisants — Catalogue",
     "Gérez votre stock de fertilisants : nom, composition NPK (%), prix, "
     "conditionnement, stock disponible, certification UAB et revendeur.\n\n"
     "Le stock (en kg) est décrémenté automatiquement à chaque apport "
     "enregistré dans le carnet. L'affichage montre les sacs pleins + "
     "les kg restants dans le sac entamé.",
     7),

    ("page_ferti_aide", "⚗️ Fertilisants — Aide à la décision",
     "Sélectionnez une culture (liée à une parcelle ou en mode NPK libre) "
     "pour calculer les doses recommandées.\n\n"
     "Mode AUTO : le solveur choisit automatiquement la combinaison optimale "
     "(moins chère, max 4 produits, tolérance ±2% configurable).\n\n"
     "Mode STRICT : cochez 3+ fertilisants précis → répartition exacte.\n\n"
     "Les doses sont modifiables avant enregistrement au carnet.",
     8),

    ("page_ferti_carnet", "📝 Fertilisants — Carnet",
     "Enregistrez chaque apport réel (date, parcelle, culture, fertilisant, dose).\n\n"
     "Le tableau de suivi surveille l'azote organique par parcelle. "
     "Une alerte apparaît si vous approchez ou dépassez le plafond réglementaire "
     "de 170 kg N/ha/an (directive nitrates).\n\n"
     "En exploitation bio, un avertissement s'affiche si vous utilisez "
     "un fertilisant non certifié UAB.",
     9),

    ("page_admin", "⚙️ Administration",
     "Gérez les utilisateurs et leurs droits.\n\n"
     "• Clic droit sur un utilisateur : Modifier, Permissions, Changer mdp, "
     "Forcer reset mdp, Désactiver/Supprimer\n"
     "• Les permissions sont configurées module par module\n"
     "• Le type CertiPhyto conditionne l'accès aux modules PPP\n"
     "• Les nouveaux utilisateurs définissent leur mot de passe "
     "à la première connexion",
     10),

    ("page_parametres", "🔧 Paramètres",
     "Mon compte : consultez vos infos et changez votre mot de passe.\n\n"
     "Application (admin uniquement) :\n"
     "• Largeur de planche et passe-pied par défaut\n"
     "• Tolérance NPK pour le solveur fertilisants\n"
     "• Colonnes et orientation de l'export PDF contrôleur bio",
     11),

    ("page_aide", "❓ Aide",
     "Cette page ! Recherchez n'importe quel terme pour trouver des explications "
     "sur toutes les fonctions de l'application.\n\n"
     "Le mode avancé du didacticiel guide bouton par bouton sur chaque module.",
     12),

    (None, "Didacticiel terminé ! 🎉",
     "Vous connaissez maintenant toutes les fonctions principales.\n\n"
     "Retrouvez des explications détaillées dans l'onglet Aide à tout moment, "
     "ou relancez ce didacticiel depuis le bouton '▶ Lancer le didacticiel'.\n\n"
     "Bonne utilisation ! 🌱",
     None),
]


# ── Étapes mode avancé ───────────────────────
# (page_attr, widget_attr, titre, texte)
ETAPES_AVANCEES = [
    ("page_parcelles", "btn_ajouter",
     "➕ Ajouter une parcelle",
     "Ce bouton ouvre le formulaire de création d'une nouvelle parcelle. "
     "Renseignez le nom, le type de sol et la surface totale en hectares."),

    ("page_parcelles", "btn_add_culture",
     "🌱 Ajouter une culture",
     "Après avoir sélectionné une parcelle dans la liste de gauche, "
     "ce bouton permet d'y ajouter une culture. "
     "Choisissez la catégorie (maraîchage, arbo, engrais vert, jachère)."),

    ("page_parcelles", "table_cultures",
     "📋 Tableau des cultures",
     "Liste les cultures de la parcelle sélectionnée. "
     "Double-cliquez sur une ligne pour modifier. "
     "Clic droit pour accéder aux options (modifier, supprimer)."),

    ("page_ferti_catalogue", "btn_ajouter",
     "➕ Ajouter un fertilisant",
     "Ouvre le formulaire d'ajout au catalogue. "
     "Renseignez nom, composition NPK (%), prix, conditionnement, "
     "stock initial et si le produit est certifié UAB."),

    ("page_ferti_aide", "btn_calculer",
     "🧮 Calculer les doses",
     "Lance le solveur PuLP. Sans case cochée = mode AUTO. "
     "Avec 3+ cases cochées = mode STRICT sur ces produits uniquement."),

    ("page_ferti_carnet", "btn_ajouter",
     "📝 Enregistrer un apport",
     "Ouvre le formulaire d'enregistrement d'un apport réel. "
     "Sélectionnez la parcelle, la culture, le fertilisant et la dose. "
     "Le stock est mis à jour automatiquement."),

    ("page_ppp_aide", "btn_rechercher",
     "🔍 Rechercher des produits PPP",
     "Lance la recherche dans le catalogue e-phy. "
     "Sélectionnez d'abord une culture et un bio-agresseur. "
     "En exploitation bio, le mode 'Bio uniquement' est pré-sélectionné."),

    ("page_ppp_carnet", "btn_export_bio",
     "📄 Export PDF contrôleur",
     "Génère un PDF du carnet de traitements sur la période filtrée. "
     "Les colonnes exportées sont configurables dans Paramètres → Application."),

    ("page_ruches", "btn_add_ruche",
     "🐝 Ajouter une ruche",
     "Crée une nouvelle ruche avec son nom, numéro NAPI, race, "
     "type de ruche et date d'installation."),

    ("page_ruches", "btn_nouvelle_visite",
     "📋 Nouvelle visite",
     "Enregistre une visite de la ruche sélectionnée. "
     "Renseignez le taux de varroa, l'état de la reine, du couvain, "
     "la population estimée et les interventions réalisées."),
]


# ── Mapping page_attr → index stack ──────────
PAGE_INDEXES = {
    "page_exploit": 0, "page_parcelles": 1,
    "page_irrigation": 2, "page_ruches": 3,
    "page_ppp_catalogue": 4, "page_ppp_aide": 5,
    "page_ppp_carnet": 6, "page_ferti_catalogue": 7,
    "page_ferti_aide": 8, "page_ferti_carnet": 9,
    "page_admin": 10, "page_parametres": 11, "page_aide": 12,
}


class DidacticielOverlay(QWidget):
    """Overlay transparent sur MainWindow — deux modes :
    - Basique (mode_avance=False) : une étape par page, textes détaillés
    - Avancé (mode_avance=True)  : étapes ciblant des boutons précis
    """

    termine = Signal()

    def __init__(self, main_window, mode_avance: bool = False, parent=None):
        super().__init__(parent or main_window)
        self.main_window = main_window
        self._mode_avance = mode_avance
        self._etapes = ETAPES_AVANCEES if mode_avance else ETAPES_BASIQUE
        self._etape = 0
        self._target_rect = None

        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.resize(main_window.size())

        self._build_bulle()
        self._afficher_etape()

    # ──────────────────────────────────────────
    # Construction de la bulle
    # ──────────────────────────────────────────
    def _build_bulle(self):
        self.bulle = QFrame(self)
        self.bulle.setMinimumWidth(480)
        self.bulle.setMaximumWidth(560)
        self.bulle.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #2563EB;
                border-radius: 10px;
            }
        """)
        b_lay = QVBoxLayout(self.bulle)
        b_lay.setContentsMargins(16, 14, 16, 14)
        b_lay.setSpacing(10)

        # Badge mode
        self.lbl_mode = QLabel(
            "🔬 Mode avancé" if self._mode_avance else "📖 Mode découverte")
        self.lbl_mode.setStyleSheet(
            "background: #eff6ff; color: #2563EB; border-radius: 3px; "
            "padding: 2px 8px; font-size: 10px; font-weight: bold;")
        self.lbl_mode.setFixedHeight(20)
        b_lay.addWidget(self.lbl_mode)

        # Titre
        self.lbl_titre = QLabel()
        f = QFont(); f.setPointSize(13); f.setBold(True)
        self.lbl_titre.setFont(f)
        self.lbl_titre.setWordWrap(True)
        b_lay.addWidget(self.lbl_titre)

        # Texte
        self.lbl_texte = QLabel()
        self.lbl_texte.setWordWrap(True)
        self.lbl_texte.setStyleSheet("color: #374151; font-size: 12px;")
        b_lay.addWidget(self.lbl_texte)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: none; background: #e5e7eb; border-radius: 2px; }
            QProgressBar::chunk { background: #2563EB; border-radius: 2px; }
        """)
        b_lay.addWidget(self.progress_bar)

        self.lbl_progress = QLabel()
        self.lbl_progress.setStyleSheet("color: #9ca3af; font-size: 10px;")
        self.lbl_progress.setAlignment(Qt.AlignCenter)
        b_lay.addWidget(self.lbl_progress)

        # Boutons
        btns = QHBoxLayout()

        self.btn_passer = QPushButton("✕ Passer")
        self.btn_passer.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #d1d5db;
                border-radius: 4px; padding: 4px 10px; color: #6b7280;
                font-size: 11px;
            }
            QPushButton:hover { background: #f3f4f6; }
        """)
        self.btn_passer.clicked.connect(self._terminer)

        label_autre = "Mode découverte" if self._mode_avance else "Mode avancé"
        self.btn_changer_mode = QPushButton(f"⇄ {label_autre}")
        self.btn_changer_mode.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #2563EB;
                border-radius: 4px; padding: 4px 10px; color: #2563EB;
                font-size: 11px;
            }
            QPushButton:hover { background: #eff6ff; }
        """)
        self.btn_changer_mode.clicked.connect(self._changer_mode)

        self.btn_prev = QPushButton("←")
        self.btn_prev.setFixedWidth(36)
        self.btn_prev.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; border: none;
                border-radius: 4px; padding: 4px;
            }
            QPushButton:hover { background: #e5e7eb; }
            QPushButton:disabled { color: #d1d5db; }
        """)
        self.btn_prev.clicked.connect(self._prev)

        self.btn_next = QPushButton("Suivant →")
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: #2563EB; color: white; border: none;
                border-radius: 4px; padding: 4px 14px; font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        self.btn_next.clicked.connect(self._next)

        btns.addWidget(self.btn_passer)
        btns.addWidget(self.btn_changer_mode)
        btns.addStretch()
        btns.addWidget(self.btn_prev)
        btns.addWidget(self.btn_next)
        b_lay.addLayout(btns)
        self.bulle.adjustSize()

    # ──────────────────────────────────────────
    # Affichage d'une étape
    # ──────────────────────────────────────────
    def _afficher_etape(self):
        if self._etape >= len(self._etapes):
            self._terminer()
            return

        etape = self._etapes[self._etape]

        if self._mode_avance:
            page_attr, widget_attr, titre, texte = etape
            if page_attr in PAGE_INDEXES:
                self.main_window._navigate_to(PAGE_INDEXES[page_attr])
                QApplication.processEvents()
            self._target_rect = self._get_widget_rect(page_attr, widget_attr)
        else:
            widget_attr, titre, texte, navigate_to = etape
            if navigate_to is not None:
                self.main_window._navigate_to(navigate_to)
                QApplication.processEvents()
            self._target_rect = self._get_target_rect(widget_attr)

        self.lbl_titre.setText(titre)
        self.lbl_texte.setText(texte)

        n = len(self._etapes)
        self.progress_bar.setMaximum(n)
        self.progress_bar.setValue(self._etape + 1)
        self.lbl_progress.setText(f"Étape {self._etape + 1} / {n}")

        self.btn_prev.setEnabled(self._etape > 0)
        self.btn_next.setText("✓ Terminer" if self._etape == n - 1 else "Suivant →")

        self._positionner_bulle()
        self.update()

    # ──────────────────────────────────────────
    # Récupération du rectangle cible
    # ──────────────────────────────────────────
    def _get_target_rect(self, widget_attr) -> QRect | None:
        """Mode basique : widget direct sur main_window."""
        if not widget_attr:
            return None
        widget = getattr(self.main_window, widget_attr, None)
        if not widget or not widget.isVisible():
            return None
        try:
            pos = widget.mapTo(self.main_window, QPoint(0, 0))
            return QRect(pos, widget.size())
        except Exception:
            return None

    def _get_widget_rect(self, page_attr: str, widget_attr: str) -> QRect | None:
        """Mode avancé : widget dans une sous-page."""
        page = getattr(self.main_window, page_attr, None)
        if not page:
            return None
        widget = getattr(page, widget_attr, None)
        if not widget or not widget.isVisible():
            return None
        try:
            pos = widget.mapTo(self.main_window, QPoint(0, 0))
            return QRect(pos, widget.size())
        except Exception:
            return None

    # ──────────────────────────────────────────
    # Positionnement de la bulle
    # ──────────────────────────────────────────
    def _positionner_bulle(self):
        self.bulle.adjustSize()
        w = self.bulle.width()
        h = self.bulle.height()
        ow, oh = self.width(), self.height()

        if self._target_rect:
            r = self._target_rect
            x = r.right() + 16
            y = r.top()
            if x + w > ow - 16:
                x = r.left() - w - 16
            if x < 16:
                x = (ow - w) // 2
            y = max(16, min(y, oh - h - 16))
        else:
            x = (ow - w) // 2
            y = (oh - h) // 2

        self.bulle.move(x, y)
        self.bulle.show()
        self.bulle.raise_()

    # ──────────────────────────────────────────
    # Rendu
    # ──────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._target_rect:
            margin = 6
            highlight = self._target_rect.adjusted(-margin, -margin, margin, margin)
            region = QRegion(self.rect())
            region -= QRegion(highlight)
            painter.setClipRegion(region)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))
            painter.setClipping(False)
            pen = QPen(QColor("#2563EB"), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(highlight, 6, 6)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 120))

        painter.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize(self.main_window.size())
        self._positionner_bulle()

    # ──────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────
    def _changer_mode(self):
        self.hide()
        self.deleteLater()
        nouveau = DidacticielOverlay(
            self.main_window,
            mode_avance=not self._mode_avance,
            parent=self.parent())
        nouveau.resize(self.main_window.size())
        nouveau.show()
        nouveau.raise_()

    def _prev(self):
        if self._etape > 0:
            self._etape -= 1
            self._afficher_etape()

    def _next(self):
        if self._etape < len(self._etapes) - 1:
            self._etape += 1
            self._afficher_etape()
        else:
            self._terminer()

    def _terminer(self):
        debug.debug("[didacticiel] Terminé")
        self.termine.emit()
        self.hide()
        self.deleteLater()