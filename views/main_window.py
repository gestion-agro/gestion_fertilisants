# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from views.shortcut import init_raccourcis
from views.menu import init_menu
from views.menu_context import menu_context_culture, menu_context_fert_droite, menu_context_fert_milieu
from views.fertilisants import ajout_fert, double_clic_fertilisant
from views.culture import ajout_culture, culture_selectionnee_changed
from views.fertilisants_utilises import table_doses_ha_modifiee, double_clic_fertilisant_enlever, mark_doses_modifiees

from tables.remplissages import remplir_tableaux, setup_table_header
from logic.calculs import calculer_doses
from logic.enregistrement import enregistrer_doses_culture
from logic.chargement import charger_fertilisants, charger_cultures

import utils.debug as debug

from ppp.catalogue import CataloguePPP


# ─────────────────────────────────────────────────────────────
# Bouton sidebar
# ─────────────────────────────────────────────────────────────
class SidebarButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background: palette(base);
                    border: 1px solid palette(mid);
                    border-radius: 6px;
                    padding: 0 10px;
                    font-weight: bold;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 6px;
                    padding: 0 10px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: palette(base);
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style(checked)


# ─────────────────────────────────────────────────────────────
# Fenêtre principale
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, current_user: dict = None):
        super().__init__()
        self.current_user = current_user or {}
        self.setWindowTitle(
            f"Gestion des cultures et fertilisants "
            f"— {self.current_user.get('prenom', '')} {self.current_user.get('nom', '')}"
        )
        self.showMaximized()

        self.MIN_doses_ha = 15
        self.TOLERANCE_DEPASS = 0.02
        self.culture_active = None
        self.cultures_selectionne = None
        self.table_modifiees = False
        self.set_doses_modifiees = False

        init_menu(self)

        # ── Widget central ────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ───────────────────────────
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        # Séparateur vertical
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: palette(mid);")
        root_layout.addWidget(sep)

        # ── Zone contenu (QStackedWidget) ─────
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        # ── Pages ─────────────────────────────
        self.page_fertilisants = self._build_page_fertilisants()
        self.page_ppp_catalogue   = CataloguePPP()
        self.page_ppp_aide        = self._build_page_placeholder("Aide à la décision", "Sélectionnez une culture et un bio-agresseur")
        self.page_ppp_carnet      = self._build_page_placeholder("Carnet de traitements", "Historique des interventions phytosanitaires")
        self.page_parametres      = self._build_page_placeholder("Paramètres", "Gestion des utilisateurs et configuration")

        self.stack.addWidget(self.page_fertilisants)   # index 0
        self.stack.addWidget(self.page_ppp_catalogue)  # index 1
        self.stack.addWidget(self.page_ppp_aide)       # index 2
        self.stack.addWidget(self.page_ppp_carnet)     # index 3
        self.stack.addWidget(self.page_parametres)     # index 4

        # ── Chargement données ────────────────
        self.lbl_modifie = QLabel("")
        self.lbl_modifie.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.lbl_modifie.setFont(font)
        self.lbl_modifie.setStyleSheet("color: red;")

        self.fert_base = charger_fertilisants(self)
        debug.debug(f"Fertilisants chargés : {len(self.fert_base)}")
        self.cultures = charger_cultures(self)
        debug.debug(f"Cultures chargées : {len(self.cultures)}")

        remplir_tableaux(self)
        self.cultures_selectionnee = None

        # Page par défaut
        self._nav_buttons[0].setChecked(True)
        self.stack.setCurrentIndex(0)

        init_raccourcis(self)

    # ─────────────────────────────────────────
    # Sidebar
    # ─────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(190)
        sidebar.setStyleSheet("background: palette(window);")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(2)

        # ── Bloc utilisateur ──────────────────
        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.setContentsMargins(8, 8, 8, 8)
        user_layout.setSpacing(4)

        # Avatar + nom
        name_layout = QHBoxLayout()
        name_layout.setSpacing(8)

        prenom = self.current_user.get("prenom", "?")
        nom    = self.current_user.get("nom", "")
        initials = (prenom[0] + nom[0]).upper() if nom else prenom[0].upper()

        avatar = QLabel(initials)
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background: #B5D4F4;
            color: #0C447C;
            border-radius: 16px;
            font-weight: bold;
            font-size: 13px;
        """)

        lbl_name = QLabel(f"{prenom} {nom}")
        lbl_name.setStyleSheet("font-weight: bold; font-size: 13px;")

        name_layout.addWidget(avatar)
        name_layout.addWidget(lbl_name)
        name_layout.addStretch()
        user_layout.addLayout(name_layout)

        # Badge CIPP
        cipp_type = self.current_user.get("certiphyto_type") or "Sans certificat"
        role      = self.current_user.get("role", "user")
        badge_text = cipp_type
        if role == "admin":
            badge_text += " · Admin"

        lbl_badge = QLabel(badge_text)
        lbl_badge.setStyleSheet("""
            background: palette(base);
            border: 1px solid palette(mid);
            border-radius: 4px;
            padding: 1px 6px;
            font-size: 11px;
            color: palette(mid);
        """)
        lbl_badge.setWordWrap(True)
        user_layout.addWidget(lbl_badge)

        user_widget.setStyleSheet("""
            QWidget {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 6px;
            }
        """)
        layout.addWidget(user_widget)
        layout.addSpacing(8)

        # ── Boutons de navigation ─────────────
        self._nav_buttons = []
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        def _add_section(label: str):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: palette(mid); padding: 6px 10px 2px;")
            layout.addWidget(lbl)

        def _add_nav(label: str, page_index: int) -> SidebarButton:
            btn = SidebarButton(label)
            btn.clicked.connect(lambda: self._navigate(page_index))
            self._nav_group.addButton(btn)
            self._nav_buttons.append(btn)
            layout.addWidget(btn)
            return btn

        _add_section("Modules")
        _add_nav("Fertilisants",       0)

        _add_section("PPP")
        _add_nav("Catalogue",          1)
        _add_nav("Aide à la décision", 2)
        _add_nav("Carnet",             3)

        layout.addStretch()

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: palette(mid);")
        layout.addWidget(sep)

        _add_nav("Paramètres",         4)

        return sidebar

    def _navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        # Sync bouton actif
        btn = self._nav_buttons[index] if index < len(self._nav_buttons) else None
        if btn:
            btn.setChecked(True)

    # ─────────────────────────────────────────
    # Page Fertilisants (contenu existant)
    # ─────────────────────────────────────────
    def _build_page_fertilisants(self) -> QWidget:
        page = QWidget()
        splitter = QSplitter(Qt.Horizontal)

        # ── Gauche : cultures ──────────────────
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(8, 8, 8, 8)

        btn_add_culture = QPushButton("Ajouter culture")
        btn_add_culture.clicked.connect(lambda: ajout_culture(self))
        left_layout.addWidget(btn_add_culture)

        self.table_cultures = QTableWidget(0, 5)
        self.table_cultures.setHorizontalHeaderLabels(["Nom", "N", "P", "K", "Surface"])
        self.table_cultures.cellDoubleClicked.connect(
            lambda row, col: culture_selectionnee_changed(self, row, col))
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(
            lambda pos: menu_context_culture(self, pos))
        setup_table_header(self, self.table_cultures, stretch_col=0)
        left_layout.addWidget(self.table_cultures)
        splitter.addWidget(left_container)

        # ── Centre : doses ─────────────────────
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(8, 8, 8, 8)

        self.lbl_culture_active = QLabel("Aucune culture sélectionnée")
        self.lbl_culture_active.setAlignment(Qt.AlignCenter)
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        self.lbl_culture_active.setFont(f)
        center_layout.addWidget(self.lbl_culture_active)

        # lbl_modifie placé ici pour remplissages.py
        center_layout.addWidget(self.lbl_modifie) if hasattr(self, 'lbl_modifie') else None

        lbl_utiliser = QLabel("Fertilisants à utiliser")
        center_layout.addWidget(lbl_utiliser)

        self.table_utiliser = QTableWidget(0, 4)
        self.table_utiliser.setHorizontalHeaderLabels(["Nom", "N", "P", "K"])
        self.table_utiliser.cellDoubleClicked.connect(
            lambda: double_clic_fertilisant_enlever(self))
        self.table_utiliser.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_utiliser.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_utiliser.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_utiliser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_utiliser.customContextMenuRequested.connect(
            lambda pos: menu_context_fert_milieu(self, pos))
        self.table_utiliser.itemChanged.connect(
            lambda item: mark_doses_modifiees(self, True))
        setup_table_header(self, self.table_utiliser, stretch_col=0)
        center_layout.addWidget(self.table_utiliser)

        lbl_doses_ha = QLabel("Doses pour 1 ha")
        center_layout.addWidget(lbl_doses_ha)

        self.table_doses_ha = QTableWidget(0, 5)
        self.table_doses_ha.setHorizontalHeaderLabels(["Fertilisant", "N", "P", "K", "Dose (kg/ha)"])
        self.table_doses_ha.cellChanged.connect(
            lambda row, col: table_doses_ha_modifiee(self, row, col))
        self.table_doses_ha.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_ha.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_doses_ha.itemChanged.connect(
            lambda item: mark_doses_modifiees(self, True))
        setup_table_header(self, self.table_doses_ha, stretch_col=0)
        center_layout.addWidget(self.table_doses_ha)

        lbl_dose_surface = QLabel("Doses pour la surface")
        center_layout.addWidget(lbl_dose_surface)
        self.lbl_dose_surface = lbl_dose_surface

        self.table_doses_surface = QTableWidget(0, 7)
        self.table_doses_surface.setHorizontalHeaderLabels(
            ["Fertilisant", "Dose", "Prix (dose)", "Cdtmt", "Prix unitaire", "Quantité", "Prix HT"])
        self.table_doses_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_surface.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_surface.setSelectionMode(QAbstractItemView.SingleSelection)
        setup_table_header(self, self.table_doses_surface, stretch_col=0)
        center_layout.addWidget(self.table_doses_surface)

        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(lambda: calculer_doses(self))
        btn_enregistrer = QPushButton("Enregistrer")
        btn_enregistrer.clicked.connect(lambda: enregistrer_doses_culture(self))
        center_layout.addWidget(btn_calcul)
        center_layout.addWidget(btn_enregistrer)

        splitter.addWidget(center_container)

        # ── Droite : fertilisants dispo ────────
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 8, 8, 8)

        btn_add_fert = QPushButton("Ajouter fertilisant")
        btn_add_fert.clicked.connect(lambda: ajout_fert(self))
        right_layout.addWidget(btn_add_fert)

        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(
            ["Nom", "N", "P", "K", "Cdtmt", "Prix", "Utilisable"])
        self.table_fertilisants.cellDoubleClicked.connect(
            lambda row, col: double_clic_fertilisant(self, row, col))
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_fertilisants.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_fertilisants.setWordWrap(False)
        self.table_fertilisants.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_fertilisants.customContextMenuRequested.connect(
            lambda pos: menu_context_fert_droite(self, pos))
        setup_table_header(self, self.table_fertilisants, stretch_col=0)
        right_layout.addWidget(self.table_fertilisants)
        splitter.addWidget(right_container)

        splitter.setSizes([300, 600, 400])

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        return page

    # ─────────────────────────────────────────
    # Pages placeholder (PPP + Paramètres)
    # Remplacées par les vraies vues par la suite
    # ─────────────────────────────────────────
    def _build_page_placeholder(self, titre: str, sous_titre: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        lbl_titre = QLabel(titre)
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        lbl_titre.setFont(f)
        lbl_titre.setAlignment(Qt.AlignCenter)

        lbl_sub = QLabel(sous_titre)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: palette(mid);")

        layout.addWidget(lbl_titre)
        layout.addSpacing(8)
        layout.addWidget(lbl_sub)
        return page