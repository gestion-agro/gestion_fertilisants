# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import os
import requests

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, DB_FILE
import utils.debug as debug
import traceback
import bcrypt

GF_DIR = os.path.dirname(DB_FILE)


class SetupWizard(QDialog):
    """
    Wizard de premier lancement — 5 étapes :
    1. Bienvenue
    2. Bio ou Conventionnel ?
    3. Entreprise (pré-remplie depuis API BIO si bio, classique sinon)
    4. Type exploitation + ruches
    5. Compte administrateur
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration initiale")
        self.setMinimumWidth(560)
        self.setMinimumHeight(560)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

        self._est_bio = False
        self._data_bio = {}          # données récupérées depuis l'API BIO
        self._current = 0
        self._pages = []

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("background: #16a34a;")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(20, 0, 20, 0)
        lbl_title = QLabel("🌱 Configuration de GestionFertilisants")
        lbl_title.setStyleSheet(
            "color: white; font-size: 16px; font-weight: bold;")
        h_lay.addWidget(lbl_title)
        root.addWidget(header)

        # Barre d'étapes
        self.steps_bar = QWidget()
        self.steps_bar.setFixedHeight(36)
        self.steps_bar.setStyleSheet("background: #f0fdf4;")
        steps_lay = QHBoxLayout(self.steps_bar)
        steps_lay.setContentsMargins(20, 0, 20, 0)
        self._step_labels = []
        step_names = ["Bienvenue", "Type", "Entreprise", "Exploitation", "Compte"]
        for i, name in enumerate(step_names):
            lbl = QLabel(f"{i+1}. {name}")
            lbl.setStyleSheet("font-size: 11px; color: #9ca3af;")
            self._step_labels.append(lbl)
            steps_lay.addWidget(lbl)
            if i < len(step_names) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #d1d5db;")
                steps_lay.addWidget(sep)
        root.addWidget(self.steps_bar)

        # Stack de pages
        self.stack = QStackedWidget()
        self._pages = [
            self._page_bienvenue(),     # 0
            self._page_type(),          # 1
            self._page_entreprise(),    # 2
            self._page_exploitation(),  # 3
            self._page_compte(),        # 4
        ]
        for page in self._pages:
            self.stack.addWidget(page)
        root.addWidget(self.stack, 1)

        # Boutons nav
        nav = QHBoxLayout()
        nav.setContentsMargins(20, 12, 20, 12)
        self.btn_back = QPushButton("← Précédent")
        self.btn_back.setEnabled(False)
        self.btn_back.clicked.connect(self._prev)
        self.btn_next = QPushButton("Suivant →")
        self.btn_next.setDefault(True)
        self.btn_next.clicked.connect(self._next)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background: #16a34a; color: white;
                border-radius: 4px; padding: 6px 18px; font-weight: bold;
            }
            QPushButton:hover { background: #15803d; }
            QPushButton:disabled { background: #d1d5db; color: #9ca3af; }
        """)
        nav.addWidget(self.btn_back)
        nav.addStretch()
        nav.addWidget(self.btn_next)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        root.addWidget(sep)
        root.addLayout(nav)

        self._update_steps()

    # ──────────────────────────────────────────
    # Pages
    # ──────────────────────────────────────────
    def _page_bienvenue(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(16)

        lbl = QLabel("Bienvenue !")
        f = QFont(); f.setPointSize(20); f.setBold(True)
        lbl.setFont(f)
        lay.addWidget(lbl)

        desc = QLabel(
            "Ce wizard va configurer votre application en quelques étapes.\n\n"
            "Vous allez :\n"
            "  • Indiquer votre type de certification (bio ou conventionnel)\n"
            "  • Renseigner les informations de votre exploitation\n"
            "    (pré-remplissage automatique depuis l'Agence BIO si certifié)\n"
            "  • Choisir votre type de production\n"
            "  • Créer votre compte administrateur\n\n"
            "Ces informations pourront être modifiées à tout moment "
            "dans l'onglet Entreprise.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px; color: #374151;")
        lay.addWidget(desc)
        lay.addStretch()
        return w

    def _page_type(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(20)

        lbl = QLabel("Type de certification")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl.setFont(f)
        lay.addWidget(lbl)

        desc = QLabel(
            "Cette information permet de configurer les vérifications "
            "adaptées à votre exploitation.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        lay.addWidget(desc)

        self.btn_bio = QPushButton("🌿 Agriculture Biologique (certifiée AB)")
        self.btn_bio.setFixedHeight(70)
        self.btn_bio.setCheckable(True)
        self.btn_bio.setStyleSheet("""
            QPushButton {
                background: white; border: 2px solid #d1d5db;
                border-radius: 8px; font-size: 14px; text-align: left;
                padding: 0 20px;
            }
            QPushButton:checked {
                border-color: #16a34a; background: #f0fdf4; color: #15803d;
                font-weight: bold;
            }
            QPushButton:hover { border-color: #16a34a; }
        """)

        self.btn_conv = QPushButton("🌾 Agriculture Conventionnelle")
        self.btn_conv.setFixedHeight(70)
        self.btn_conv.setCheckable(True)
        self.btn_conv.setStyleSheet("""
            QPushButton {
                background: white; border: 2px solid #d1d5db;
                border-radius: 8px; font-size: 14px; text-align: left;
                padding: 0 20px;
            }
            QPushButton:checked {
                border-color: #2563eb; background: #eff6ff; color: #1d4ed8;
                font-weight: bold;
            }
            QPushButton:hover { border-color: #2563eb; }
        """)

        grp = QButtonGroup(self)
        grp.setExclusive(True)
        grp.addButton(self.btn_bio)
        grp.addButton(self.btn_conv)

        self.btn_bio.toggled.connect(self._on_type_changed)
        self.btn_conv.toggled.connect(self._on_type_changed)

        lay.addWidget(self.btn_bio)
        lay.addWidget(self.btn_conv)
        lay.addStretch()
        return w

    def _on_type_changed(self):
        self._est_bio = self.btn_bio.isChecked()
        # Adapter la page entreprise selon le type
        self._adapter_page_entreprise()

    def _page_entreprise(self) -> QWidget:
        w = QWidget()
        self._w_entreprise = w
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        self._form_entreprise = QFormLayout(inner)
        self._form_entreprise.setSpacing(10)
        self._form_entreprise.setContentsMargins(30, 20, 30, 20)

        # ── Section Bio : recherche par SIRET ──
        self._w_bio_search = QWidget()
        bio_lay = QVBoxLayout(self._w_bio_search)
        bio_lay.setContentsMargins(0, 0, 0, 0)
        bio_lay.setSpacing(10)

        lbl_bio = QLabel("Recherche automatique via l'Agence BIO")
        f = QFont(); f.setPointSize(13); f.setBold(True)
        lbl_bio.setFont(f)
        bio_lay.addWidget(lbl_bio)

        info_siret = QLabel(
            "Saisissez votre SIRET (14 chiffres) — les informations seront "
            "récupérées automatiquement depuis la base officielle de l'Agence BIO.")
        info_siret.setWordWrap(True)
        info_siret.setStyleSheet("color: #6b7280; font-size: 12px;")
        bio_lay.addWidget(info_siret)

        siret_row = QHBoxLayout()
        self.ent_siret_bio = QLineEdit()
        self.ent_siret_bio.setMaxLength(14)
        self.ent_siret_bio.setPlaceholderText("14 chiffres")
        self.ent_siret_bio.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,14}$")))
        self.btn_chercher_bio = QPushButton("🔍 Rechercher")
        self.btn_chercher_bio.setStyleSheet("""
            QPushButton { background:#16a34a; color:white;
                border-radius:4px; padding:6px 14px; }
            QPushButton:hover { background:#15803d; }
        """)
        self.btn_chercher_bio.clicked.connect(self._rechercher_api_bio)
        siret_row.addWidget(self.ent_siret_bio, 1)
        siret_row.addWidget(self.btn_chercher_bio)
        bio_lay.addLayout(siret_row)

        self.lbl_bio_status = QLabel("")
        self.lbl_bio_status.setWordWrap(True)
        bio_lay.addWidget(self.lbl_bio_status)

        self._form_entreprise.addRow(self._w_bio_search)

        # ── Avertissement pré-remplissage ──
        self._w_avertissement = QWidget()
        av_lay = QVBoxLayout(self._w_avertissement)
        av_lay.setContentsMargins(0, 0, 0, 0)
        lbl_av = QLabel(
            "ℹ Ces informations proviennent de la base officielle de l'Agence BIO "
            "(données gouvernementales). Si elles ne correspondent pas à votre "
            "situation réelle, vous pouvez les corriger ci-dessous et signaler "
            "l'écart à votre organisme certificateur.")
        lbl_av.setWordWrap(True)
        lbl_av.setStyleSheet(
            "background:#FEF9C3; border:1px solid #EAB308; border-radius:6px; "
            "padding:10px; color:#713F12; font-size:11px;")
        av_lay.addWidget(lbl_av)
        self._w_avertissement.setVisible(False)
        self._form_entreprise.addRow(self._w_avertissement)

        # ── Champs communs ──
        self.ent_nom = QLineEdit()
        self.ent_nom.setPlaceholderText("EARL Dupont, GAEC Les Jardins...")

        self.ent_siret = QLineEdit()
        self.ent_siret.setMaxLength(14)
        self.ent_siret.setPlaceholderText("14 chiffres")
        self.ent_siret.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,14}$")))

        self.ent_adresse = QLineEdit()

        self.ent_cp = QLineEdit()
        self.ent_cp.setMaxLength(5)
        self.ent_cp.setFixedWidth(80)
        self.ent_cp.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,5}$")))
        self.ent_ville = QLineEdit()
        cp_ville = QWidget()
        cp_lay = QHBoxLayout(cp_ville)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.addWidget(self.ent_cp)
        cp_lay.addWidget(self.ent_ville)

        # Téléphone : +33 figé + 9 chiffres
        tel_w = QWidget()
        tel_lay = QHBoxLayout(tel_w)
        tel_lay.setContentsMargins(0, 0, 0, 0)
        tel_lay.setSpacing(4)
        lbl_indicatif = QLabel("+33")
        lbl_indicatif.setStyleSheet(
            "background: #f3f4f6; border: 1px solid #d1d5db; "
            "border-radius: 3px; padding: 4px 8px; color: #374151;")
        lbl_indicatif.setFixedWidth(40)
        self.ent_tel = QLineEdit()
        self.ent_tel.setMaxLength(9)
        self.ent_tel.setPlaceholderText("9 chiffres (sans le 0 initial)")
        self.ent_tel.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^\d{0,9}$")))
        tel_lay.addWidget(lbl_indicatif)
        tel_lay.addWidget(self.ent_tel)

        self.ent_email = QLineEdit()

        self.ent_num_tva = QLineEdit()
        self.ent_num_tva.setMaxLength(13)
        self.ent_num_tva.setPlaceholderText("FR + 11 chiffres")
        self.ent_num_tva.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^(FR)?\d{0,11}$",
                                   QRegularExpression.CaseInsensitiveOption)))

        # Champs bio (masqués si conventionnel)
        self.ent_num_bio = QLineEdit()
        self.ent_num_bio.setMaxLength(50)
        self.ent_num_bio.setPlaceholderText("Numéro opérateur Agence BIO")
        self.ent_num_bio.setReadOnly(True)
        self.ent_num_bio.setStyleSheet(
            "background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;")
        self.ent_org_certif = QLineEdit()
        self.ent_org_certif.setPlaceholderText("Ex: Ecocert, Bureau Veritas...")
        self.ent_lien_certif = QLineEdit()
        self.ent_lien_certif.setReadOnly(True)
        self.ent_lien_certif.setStyleSheet(
            "background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;")

        self._form_entreprise.addRow("Nom exploitation *", self.ent_nom)
        self._form_entreprise.addRow("SIRET *",            self.ent_siret)
        self._form_entreprise.addRow("Adresse",            self.ent_adresse)
        self._form_entreprise.addRow("CP / Ville",         cp_ville)
        self._form_entreprise.addRow("Téléphone",          tel_w)
        self._form_entreprise.addRow("Email",              self.ent_email)
        self._form_entreprise.addRow("N° TVA",             self.ent_num_tva)

        # Labels bio (stockés pour les cacher/afficher)
        self._lbl_num_bio  = QLabel("N° opérateur BIO")
        self._lbl_org_certif = QLabel("Organisme certif.")
        self._lbl_lien_certif = QLabel("Lien certificat")
        self._form_entreprise.addRow(self._lbl_num_bio,    self.ent_num_bio)
        self._form_entreprise.addRow(self._lbl_org_certif, self.ent_org_certif)
        self._form_entreprise.addRow(self._lbl_lien_certif, self.ent_lien_certif)

        scroll.setWidget(inner)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._adapter_page_entreprise()
        return w

    def _adapter_page_entreprise(self):
        """Affiche/masque les sections selon bio ou conventionnel."""
        if not hasattr(self, "_w_bio_search"):
            return
        self._w_bio_search.setVisible(self._est_bio)
        champs_bio_visibles = self._est_bio
        self._lbl_num_bio.setVisible(champs_bio_visibles)
        self.ent_num_bio.setVisible(champs_bio_visibles)
        self._lbl_org_certif.setVisible(champs_bio_visibles)
        self.ent_org_certif.setVisible(champs_bio_visibles)
        self._lbl_lien_certif.setVisible(champs_bio_visibles)
        self.ent_lien_certif.setVisible(champs_bio_visibles)
        # En conventionnel le SIRET est saisi directement
        self.ent_siret.setReadOnly(self._est_bio)

    def _rechercher_api_bio(self):
        siret = self.ent_siret_bio.text().strip()
        if len(siret) != 14 or not siret.isdigit():
            self.lbl_bio_status.setText(
                "⚠ Saisissez un SIRET valide (14 chiffres).")
            self.lbl_bio_status.setStyleSheet("color: #DC2626;")
            return

        self.btn_chercher_bio.setEnabled(False)
        self.lbl_bio_status.setText("⏳ Recherche en cours...")
        self.lbl_bio_status.setStyleSheet("color: #6b7280;")
        QApplication.processEvents()

        try:
            from logic.verif_entreprise import verifier_agence_bio
            r = verifier_agence_bio(siret=siret)

            if r.get("erreur") or not r.get("trouve"):
                self.lbl_bio_status.setText(
                    f"❌ {r.get('erreur') or 'Aucun opérateur trouvé pour ce SIRET.'}\n"
                    "Vérifiez votre SIRET ou renseignez manuellement vos informations.")
                self.lbl_bio_status.setStyleSheet("color: #DC2626;")
                self.btn_chercher_bio.setEnabled(True)
                return

            # Pré-remplissage
            self._data_bio = r
            self.ent_nom.setText(r.get("nom_officiel") or "")
            self.ent_siret.setText(siret)

            # Calcul automatique N° TVA depuis SIREN
            siren = siret[:9]
            if siren.isdigit():
                cle_tva = (12 + 3 * (int(siren) % 97)) % 97
                self.ent_num_tva.setText(f"FR{cle_tva:02d}{siren}")

            # Adresse depuis l'API BIO (adressesOperateurs)
            adresses = r.get("adresses") or []
            if adresses:
                adr = adresses[0]
                self.ent_adresse.setText(adr.get("lieu") or adr.get("adresse") or "")
                self.ent_cp.setText(str(adr.get("codePostal") or ""))
                self.ent_ville.setText(adr.get("ville") or "")

            self.ent_org_certif.setText(r.get("organisme_certif_officiel") or "")
            self.ent_num_bio.setText(r.get("numero_bio_trouve") or "")
            self.ent_lien_certif.setText(r.get("lien_certificat") or "")

            alertes = r.get("alertes") or []
            nb_alertes = len(alertes)
            if nb_alertes:
                self.lbl_bio_status.setText(
                    f"✅ Opérateur trouvé — {nb_alertes} point(s) à vérifier :\n"
                    + "\n".join(alertes))
                self.lbl_bio_status.setStyleSheet("color: #D97706;")
            else:
                self.lbl_bio_status.setText(
                    f"✅ Opérateur trouvé et informations cohérentes — "
                    f"État : {r.get('etat_certif') or '—'} | "
                    f"Production : {r.get('etat_production') or '—'}")
                self.lbl_bio_status.setStyleSheet("color: #16a34a;")

            self._w_avertissement.setVisible(True)

        except Exception as e:
            debug.debug(f"[wizard] Erreur recherche BIO : {e}")
            traceback.print_exc()
            self.lbl_bio_status.setText(f"❌ Erreur : {e}")
            self.lbl_bio_status.setStyleSheet("color: #DC2626;")
        finally:
            self.btn_chercher_bio.setEnabled(True)

    def _page_exploitation(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(30, 20, 30, 20)
        lay.setSpacing(16)

        lbl_titre = QLabel("Type d'exploitation")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl_titre.setFont(f)
        lay.addWidget(lbl_titre)

        types_group = QGroupBox("Production principale *")
        types_lay = QVBoxLayout(types_group)
        self.chk_maraichage   = QCheckBox("Maraîchage")
        self.chk_grandes_cult = QCheckBox("Grandes cultures / Arboriculture")
        for chk in (self.chk_maraichage, self.chk_grandes_cult):
            chk.setStyleSheet("font-size: 13px;")
            types_lay.addWidget(chk)
        lay.addWidget(types_group)

        ruches_group = QGroupBox("Apiculture")
        ruches_lay = QVBoxLayout(ruches_group)
        self.chk_ruches = QCheckBox("Mon exploitation possède des ruches")
        self.chk_ruches.setStyleSheet("font-size: 13px;")
        self.chk_ruches.toggled.connect(self._on_ruches_toggled)
        ruches_lay.addWidget(self.chk_ruches)

        self.w_ruches_infos = QWidget()
        ri_lay = QFormLayout(self.w_ruches_infos)
        ri_lay.setContentsMargins(20, 8, 0, 0)
        self.ent_napi = QLineEdit()
        self.ent_napi.setMaxLength(12)
        self.ent_napi.setPlaceholderText("12 caractères max (ex: A5218882)")
        self.ent_napi.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"^[A-Za-z0-9]{0,12}$")))
        ri_lay.addRow("N° NAPI *", self.ent_napi)
        ri_lay.addRow("", QLabel("Format : lettres + chiffres, 12 caractères max"))
        self.w_ruches_infos.setVisible(False)
        ruches_lay.addWidget(self.w_ruches_infos)
        lay.addWidget(ruches_group)
        lay.addStretch()
        return w

    def _on_ruches_toggled(self, checked: bool):
        self.w_ruches_infos.setVisible(checked)

    def _page_compte(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(30, 20, 30, 20)
        lay.setSpacing(16)

        lbl = QLabel("Compte administrateur")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl.setFont(f)
        lay.addWidget(lbl)

        desc = QLabel(
            "Ce compte aura tous les droits.\n"
            "Vous pourrez créer d'autres utilisateurs ensuite.")
        desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        lay.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)
        self.acc_prenom   = QLineEdit()
        self.acc_nom      = QLineEdit()
        self.acc_username = QLineEdit()
        self.acc_mdp      = QLineEdit()
        self.acc_mdp.setEchoMode(QLineEdit.Password)
        self.acc_mdp2     = QLineEdit()
        self.acc_mdp2.setEchoMode(QLineEdit.Password)
        self.acc_mdp2.setPlaceholderText("Confirmer le mot de passe")

        form.addRow("Prénom *",        self.acc_prenom)
        form.addRow("Nom *",           self.acc_nom)
        form.addRow("Identifiant *",   self.acc_username)
        form.addRow("Mot de passe *",  self.acc_mdp)
        form.addRow("Confirmer mdp *", self.acc_mdp2)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        form.addRow(self.lbl_err)

        lay.addLayout(form)
        lay.addStretch()
        return w

    # ──────────────────────────────────────────
    # Navigation
    # ──────────────────────────────────────────
    def _update_steps(self):
        for i, lbl in enumerate(self._step_labels):
            if i == self._current:
                lbl.setStyleSheet(
                    "font-size: 11px; color: #16a34a; font-weight: bold;")
            elif i < self._current:
                lbl.setStyleSheet("font-size: 11px; color: #6b7280;")
            else:
                lbl.setStyleSheet("font-size: 11px; color: #d1d5db;")
        self.btn_back.setEnabled(self._current > 0)
        if self._current == len(self._pages) - 1:
            self.btn_next.setText("✓ Terminer")
        else:
            self.btn_next.setText("Suivant →")

    def _prev(self):
        if self._current > 0:
            self._current -= 1
            self.stack.setCurrentIndex(self._current)
            self._update_steps()

    def _next(self):
        # ── Validations par étape ──
        if self._current == 1:
            if not self.btn_bio.isChecked() and not self.btn_conv.isChecked():
                QMessageBox.warning(self, "Choix requis",
                    "Sélectionnez votre type de certification.")
                return

        if self._current == 2:
            nom = self.ent_nom.text().strip()
            if not nom:
                QMessageBox.warning(self, "Champ manquant",
                    "Le nom de l'exploitation est obligatoire.")
                return

            if self._est_bio:
                if not self.ent_siret.text().strip():
                    QMessageBox.warning(self, "SIRET manquant",
                        "Recherchez votre exploitation par SIRET "
                        "ou renseignez-le manuellement.")
                    return
            else:
                siret = self.ent_siret.text().strip()
                if siret:
                    from logic.verif_entreprise import valider_siret
                    ok, msg = valider_siret(siret)
                    if not ok:
                        rep = QMessageBox.warning(self, "SIRET invalide",
                            f"{msg}\n\nContinuer quand même ?",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                        if rep == QMessageBox.No:
                            return

            tva = self.ent_num_tva.text().strip().upper()
            if tva:
                tva_chiffres = tva.lstrip("FR")
                if not tva_chiffres.isdigit() or len(tva_chiffres) != 11:
                    QMessageBox.warning(self, "N° TVA invalide",
                        "Format attendu : FR + 11 chiffres.")
                    return

            tel = self.ent_tel.text().strip()
            if tel and len(tel) != 9:
                QMessageBox.warning(self, "Téléphone invalide",
                    "9 chiffres requis (après l'indicatif +33).")
                return

        if self._current == 3:
            if not self.chk_maraichage.isChecked() and \
               not self.chk_grandes_cult.isChecked():
                QMessageBox.warning(self, "Champ manquant",
                    "Sélectionnez au moins un type de production.")
                return
            if self.chk_ruches.isChecked():
                napi = self.ent_napi.text().strip()
                if not napi or len(napi) < 4:
                    QMessageBox.warning(self, "N° NAPI invalide",
                        "Le N° NAPI doit contenir au moins 4 caractères.")
                    return

        if self._current == len(self._pages) - 1:
            if self._valider():
                self.accept()
            return

        self._current += 1
        self.stack.setCurrentIndex(self._current)
        self._update_steps()

    # ──────────────────────────────────────────
    # Validation finale
    # ──────────────────────────────────────────
    def _valider(self) -> bool:
        prenom   = self.acc_prenom.text().strip()
        nom      = self.acc_nom.text().strip()
        username = self.acc_username.text().strip()
        mdp      = self.acc_mdp.text()
        mdp2     = self.acc_mdp2.text()

        if not all([prenom, nom, username, mdp]):
            self.lbl_err.setText("Tous les champs sont obligatoires.")
            return False
        if mdp != mdp2:
            self.lbl_err.setText("Les mots de passe ne correspondent pas.")
            return False
        if len(mdp) < 6:
            self.lbl_err.setText("Mot de passe trop court (6 caractères min).")
            return False

        types = []
        if self.chk_maraichage.isChecked():
            types.append("maraichage")
        if self.chk_grandes_cult.isChecked():
            types.append("grandes_cultures")
        type_exploit = ",".join(types) or None

        has_ruches = 1 if self.chk_ruches.isChecked() else 0

        tel_brut = self.ent_tel.text().strip()
        tel_complet = f"+33{tel_brut}" if tel_brut else None

        tva = self.ent_num_tva.text().strip().upper() or None
        if tva and not tva.startswith("FR"):
            tva = f"FR{tva}"

        num_bio    = self.ent_num_bio.text().strip() or None
        org_certif = self.ent_org_certif.text().strip() or None
        lien_certif = self.ent_lien_certif.text().strip() or None
        siret = self.ent_siret.text().strip() or None

        try:
            conn = get_connection()
            cur  = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO entreprise
                (id, nom, siret, adresse, code_postal, ville,
                 telephone, email, num_tva, num_bio, organisme_certif,
                 type_exploitation, has_ruches, num_napi)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.ent_nom.text().strip(),
                siret,
                self.ent_adresse.text().strip() or None,
                self.ent_cp.text().strip() or None,
                self.ent_ville.text().strip() or None,
                tel_complet,
                self.ent_email.text().strip() or None,
                tva, num_bio, org_certif,
                type_exploit, has_ruches,
                self.ent_napi.text().strip().upper() or None,
            ))

            pw_hash = bcrypt.hashpw(mdp.encode(), bcrypt.gensalt()).decode()
            cur.execute("""
                INSERT INTO users
                (nom, prenom, username, password_hash, role, actif)
                VALUES (?, ?, ?, ?, 'admin', 1)
            """, (nom, prenom, username, pw_hash))

            conn.commit()
            cur.close()
            debug.debug(f"[wizard] Setup terminé — bio={self._est_bio} "
                        f"type={type_exploit} ruches={has_ruches}")

            # Téléchargement du certificat bio si lien disponible
            if self._est_bio and lien_certif:
                self._telecharger_certificat(lien_certif, siret or "certif")

            return True

        except Exception as e:
            debug.debug(f"[wizard] Erreur : {e}")
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")
            return False

    def _telecharger_certificat(self, url: str, siret: str):
        """Télécharge le certificat bio PDF et le stocke localement."""
        try:
            nom_fichier = f"certificat_bio_{siret}.pdf"
            chemin = os.path.join(GF_DIR, nom_fichier)
            debug.debug(f"[wizard] Téléchargement certificat : {url}")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            with open(chemin, "wb") as f:
                f.write(resp.content)
            debug.debug(f"[wizard] Certificat stocké : {chemin}")

            # Stocker le chemin local dans la BDD
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE entreprise SET logo_path=? WHERE id=1",
                (chemin,))
            conn.commit()
            cur.close()
        except Exception as e:
            debug.debug(f"[wizard] Impossible de télécharger le certificat : {e}")