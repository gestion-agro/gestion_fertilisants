# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug


# ── Contenu de l'aide par module ──────────────
# Structure : {section: [(titre, texte), ...]}
# Facilement extensible / traduisible
AIDE_CONTENU = {
    "🏢 Entreprise": [
        ("Informations générales",
         "Renseignez le nom, SIRET, adresse, téléphone et email de votre exploitation. "
         "Ces informations apparaissent sur vos exports (carnet de traitements, etc.)."),
        ("Certification biologique",
         "Si vous êtes certifié AB, renseignez votre numéro d'agrément bio et votre "
         "organisme certificateur. L'application adaptera automatiquement les alertes "
         "et vérifications (produits non-UAB, etc.)."),
        ("Production",
         "Indiquez votre type de production (maraîchage, arboriculture) et si vous "
         "possédez des ruches (affiche l'onglet Ruches dans la navigation)."),
        ("Vérification",
         "L'onglet Vérification interroge l'API de l'Agence BIO pour confirmer que "
         "vos informations (SIRET, nom, OC) correspondent aux données officielles."),
    ],
    "🌱 Parcelles": [
        ("Créer une parcelle",
         "Cliquez sur '+ Ajouter une parcelle'. Renseignez le nom, le type de sol "
         "et la surface totale (en ha). Une parcelle peut contenir plusieurs cultures."),
        ("Ajouter une culture",
         "Sélectionnez une parcelle puis cliquez '+ Culture'. Choisissez la catégorie "
         "(maraîchage, arboriculture, engrais vert, jachère) et renseignez l'espèce, "
         "la variété et les données de plantation."),
        ("Besoins NPK",
         "Pour les cultures maraîchage et arbo, renseignez les besoins NPK (kg/ha). "
         "Ces valeurs sont partagées avec le module Fertilisants — modifier le NPK "
         "ici le met à jour automatiquement dans l'aide à la décision."),
        ("Systèmes d'irrigation",
         "Ajoutez des systèmes d'irrigation liés à une ou plusieurs cultures de la "
         "parcelle. Pour les systèmes goutteurs, le nombre d'émetteurs est calculé "
         "automatiquement depuis la longueur des planches."),
        ("Catégories PPP",
         "Chaque culture peut être associée à une ou plusieurs catégories e-phy "
         "(ex: Tomate, Aubergine). Ces catégories sont utilisées dans le Carnet PPP "
         "pour vérifier l'homologation des produits."),
    ],
    "💧 Irrigation": [
        ("Enregistrer un apport",
         "Sélectionnez la parcelle puis le système d'irrigation. "
         "Renseignez la date, la durée et le volume apporté. "
         "L'historique est consultable par parcelle et par période."),
        ("Cultures couvertes",
         "Chaque système d'irrigation indique les cultures qu'il couvre. "
         "Cette information apparaît dans l'historique pour tracer les apports "
         "par culture."),
    ],
    "🐝 Ruches": [
        ("Gérer ses ruches",
         "Ajoutez vos ruches avec leur nom, numéro NAPI, race, type et date "
         "d'installation. Associez-les à une parcelle si nécessaire."),
        ("Visites et interventions",
         "Enregistrez chaque visite (date, état varroa, reine, couvain, population) "
         "et les interventions associées (sirop, candi, varroa, hausse...). "
         "Le résumé de la dernière visite apparaît sous le bouton 'Nouvelle visite'."),
        ("Permissions apiculteur",
         "L'administrateur peut marquer un utilisateur comme 'Apiculteur' pour lui "
         "donner accès aux fonctions de suppression de ruches."),
    ],
    "🌿 PPP (Phytosanitaires)": [
        ("Catalogue e-phy",
         "Importez le catalogue des produits phytosanitaires depuis e-phy "
         "(Ministère de l'Agriculture). L'import peut prendre quelques minutes. "
         "Les données sont mises à jour périodiquement."),
        ("Aide à la décision",
         "Sélectionnez une culture et un bio-agresseur pour obtenir la liste des "
         "produits homologués, avec leur dose max, DAR et conditions d'usage. "
         "En exploitation bio, seuls les produits bio-compatibles sont proposés par défaut."),
        ("Carnet de traitements",
         "Les décideurs (CON, DESA, DENSA) créent des décisions de traitement. "
         "Les opérateurs (OPE) les confirment en renseignant les données réelles "
         "(dose appliquée, météo, EPI, signature)."),
        ("Export contrôleur bio",
         "Dans l'historique des traitements, cliquez 'Export PDF contrôleur' pour "
         "générer un document prêt à remettre lors d'un contrôle bio. "
         "Les colonnes exportées sont configurables dans Paramètres → Application."),
        ("Produits non bio en exploitation bio",
         "Si votre exploitation est certifiée AB et qu'un produit non bio-compatible "
         "est utilisé, un avertissement fort s'affiche avant validation. "
         "L'usage reste possible (dérogation réglementaire possible selon l'annexe II "
         "du règlement bio) mais doit être signalé à votre OC."),
    ],
    "🧪 Fertilisants": [
        ("Catalogue",
         "Gérez votre stock de fertilisants : nom, composition NPK (%), prix, "
         "conditionnement, stock disponible, UAB et coordonnées du revendeur. "
         "Le stock est décrémenté automatiquement à chaque apport au carnet."),
        ("Aide à la décision",
         "Sélectionnez une culture (liée à une parcelle ou générique) pour obtenir "
         "les doses recommandées. Le solveur PuLP optimise automatiquement la "
         "combinaison de fertilisants la moins chère respectant les besoins NPK. "
         "Mode strict disponible pour imposer des fertilisants précis."),
        ("Tolérance NPK",
         "La tolérance (défaut 2%) permet au solveur de trouver une solution même si "
         "la combinaison exacte est impossible. Modifiable dans Paramètres → Application."),
        ("Carnet de fertilisation",
         "Enregistrez chaque apport réel (date, parcelle, culture, fertilisant, dose). "
         "Le suivi de l'azote organique (plafond réglementaire : 170 kg N/ha/an, "
         "directive nitrates) est calculé automatiquement avec règle de trois sur la "
         "surface traitée réelle."),
        ("Produits non UAB en exploitation bio",
         "En exploitation certifiée AB, les fertilisants non-UAB sont signalés en rouge "
         "dans le carnet et un avertissement fort s'affiche avant validation."),
    ],
    "⚙️ Administration": [
        ("Gestion des utilisateurs",
         "Créez des comptes utilisateurs sans mot de passe initial (l'utilisateur "
         "définit son mot de passe à la première connexion via le lien 'Première connexion'). "
         "Double-cliquez sur un utilisateur pour le modifier."),
        ("Permissions",
         "Chaque utilisateur dispose d'une matrice de permissions par module "
         "(lecture / écriture / suppression). Les presets 'Lecture seule' et "
         "'Lecture + Écriture' simplifient la configuration."),
        ("CertiPhyto",
         "Renseignez le type de certification phytosanitaire (CON, DESA, DENSA, OPE, MV/V) "
         "et sa date d'expiration pour chaque utilisateur. "
         "Le type conditionne l'accès aux modules PPP."),
        ("Reset mot de passe",
         "Utilisez 'Forcer reset mdp' dans le menu contextuel pour obliger un "
         "utilisateur à changer son mot de passe à sa prochaine connexion."),
        ("Modifier son propre compte",
         "L'administrateur peut modifier ses propres informations (nom, prénom, mdp) "
         "mais pas son identifiant de connexion (pour éviter les blocages accidentels)."),
    ],
    "🔧 Paramètres": [
        ("Mon compte",
         "Consultez vos informations et changez votre mot de passe depuis l'onglet "
         "'Mon compte'. La connexion automatique peut être activée depuis 'Connexion'."),
        ("Application (admin)",
         "Les administrateurs peuvent configurer : largeur de planche et passe-pied "
         "par défaut, tolérance NPK pour le solveur, et colonnes de l'export PDF "
         "contrôleur bio (portrait/paysage, N° AMM, DAR, météo, EPI...)."),
    ],
}


