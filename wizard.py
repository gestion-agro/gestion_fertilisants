# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
import utils.debug as debug
import traceback
import bcrypt


class SetupWizard(QDialog):
    """
    Wizard de premier lancement — 4 étapes :
    1. Bienvenue
    2. Mon entreprise (nom, siret, adresse...)
    3. Type d'exploitation + ruches
    4. Créer le compte administrateur
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration initiale")
        self.setMinimumWidth(540)
        self.setMinimumHeight(520)
        self.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)

        self._pages = []
        self._current = 0

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header coloré
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

        # Indicateur d'étapes
        self.steps_bar = QWidget()
        self.steps_bar.setFixedHeight(36)
        self.steps_bar.setStyleSheet("background: #f0fdf4;")
        steps_lay = QHBoxLayout(self.steps_bar)
        steps_lay.setContentsMargins(20, 0, 20, 0)
        self._step_labels = []
        step_names = ["Bienvenue", "Entreprise", "Exploitation", "Compte"]
        for i, name in enumerate(step_names):
            lbl = QLabel(f"{i+1}. {name}")
            lbl.setStyleSheet("font-size: 12px; color: #9ca3af;")
            self._step_labels.append(lbl)
            steps_lay.addWidget(lbl)
            if i < len(step_names) - 1:
                sep = QLabel("›")
                sep.setStyleSheet("color: #9ca3af;")
                steps_lay.addWidget(sep)
        root.addWidget(self.steps_bar)

        # Stack de pages
        self.stack = QStackedWidget()
        self._pages = [
            self._page_bienvenue(),
            self._page_entreprise(),
            self._page_exploitation(),
            self._page_compte(),
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
                border-radius: 4px; padding: 6px 18px;
                font-weight: bold;
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
            "  • Renseigner les informations de votre exploitation\n"
            "  • Choisir votre type de production\n"
            "  • Créer votre compte administrateur\n\n"
            "Ces informations pourront être modifiées à tout moment "
            "dans l'onglet Entreprise.")
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 14px; color: #374151; line-height: 1.5;")
        lay.addWidget(desc)
        lay.addStretch()
        return w

    def _page_entreprise(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setSpacing(10)
        form.setContentsMargins(30, 20, 30, 20)

        lbl_titre = QLabel("Votre exploitation")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl_titre.setFont(f)
        form.addRow(lbl_titre)

        self.ent_nom = QLineEdit()
        self.ent_nom.setPlaceholderText("EARL Dupont, GAEC Les Jardins...")

        # SIRET : 14 chiffres uniquement
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

        # N° TVA : FR + 11 chiffres (13 caractères)
        self.ent_num_tva = QLineEdit()
        self.ent_num_tva.setMaxLength(13)
        self.ent_num_tva.setPlaceholderText("FR + 11 chiffres (ex: FR12345678910)")
        self.ent_num_tva.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^(FR)?\d{0,11}$", QRegularExpression.CaseInsensitiveOption)))

        # N° agrément bio : format libre mais borné
        self.ent_num_bio = QLineEdit()
        self.ent_num_bio.setMaxLength(50)
        self.ent_num_bio.setPlaceholderText("Ex: FR-BIO-01-12345 (si agriculture biologique)")

        self.ent_org_certif = QLineEdit()
        self.ent_org_certif.setPlaceholderText("Ex: Ecocert, Bureau Veritas...")

        cp_ville = QWidget()
        cp_lay = QHBoxLayout(cp_ville)
        cp_lay.setContentsMargins(0, 0, 0, 0)
        cp_lay.addWidget(self.ent_cp)
        cp_lay.addWidget(self.ent_ville)

        form.addRow("Nom exploitation *", self.ent_nom)
        form.addRow("SIRET",              self.ent_siret)
        form.addRow("Adresse",            self.ent_adresse)
        form.addRow("CP / Ville",         cp_ville)
        form.addRow("Téléphone",          tel_w)
        form.addRow("Email",              self.ent_email)
        form.addRow("N° TVA",             self.ent_num_tva)
        form.addRow("N° agrément bio",    self.ent_num_bio)
        form.addRow("Organisme certif.",  self.ent_org_certif)

        scroll.setWidget(inner)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(scroll)
        return w

    def _page_exploitation(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(30, 20, 30, 20)
        lay.setSpacing(16)

        lbl_titre = QLabel("Type d'exploitation")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl_titre.setFont(f)
        lay.addWidget(lbl_titre)

        desc = QLabel(
            "Ces informations permettent de pré-configurer l'application "
            "pour votre type de production.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        lay.addWidget(desc)

        # Type d'exploitation
        types_group = QGroupBox("Production principale *")
        types_lay = QVBoxLayout(types_group)
        types_lay.setSpacing(8)

        self.chk_maraichage   = QCheckBox("Maraîchage")
        self.chk_grandes_cult = QCheckBox("Grandes cultures / Arboriculture")
        self.chk_maraichage.setStyleSheet("font-size: 13px;")
        self.chk_grandes_cult.setStyleSheet("font-size: 13px;")
        types_lay.addWidget(self.chk_maraichage)
        types_lay.addWidget(self.chk_grandes_cult)
        lay.addWidget(types_group)

        # Ruches
        ruches_group = QGroupBox("Apiculture")
        ruches_lay = QVBoxLayout(ruches_group)

        self.chk_ruches = QCheckBox("Mon exploitation possède des ruches")
        self.chk_ruches.setStyleSheet("font-size: 13px;")
        self.chk_ruches.toggled.connect(self._on_ruches_toggled)
        ruches_lay.addWidget(self.chk_ruches)

        # Infos ruches (conditionnelles)
        self.w_ruches_infos = QWidget()
        ri_lay = QFormLayout(self.w_ruches_infos)
        ri_lay.setContentsMargins(20, 8, 0, 0)
        ri_lay.setSpacing(8)

        # NAPI : 12 caractères alphanumériques (lettres + chiffres)
        self.ent_napi = QLineEdit()
        self.ent_napi.setMaxLength(12)
        self.ent_napi.setPlaceholderText("12 caractères (ex: A5218882)")
        self.ent_napi.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"^[A-Za-z0-9]{0,12}$")))

        napi_info = QLabel("Format : 1-2 lettres + chiffres, 12 caractères max")
        napi_info.setStyleSheet("color: #9ca3af; font-size: 11px;")

        ri_lay.addRow("N° NAPI *", self.ent_napi)
        ri_lay.addRow("", napi_info)
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

        lbl_titre = QLabel("Compte administrateur")
        f = QFont(); f.setPointSize(14); f.setBold(True)
        lbl_titre.setFont(f)
        lay.addWidget(lbl_titre)

        desc = QLabel(
            "Ce compte aura tous les droits sur l'application.\n"
            "Vous pourrez créer d'autres utilisateurs ensuite.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #6b7280; font-size: 12px;")
        lay.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(10)

        self.acc_prenom   = QLineEdit()
        self.acc_nom      = QLineEdit()
        self.acc_username = QLineEdit()
        self.acc_username.setPlaceholderText("Identifiant de connexion")
        self.acc_mdp      = QLineEdit()
        self.acc_mdp.setEchoMode(QLineEdit.Password)
        self.acc_mdp2     = QLineEdit()
        self.acc_mdp2.setEchoMode(QLineEdit.Password)
        self.acc_mdp2.setPlaceholderText("Confirmer le mot de passe")

        form.addRow("Prénom *",       self.acc_prenom)
        form.addRow("Nom *",          self.acc_nom)
        form.addRow("Identifiant *",  self.acc_username)
        form.addRow("Mot de passe *", self.acc_mdp)
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
                    "font-size: 12px; color: #16a34a; font-weight: bold;")
            elif i < self._current:
                lbl.setStyleSheet("font-size: 12px; color: #6b7280;")
            else:
                lbl.setStyleSheet("font-size: 12px; color: #d1d5db;")

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
        if self._current == 1:
            if not self.ent_nom.text().strip():
                QMessageBox.warning(self, "Champ manquant",
                    "Le nom de l'exploitation est obligatoire.")
                return
            # Validation SIRET longueur exacte si renseigné
            siret = self.ent_siret.text().strip()
            if siret and len(siret) != 14:
                QMessageBox.warning(self, "SIRET invalide",
                    "Le numéro SIRET doit contenir exactement 14 chiffres.")
                return
            # Validation TVA si renseigné
            tva = self.ent_num_tva.text().strip().upper()
            if tva:
                tva_chiffres = tva.lstrip("FR")
                if not tva_chiffres.isdigit() or len(tva_chiffres) != 11:
                    QMessageBox.warning(self, "N° TVA invalide",
                        "Le numéro de TVA doit être au format FR + 11 chiffres.")
                    return
            # Téléphone : 9 chiffres si renseigné
            tel = self.ent_tel.text().strip()
            if tel and len(tel) != 9:
                QMessageBox.warning(self, "Téléphone invalide",
                    "Le numéro de téléphone doit contenir 9 chiffres "
                    "(après l'indicatif +33).")
                return

        if self._current == 2:
            if not self.chk_maraichage.isChecked() and \
               not self.chk_grandes_cult.isChecked():
                QMessageBox.warning(self, "Champ manquant",
                    "Sélectionnez au moins un type de production.")
                return
            if self.chk_ruches.isChecked():
                napi = self.ent_napi.text().strip()
                if not napi:
                    QMessageBox.warning(self, "Champ manquant",
                        "Le N° NAPI est obligatoire si vous avez des ruches.")
                    return
                if len(napi) < 4:
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

        # Type exploitation
        types = []
        if self.chk_maraichage.isChecked():
            types.append("maraichage")
        if self.chk_grandes_cult.isChecked():
            types.append("grandes_cultures")
        type_exploit = ",".join(types) if types else None

        has_ruches = 1 if self.chk_ruches.isChecked() else 0

        # Construction du numéro de téléphone complet
        tel_brut = self.ent_tel.text().strip()
        tel_complet = f"+33{tel_brut}" if tel_brut else None

        # Normalisation TVA
        tva = self.ent_num_tva.text().strip().upper() or None
        if tva and not tva.startswith("FR"):
            tva = f"FR{tva}"

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
                self.ent_siret.text().strip() or None,
                self.ent_adresse.text().strip() or None,
                self.ent_cp.text().strip() or None,
                self.ent_ville.text().strip() or None,
                tel_complet,
                self.ent_email.text().strip() or None,
                tva,
                self.ent_num_bio.text().strip() or None,
                self.ent_org_certif.text().strip() or None,
                type_exploit,
                has_ruches,
                self.ent_napi.text().strip().upper() or None,
            ))

            pw_hash = bcrypt.hashpw(
                mdp.encode(), bcrypt.gensalt()).decode()
            cur.execute("""
                INSERT INTO users
                (nom, prenom, username, password_hash, role, actif)
                VALUES (?, ?, ?, ?, 'admin', 1)
            """, (nom, prenom, username, pw_hash))

            conn.commit()
            cur.close()
            debug.debug(f"[wizard] Setup terminé — "
                        f"type={type_exploit} ruches={has_ruches}")
            return True

        except Exception as e:
            debug.debug(f"[wizard] Erreur : {e}")
            traceback.print_exc()
            self.lbl_err.setText(f"Erreur : {e}")
            return False