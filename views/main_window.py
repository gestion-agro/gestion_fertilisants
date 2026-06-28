# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from views.shortcut import init_raccourcis
from views.menu import init_menu

from ppp.catalogue import CataloguePPP
from ppp.aide_decision import AideDecision
from ppp.carnet import CarnetPage

from fertilisants.catalogue import CatalogueFertilisants
from fertilisants.aide_decision import AideDecisionFerti
from fertilisants.carnet import CarnetFertilisation

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

        # ── Construction des pages ────────────
        self.page_exploit          = ExploitPage(current_user=self.current_user)
        self.page_parcelles        = ParcellePage(current_user=self.current_user)
        self.page_irrigation       = IrrigationPage(current_user=self.current_user)
        self.page_ruches           = RuchesPage(current_user=self.current_user)
        self.page_ppp_catalogue    = CataloguePPP()
        self.page_ppp_aide         = AideDecision(current_user=self.current_user)
        self.page_ppp_carnet       = CarnetPage(current_user=self.current_user)
        self.page_ferti_catalogue  = CatalogueFertilisants(current_user=self.current_user)
        self.page_ferti_aide       = AideDecisionFerti(current_user=self.current_user)
        self.page_ferti_carnet     = CarnetFertilisation(current_user=self.current_user)
        self.page_admin            = AdminPage(current_user=self.current_user)
        self.page_parametres       = ParametresPage(current_user=self.current_user)

        # ── Signaux de synchronisation entre pages ──
        # Parcelles → Irrigation (rechargement sans restart)
        self.page_parcelles.parcelle_modifiee.connect(
            self.page_irrigation.recharger_parcelles)
        # Parcelles → Aide ferti / Carnet ferti (nouvelles cultures dispo)
        self.page_parcelles.parcelle_modifiee.connect(
            self.page_ferti_aide.recharger)
        self.page_parcelles.parcelle_modifiee.connect(
            self.page_ferti_carnet.recharger)
        self.page_parcelles.parcelle_modifiee.connect(
            self.page_ferti_catalogue.recharger)
        self.page_ferti_catalogue.fertilisant_modifie.connect(
            self.page_ferti_aide.recharger)
        self.page_ferti_catalogue.fertilisant_modifie.connect(
            self.page_ferti_carnet.recharger)

        # ── Ordre du stack = ordre exact de la sidebar ──
        for p in [self.page_exploit,          # 0
                  self.page_parcelles,        # 1
                  self.page_irrigation,       # 2
                  self.page_ruches,           # 3
                  self.page_ppp_catalogue,    # 4
                  self.page_ppp_aide,         # 5
                  self.page_ppp_carnet,       # 6
                  self.page_ferti_catalogue,  # 7
                  self.page_ferti_aide,       # 8
                  self.page_ferti_carnet,     # 9
                  self.page_admin,            # 10
                  self.page_parametres]:      # 11
            self.stack.addWidget(p)

        self.page_ppp_aide.creer_traitement.connect(self._aller_au_carnet_ppp)
        self.page_ferti_aide.btn_aller_carnet  # bouton interne, pas de signal externe nécessaire

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
            btn.clicked.connect(lambda checked=False, pi=page_index: self._navigate_to(pi))
            self._nav_group.addButton(btn)
            self._nav_buttons.append(btn)
            self._nav_page_indexes.append(page_index)
            layout.addWidget(btn)
            return btn

        _section("Exploitation")
        _nav("Entreprise",           0)
        _nav("Parcelles",            1)
        _nav("Irrigation",           2)
        from db import get_entreprise
        ent = get_entreprise()
        if ent.get("has_ruches"):
            _nav("Ruches",            3)

        _section("PPP")
        _nav("Catalogue",             4)
        cipp = self.current_user.get("certiphyto_type")
        if cipp in ("CON", "DESA", "DENSA", "OPE") or role == "admin":
            _nav("Aide à la décision",    5)
            _nav("Carnet de traitements", 6)

        _section("Fertilisants")
        _nav("Catalogue",             7)
        _nav("Aide à la décision",    8)
        _nav("Carnet de fertilisation", 9)

        if role == "admin":
            _section("Administration")
            _nav("Gestion",         10)

        layout.addStretch()

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: palette(text); margin: 0 4px;")
        layout.addWidget(sep)

        _nav("Paramètres",           11)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: palette(text); margin: 0 4px;")
        layout.addWidget(sep2)

        btn_logout = QPushButton("⏻ Déconnexion")
        btn_logout.setFixedHeight(30)
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                border-radius: 5px; padding: 0 8px 0 22px;
                font-size: 12px; text-align: left; color: #DC2626;
            }
            QPushButton:hover { background: #FEE2E2; }
        """)
        btn_logout.clicked.connect(self._deconnecter)
        layout.addWidget(btn_logout)

        return sidebar

    def _navigate_to(self, page_index: int):
        """Navigation vers une page par son index dans le stack."""
        self.stack.setCurrentIndex(page_index)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(self._nav_page_indexes[i] == page_index)

    def _aller_au_carnet_ppp(self, produit_id: int, usage_id: int,
                              culture: str, bio_agresseur: str):
        self._navigate_to(6)  # page_ppp_carnet
        self.page_ppp_carnet.pre_remplir(produit_id, usage_id, culture, bio_agresseur)

    def closeEvent(self, event):
        worker = getattr(self.page_ppp_catalogue, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.quit()
            worker.wait(30000)
        super().closeEvent(event)

    def _deconnecter(self):
        from ui.login_window import LoginWindow
        rep = QMessageBox.question(self, "Déconnexion",
            "Se déconnecter et revenir à l'écran de connexion ?")
        if rep == QMessageBox.Yes:
            self.close()
            login = LoginWindow()
            if login.exec() == LoginWindow.Accepted and login.current_user:
                new_window = MainWindow(current_user=login.current_user)
                new_window.show()