class AidePage(QWidget):
    """Page d'aide statique avec recherche et didacticiel."""

    # Signal pour demander le lancement du didacticiel
    lancer_didacticiel = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # En-tête
        header = QHBoxLayout()
        titre = QLabel("Aide")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        header.addWidget(titre)
        header.addStretch()

        btn_didacticiel = QPushButton("▶ Lancer le didacticiel interactif")
        btn_didacticiel.setFixedHeight(34)
        btn_didacticiel.setStyleSheet("""
            QPushButton {
                background: #2563EB; color: white; border-radius: 4px;
                padding: 0 14px; font-weight: bold;
            }
            QPushButton:hover { background: #1d4ed8; }
        """)
        btn_didacticiel.clicked.connect(self.lancer_didacticiel.emit)
        header.addWidget(btn_didacticiel)
        root.addLayout(header)

        # Barre de recherche
        self.inp_recherche = QLineEdit()
        self.inp_recherche.setPlaceholderText(
            "🔍 Rechercher dans l'aide (ex: varroa, SIRET, NPK, carnet...)")
        self.inp_recherche.setFixedHeight(34)
        self.inp_recherche.textChanged.connect(self._filtrer)
        root.addWidget(self.inp_recherche)

        # Zone de contenu scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._contenu_widget = QWidget()
        self._contenu_lay = QVBoxLayout(self._contenu_widget)
        self._contenu_lay.setSpacing(8)
        self._contenu_lay.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self._contenu_widget)
        root.addWidget(scroll, 1)

        self._build_contenu()

    def _build_contenu(self, filtre: str = ""):
        # Vider le contenu précédent
        while self._contenu_lay.count():
            item = self._contenu_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtre = filtre.lower().strip()
        nb_resultats = 0

        for section, items in AIDE_CONTENU.items():
            items_filtres = []
            for titre, texte in items:
                if not filtre or filtre in titre.lower() or filtre in texte.lower() \
                        or filtre in section.lower():
                    items_filtres.append((titre, texte))

            if not items_filtres:
                continue

            # Section
            group = QGroupBox(section)
            group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold; font-size: 13px;
                    border: 1px solid #e5e7eb; border-radius: 6px;
                    margin-top: 8px; padding-top: 8px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 12px; padding: 0 6px;
                }
            """)
            g_lay = QVBoxLayout(group)
            g_lay.setSpacing(6)

            for titre, texte in items_filtres:
                # Titre de l'entrée
                lbl_titre = QLabel(f"<b>{titre}</b>")
                lbl_titre.setStyleSheet("color: #1f2937; font-size: 12px;")
                g_lay.addWidget(lbl_titre)

                # Texte avec surbrillance du terme recherché
                texte_affiche = texte
                if filtre:
                    texte_affiche = texte.replace(
                        filtre,
                        f"<mark style='background:#FEF9C3'>{filtre}</mark>")
                    # Aussi pour les majuscules
                    texte_affiche = texte_affiche.replace(
                        filtre.capitalize(),
                        f"<mark style='background:#FEF9C3'>{filtre.capitalize()}</mark>")

                lbl_texte = QLabel(texte_affiche)
                lbl_texte.setWordWrap(True)
                lbl_texte.setStyleSheet(
                    "color: #4b5563; font-size: 12px; padding-left: 12px;")
                lbl_texte.setTextFormat(Qt.RichText)
                g_lay.addWidget(lbl_texte)

                if (titre, texte) != items_filtres[-1]:
                    sep = QFrame()
                    sep.setFrameShape(QFrame.HLine)
                    sep.setStyleSheet("color: #f3f4f6;")
                    g_lay.addWidget(sep)

                nb_resultats += 1

            self._contenu_lay.addWidget(group)

        if nb_resultats == 0 and filtre:
            lbl_vide = QLabel(
                f"Aucun résultat pour « {filtre} ».\n"
                "Essayez avec d'autres mots-clés.")
            lbl_vide.setAlignment(Qt.AlignCenter)
            lbl_vide.setStyleSheet("color: palette(mid); padding: 40px;")
            self._contenu_lay.addWidget(lbl_vide)

        self._contenu_lay.addStretch()

    def _filtrer(self, texte: str):
        self._build_contenu(texte)