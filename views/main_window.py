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

from ppp.catalogue import CataloguePPP
from ppp.aide_decision import AideDecision
from ppp.carnet import CarnetPage

from parcelles.parcelles import ParcellePage

from irrigation.irrigation import IrrigationPage

from admin.admin import AdminPage

from exploit.exploit import ExploitPage

from ruches.ruches import RuchesPage

from views.parametres import ParametresPage

import utils.debug as debug


class SidebarButton(QPushButton):
    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setFixedHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

    def _apply_style(self, active: bool):
        if active:
            self.setStyleSheet("""
                QPushButton {
                    background: #2563EB;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 0 8px 0 22px;
                    font-size: 12px;
                    font-weight: 500;
                    text-align: left;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    border-radius: 5px;
                    padding: 0 8px 0 22px;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background: rgba(37, 99, 235, 0.12);
                }
            """)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style(checked)


class SidebarSection(QLabel):
    def __init__(self, label: str, parent=None):
        super().__init__(label.upper(), parent)
        self.setStyleSheet("""
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.08em;
            color: palette(text);
            padding: 10px 8px 2px 8px;
        """)


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

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar et index de page associés à chaque bouton
        self._nav_buttons = []       # liste de SidebarButton
        self._nav_page_indexes = []  # index de page correspondant

        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("background-color: palette(mid);")
        root_layout.addWidget(sep)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        # lbl_modifie doit exister avant _build_page_fertilisants
        self.lbl_modifie = QLabel("")
        self.lbl_modifie.setAlignment(Qt.AlignCenter)
        font = QFont(); font.setPointSize(12); font.setBold(True)
        self.lbl_modifie.setFont(font)
        self.lbl_modifie.setStyleSheet("color: red;")

        self.page_fertilisants  = self._build_page_fertilisants()
        self.page_ppp_catalogue = CataloguePPP()
        self.page_ppp_aide      = AideDecision(current_user=self.current_user)
        self.page_ppp_carnet    = CarnetPage(current_user=self.current_user)
        self.page_exploit       = ExploitPage(current_user=self.current_user)
        self.page_parcelles     = ParcellePage(current_user=self.current_user)
        self.page_irrigation    = IrrigationPage(current_user=self.current_user)
        self.page_admin         = AdminPage(current_user=self.current_user)
        self.page_ruches        = RuchesPage(current_user=self.current_user)
        self.page_parametres    = ParametresPage(current_user=self.current_user)

        # Signal parcelles → irrigation (rechargement sans restart)
        self.page_parcelles.parcelle_modifiee.connect(
            self.page_irrigation.recharger_parcelles)

        for p in [self.page_fertilisants,
                  self.page_ppp_catalogue,
                  self.page_ppp_aide,
                  self.page_ppp_carnet,
                  self.page_exploit,
                  self.page_parcelles,
                  self.page_irrigation,
                  self.page_admin,
                  self.page_parametres,
                  self.page_ruches]:
            self.stack.addWidget(p)

        self.page_ppp_aide.creer_traitement.connect(self._aller_au_carnet)

        self.fert_base = charger_fertilisants(self)
        self.cultures  = charger_cultures(self)
        remplir_tableaux(self)
        self.cultures_selectionnee = None

        # Page par défaut
        self._navigate_to(0)
        init_raccourcis(self)

    # ─────────────────────────────────────────
    # Sidebar
    # ─────────────────────────────────────────
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(205)
        sidebar.setStyleSheet("background: palette(window);")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(1)

        # Bloc utilisateur
        user_widget = QWidget()
        ul = QVBoxLayout(user_widget)
        ul.setContentsMargins(8, 8, 8, 8)
        ul.setSpacing(4)

        prenom = self.current_user.get("prenom", "?")
        nom    = self.current_user.get("nom", "")
        initials = (prenom[0] + (nom[0] if nom else "")).upper()

        row_u = QHBoxLayout()
        row_u.setSpacing(8)
        avatar = QLabel(initials)
        avatar.setFixedSize(32, 32)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background: #BFDBFE; color: #1D4ED8;
            border-radius: 16px; font-weight: bold; font-size: 13px;
        """)
        lbl_name = QLabel(f"{prenom} {nom}")
        lbl_name.setStyleSheet("font-weight: bold; font-size: 13px;")
        row_u.addWidget(avatar)
        row_u.addWidget(lbl_name)
        row_u.addStretch()
        ul.addLayout(row_u)

        cipp_type  = self.current_user.get("certiphyto_type") or "Sans certificat"
        role       = self.current_user.get("role", "user")
        badge_text = cipp_type + (" · Admin" if role == "admin" else "")
        lbl_badge  = QLabel(badge_text)
        lbl_badge.setStyleSheet("""
            background: palette(base); border: 1px solid palette(text);
            border-radius: 4px; padding: 1px 6px; font-size: 10px;
        """)
        lbl_badge.setWordWrap(True)
        ul.addWidget(lbl_badge)

        user_widget.setStyleSheet("""
            QWidget { background: palette(base); border: 1px solid palette(text);
                      border-radius: 6px; }
        """)
        layout.addWidget(user_widget)
        layout.addSpacing(6)

        # Navigation
        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        def _section(label: str):
            layout.addWidget(SidebarSection(label))

        def _nav(label: str, page_index: int) -> SidebarButton:
            btn = SidebarButton(label)
            idx = len(self._nav_buttons)
            btn.clicked.connect(lambda checked=False, pi=page_index: self._navigate_to(pi))
            self._nav_group.addButton(btn)
            self._nav_buttons.append(btn)
            self._nav_page_indexes.append(page_index)
            layout.addWidget(btn)
            return btn

        _section("Fertilisants")
        _nav("Gestion fertilisants", 0)

        _section("PPP")
        _nav("Catalogue",            1)
        cipp = self.current_user.get("certiphyto_type")
        if cipp in  ("CON", "DESA", "DENSA", "OPE") or role == "admin":
            _nav("Aide à la décision",   2)
            _nav("Carnet de traitements", 3)

        _section("Exploitation")
        _nav("Entreprise",          4)
        _nav("Parcelles",            5)
        _nav("Irrigation",           6)
        from db import get_entreprise
        ent = get_entreprise()
        if ent.get("has_ruches"):
            _nav("Ruches",              9)

        if role == "admin":
            _section("Administration")
            _nav("Gestion",          7)

        layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: palette(text); margin: 0 4px;")
        layout.addWidget(sep)

        _nav("Paramètres",           8)

        return sidebar

    def _navigate_to(self, page_index: int):
        """Navigation vers une page par son index dans le stack."""
        self.stack.setCurrentIndex(page_index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(self._nav_page_indexes[i] == page_index)

    def _aller_au_carnet(self, produit_id: int, usage_id: int,
                         culture: str, bio_agresseur: str):
        self._navigate_to(3)
        self.page_ppp_carnet.pre_remplir(produit_id, usage_id, culture, bio_agresseur)

    # ─────────────────────────────────────────
    # Pages
    # ─────────────────────────────────────────
    def _build_page_fertilisants(self) -> QWidget:
        page = QWidget()
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        ll = QVBoxLayout(left); ll.setContentsMargins(8, 8, 8, 8)
        btn_add_culture = QPushButton("Ajouter culture")
        btn_add_culture.clicked.connect(lambda: ajout_culture(self))
        ll.addWidget(btn_add_culture)
        self.table_cultures = QTableWidget(0, 5)
        self.table_cultures.setHorizontalHeaderLabels(["Nom","N","P","K","Surface"])
        self.table_cultures.cellDoubleClicked.connect(
            lambda r,c: culture_selectionnee_changed(self,r,c))
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(
            lambda pos: menu_context_culture(self, pos))
        setup_table_header(self, self.table_cultures, stretch_col=0)
        ll.addWidget(self.table_cultures)
        splitter.addWidget(left)

        center = QWidget()
        cl = QVBoxLayout(center); cl.setContentsMargins(8, 8, 8, 8)
        self.lbl_culture_active = QLabel("Aucune culture sélectionnée")
        self.lbl_culture_active.setAlignment(Qt.AlignCenter)
        f = QFont(); f.setPointSize(16); f.setBold(True)
        self.lbl_culture_active.setFont(f)
        cl.addWidget(self.lbl_culture_active)
        cl.addWidget(self.lbl_modifie)
        cl.addWidget(QLabel("Fertilisants à utiliser"))
        self.table_utiliser = QTableWidget(0, 4)
        self.table_utiliser.setHorizontalHeaderLabels(["Nom","N","P","K"])
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
        cl.addWidget(self.table_utiliser)
        cl.addWidget(QLabel("Doses pour 1 ha"))
        self.table_doses_ha = QTableWidget(0, 5)
        self.table_doses_ha.setHorizontalHeaderLabels(
            ["Fertilisant","N","P","K","Dose (kg/ha)"])
        self.table_doses_ha.cellChanged.connect(
            lambda r,c: table_doses_ha_modifiee(self,r,c))
        self.table_doses_ha.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_ha.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_doses_ha.itemChanged.connect(
            lambda item: mark_doses_modifiees(self, True))
        setup_table_header(self, self.table_doses_ha, stretch_col=0)
        cl.addWidget(self.table_doses_ha)
        self.lbl_dose_surface = QLabel("Doses pour la surface")
        cl.addWidget(self.lbl_dose_surface)
        self.table_doses_surface = QTableWidget(0, 7)
        self.table_doses_surface.setHorizontalHeaderLabels(
            ["Fertilisant","Dose","Prix (dose)","Cdtmt","Prix unitaire","Quantité","Prix HT"])
        self.table_doses_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_surface.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_surface.setSelectionMode(QAbstractItemView.SingleSelection)
        setup_table_header(self, self.table_doses_surface, stretch_col=0)
        cl.addWidget(self.table_doses_surface)
        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(lambda: calculer_doses(self))
        btn_enr = QPushButton("Enregistrer")
        btn_enr.clicked.connect(lambda: enregistrer_doses_culture(self))
        cl.addWidget(btn_calcul); cl.addWidget(btn_enr)
        splitter.addWidget(center)

        right = QWidget()
        rl = QVBoxLayout(right); rl.setContentsMargins(8, 8, 8, 8)
        btn_add_fert = QPushButton("Ajouter fertilisant")
        btn_add_fert.clicked.connect(lambda: ajout_fert(self))
        rl.addWidget(btn_add_fert)
        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(
            ["Nom","N","P","K","Cdtmt","Prix","Utilisable"])
        self.table_fertilisants.cellDoubleClicked.connect(
            lambda r,c: double_clic_fertilisant(self,r,c))
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_fertilisants.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_fertilisants.setWordWrap(False)
        self.table_fertilisants.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_fertilisants.customContextMenuRequested.connect(
            lambda pos: menu_context_fert_droite(self, pos))
        setup_table_header(self, self.table_fertilisants, stretch_col=0)
        rl.addWidget(self.table_fertilisants)
        splitter.addWidget(right)

        splitter.setSizes([300, 600, 400])
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter)
        return page

    def _build_page_placeholder(self, titre: str, sous_titre: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)
        lbl_titre = QLabel(titre)
        f = QFont(); f.setPointSize(20); f.setBold(True)
        lbl_titre.setFont(f); lbl_titre.setAlignment(Qt.AlignCenter)
        lbl_sub = QLabel(sous_titre)
        lbl_sub.setAlignment(Qt.AlignCenter)
        lbl_sub.setStyleSheet("color: palette(text);")
        layout.addWidget(lbl_titre)
        layout.addSpacing(8)
        layout.addWidget(lbl_sub)
        return page