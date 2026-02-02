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

from utils.debug import debug

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gestion des cultures et fertilisants")
        self.showMaximized()

        self.MIN_doses_ha = 15      # kg/ha minimum affichable
        self.TOLERANCE_DEPASS = 0.02  # +5 % max autorisé
        self.culture_active = None
        self.cultures_selectionne = None
        self.table_modifiees = False
        self.DEBUG = True

        init_menu(self)

        # Label badge
        self.lbl_modifie = QLabel("")

        self.lbl_modifie.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.lbl_modifie.setFont(font)

        self.lbl_modifie.setStyleSheet("color: red;")
        self.set_doses_modifiees = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # ======================
        # Splitter horizontal
        # ======================
        splitter = QSplitter(Qt.Horizontal)

        # ----------------------
        # Côté gauche : cultures
        left_layout = QVBoxLayout()
        left_container = QWidget()
        left_container.setLayout(left_layout)

        btn_add_culture = QPushButton("Ajouter culture")
        btn_add_culture.clicked.connect(
            lambda : ajout_culture(self)
        )
        left_layout.addWidget(btn_add_culture)

        self.table_cultures = QTableWidget(0, 5)
        self.table_cultures.setHorizontalHeaderLabels(["Nom", "N", "P", "K", "Surface"])
        self.table_cultures.cellDoubleClicked.connect(
            lambda row, column : culture_selectionnee_changed(self, row, column)
        )
        self.table_cultures.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_cultures.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_cultures.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_cultures.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_cultures.customContextMenuRequested.connect(
            lambda pos: menu_context_culture(self, pos)
        )

        # Setup header via fonction
        setup_table_header(self, self.table_cultures, stretch_col=0)
        left_layout.addWidget(self.table_cultures)

        splitter.addWidget(left_container)
        # ----------------------

        # ----------------------
        # Zone centrale : utilisation + doses
        center_layout = QVBoxLayout()
        center_container = QWidget()
        center_container.setLayout(center_layout)

        self.lbl_culture_active = QLabel("Aucune culture sélectionnée")
        self.lbl_culture_active.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.lbl_culture_active.setFont(font)
        center_layout.addWidget(self.lbl_culture_active)
        center_layout.addWidget(self.lbl_modifie)

        self.lbl_utiliser = QLabel("Fertilisants à utiliser")
        center_layout.addWidget(self.lbl_utiliser)

        self.table_utiliser = QTableWidget(0, 4)
        self.table_utiliser.setHorizontalHeaderLabels(["Nom", "N", "P", "K"])
        self.table_utiliser.cellDoubleClicked.connect(
            lambda : double_clic_fertilisant_enlever(self)
        )
        self.table_utiliser.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_utiliser.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_utiliser.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_utiliser.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_utiliser.customContextMenuRequested.connect(
            lambda pos : menu_context_fert_milieu(self, pos)
        )

        debug("Affichage de lbl_modifie")
        self.table_utiliser.itemChanged.connect(
            lambda item: mark_doses_modifiees(self, True)
        )

        setup_table_header(self, self.table_utiliser, stretch_col=0)
        center_layout.addWidget(self.table_utiliser)

        lbl_doses_ha = QLabel("Doses pour 1 ha")
        center_layout.addWidget(lbl_doses_ha)

        self.table_doses_ha = QTableWidget(0, 5)
        self.table_doses_ha.setHorizontalHeaderLabels(["Fertilisant", "N", "P", "K", "Dose (kg/ha)"])
        self.table_doses_ha.cellChanged.connect(
            lambda row, column : table_doses_ha_modifiee(self, row, column)
        )
        self.table_doses_ha.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_ha.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_ha.setSelectionMode(QAbstractItemView.SingleSelection)

        debug("Affichage de lbl_modifie")
        self.table_doses_ha.itemChanged.connect(
            lambda item: mark_doses_modifiees(self, True)
        )

        setup_table_header(self, self.table_doses_ha, stretch_col=0)
        center_layout.addWidget(self.table_doses_ha)

        self.lbl_dose_surface = QLabel("Doses pour la surface")
        center_layout.addWidget(self.lbl_dose_surface)

        self.table_doses_surface = QTableWidget(0, 7)
        self.table_doses_surface.setHorizontalHeaderLabels(
            ["Fertilisant", "Dose", "Prix (dose)", "Cdtmt", "Prix unitaire", "Quantité", "Prix HT"]
        )
        self.table_doses_surface.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_doses_surface.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_doses_surface.setSelectionMode(QAbstractItemView.SingleSelection)

        setup_table_header(self, self.table_doses_surface, stretch_col=0)
        center_layout.addWidget(self.table_doses_surface)

        btn_calcul = QPushButton("Calculer les doses")
        btn_calcul.clicked.connect(
            lambda : calculer_doses(self)
        )
        btn_enregistrer = QPushButton("Enregistrer")
        btn_enregistrer.clicked.connect(
            lambda : enregistrer_doses_culture(self)
        )
        center_layout.addWidget(btn_calcul)
        center_layout.addWidget(btn_enregistrer)

        splitter.addWidget(center_container)
        # ----------------------

        # ----------------------
        # Côté droit : fertilisants disponibles
        right_layout = QVBoxLayout()
        right_container = QWidget()
        right_container.setLayout(right_layout)

        btn_add_fert = QPushButton("Ajouter fertilisant")
        btn_add_fert.clicked.connect(
            lambda : ajout_fert(self)
        )
        right_layout.addWidget(btn_add_fert)

        self.table_fertilisants = QTableWidget(0, 7)
        self.table_fertilisants.setHorizontalHeaderLabels(["Nom", "N", "P", "K", "Cdtmt", "Prix", "Utilisable"])
        self.table_fertilisants.cellDoubleClicked.connect(
            lambda row, column : double_clic_fertilisant(self, row, column)
        )
        self.table_fertilisants.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_fertilisants.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_fertilisants.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_fertilisants.setWordWrap(False)
        self.table_fertilisants.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_fertilisants.customContextMenuRequested.connect(
            lambda pos : menu_context_fert_droite(self, pos)
        )

        setup_table_header(self, self.table_fertilisants, stretch_col=0)
        right_layout.addWidget(self.table_fertilisants)

        splitter.addWidget(right_container)
        # ----------------------

        # ----------------------
        # Mettre le splitter comme layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.addWidget(splitter)
        splitter.setSizes([300, 600, 400])
        # ----------------------

        # Charger les données
        self.fert_base = charger_fertilisants(self)
        debug(f"Fertilisants chargés : {len(self.fert_base)}")
        self.cultures = charger_cultures(self)
        debug(f"Cultures chargées : {len(self.cultures)}")

        # Remplir les tableaux
        remplir_tableaux(self)

        self.cultures_selectionnee = None

        init_raccourcis(self)