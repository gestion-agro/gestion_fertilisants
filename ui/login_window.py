# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QTabWidget, QWidget, QComboBox, QDateEdit
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from views.login import authenticate, create_user, count_users, CERTIPHYTO_TYPES


class LoginWindow(QDialog):
    """
    Fenêtre de connexion affichée au démarrage.
    - Si aucun utilisateur n'existe -> onglet Créer un compte en premier (premier lancement).
    - Après connexion réussie, self.current_user contient le dict utilisateur.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connexion")
        self.setMinimumWidth(440)
        self.setModal(True)
        self.current_user = None
        self._build_ui()

        if count_users() == 0:
            self.tabs.setCurrentIndex(1)
            QMessageBox.information(
                self, "Premier lancement",
                "Aucun utilisateur trouvé.\n"
                "Veuillez créer le premier compte administrateur."
            )
            self.combo_role.setCurrentText("admin")
            self.combo_role.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Gestion des cultures et fertilisants")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_login(),    "Connexion")
        self.tabs.addTab(self._tab_register(), "Créer un compte")
        layout.addWidget(self.tabs)

    def _tab_login(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("Nom d'utilisateur")
        form.addRow("Identifiant :", self.inp_username)

        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.inp_password.setPlaceholderText("Mot de passe")
        self.inp_password.returnPressed.connect(self._do_login)
        form.addRow("Mot de passe :", self.inp_password)

        self.lbl_login_error = QLabel("")
        self.lbl_login_error.setStyleSheet("color: red;")
        form.addRow(self.lbl_login_error)

        btn = QPushButton("Se connecter")
        btn.clicked.connect(self._do_login)
        form.addRow(btn)

        return widget

    def _tab_register(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)

        self.inp_reg_nom    = QLineEdit()
        self.inp_reg_prenom = QLineEdit()
        self.inp_reg_user   = QLineEdit()
        self.inp_reg_pass   = QLineEdit()
        self.inp_reg_pass.setEchoMode(QLineEdit.Password)
        self.inp_reg_pass2  = QLineEdit()
        self.inp_reg_pass2.setEchoMode(QLineEdit.Password)

        # CertiPhyto
        self.inp_reg_cipp = QLineEdit()
        self.inp_reg_cipp.setPlaceholderText("Ex: A-5-NNSSUHDIWA_CER… (facultatif)")

        self.combo_cipp_type = QComboBox()
        self.combo_cipp_type.addItem("— Non renseigné —", None)
        for t in CERTIPHYTO_TYPES:
            self.combo_cipp_type.addItem(t, t)

        self.inp_cipp_expiration = QDateEdit()
        self.inp_cipp_expiration.setDisplayFormat("dd/MM/yyyy")
        self.inp_cipp_expiration.setCalendarPopup(True)
        self.inp_cipp_expiration.setDate(QDate.currentDate().addYears(5))
        self.inp_cipp_expiration.setEnabled(False)

        # Activer la date seulement si un type est sélectionné
        self.combo_cipp_type.currentIndexChanged.connect(
            lambda i: self.inp_cipp_expiration.setEnabled(i > 0)
        )

        self.combo_role = QComboBox()
        self.combo_role.addItems(["user", "admin"])

        form.addRow("Nom :",                self.inp_reg_nom)
        form.addRow("Prénom :",             self.inp_reg_prenom)
        form.addRow("Identifiant :",        self.inp_reg_user)
        form.addRow("Mot de passe :",       self.inp_reg_pass)
        form.addRow("Confirmer mdp :",      self.inp_reg_pass2)

        lbl_sep = QLabel("── CertiPhyto (facultatif) ──")
        lbl_sep.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow(lbl_sep)

        form.addRow("N° CIPP :",            self.inp_reg_cipp)
        form.addRow("Type de certificat :", self.combo_cipp_type)
        form.addRow("Date d'expiration :",  self.inp_cipp_expiration)
        form.addRow("Rôle :",               self.combo_role)

        self.lbl_reg_error = QLabel("")
        self.lbl_reg_error.setStyleSheet("color: red;")
        self.lbl_reg_error.setWordWrap(True)
        form.addRow(self.lbl_reg_error)

        btn = QPushButton("Créer le compte")
        btn.clicked.connect(self._do_register)
        form.addRow(btn)

        return widget

    def _do_login(self):
        username = self.inp_username.text().strip()
        password = self.inp_password.text()

        if not username or not password:
            self.lbl_login_error.setText("Veuillez remplir tous les champs.")
            return

        user = authenticate(username, password)
        if user:
            self.current_user = user
            self.accept()
        else:
            self.lbl_login_error.setText("Identifiant ou mot de passe incorrect.")
            self.inp_password.clear()

    def _do_register(self):
        import traceback
        try:
            nom      = self.inp_reg_nom.text().strip()
            prenom   = self.inp_reg_prenom.text().strip()
            username = self.inp_reg_user.text().strip()
            password = self.inp_reg_pass.text()
            password2 = self.inp_reg_pass2.text()
            cipp      = self.inp_reg_cipp.text().strip() or None
            cipp_type = self.combo_cipp_type.currentData()
            cipp_exp  = (self.inp_cipp_expiration.date().toPython()
                        if cipp_type else None)
            role      = self.combo_role.currentText()

            if not all([nom, prenom, username, password]):
                self.lbl_reg_error.setText(
                    "Nom, prénom, identifiant et mot de passe sont obligatoires.")
                return

            if password != password2:
                self.lbl_reg_error.setText("Les mots de passe ne correspondent pas.")
                return

            if len(password) < 6:
                self.lbl_reg_error.setText(
                    "Le mot de passe doit faire au moins 6 caractères.")
                return

            ok, msg = create_user(nom, prenom, username, password,
                                cipp, cipp_type, cipp_exp, role)
            if ok:
                QMessageBox.information(
                    self, "Compte créé",
                    f"Compte '{username}' créé avec succès.\n"
                    + (f"Certificat : {cipp_type}" if cipp_type else
                    "Aucun certificat renseigné — accès PPP limité à la lecture.")
                )
                self.current_user = authenticate(username, password)
                self.accept()
            else:
                self.lbl_reg_error.setText(msg)
        except Exception as e:
            traceback.print_exc()
            self.lbl_reg_error.setText(f"Erreur lors de la création du compte : {e}")