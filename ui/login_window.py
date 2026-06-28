# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from views.login import authenticate
import utils.debug as debug
import traceback


class LoginWindow(QDialog):
    """
    Fenêtre de connexion.
    - Connexion normale avec identifiant + mot de passe
    - Si first_login=1 → dialog création mot de passe
    - Si actif=0 → message compte désactivé
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connexion")
        self.setMinimumWidth(400)
        self.setModal(True)
        self.current_user = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("🌱 Gestion des cultures et fertilisants")
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)

        self.inp_username = QLineEdit()
        self.inp_username.setPlaceholderText("Nom d'utilisateur")
        self.inp_username.setFixedHeight(34)
        form.addRow("Identifiant :", self.inp_username)
        lbl_first = QLabel('<a href="#" style="color:#6b7280; font-size:11px;">Première connexion ?</a>')
        lbl_first.setTextFormat(Qt.RichText)
        lbl_first.setAlignment(Qt.AlignRight)
        lbl_first.linkActivated.connect(self._demander_premiere_connexion)
        form.addRow("", lbl_first)

        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.Password)
        self.inp_password.setPlaceholderText("Mot de passe")
        self.inp_password.setFixedHeight(34)
        self.inp_password.returnPressed.connect(self._do_login)
        form.addRow("Mot de passe :", self.inp_password)

        layout.addLayout(form)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #DC2626; font-size: 12px;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        btn = QPushButton("Se connecter")
        btn.setFixedHeight(38)
        btn.setStyleSheet("""
            QPushButton {
                background: #16a34a; color: white;
                border-radius: 4px; font-weight: bold; font-size: 13px;
            }
            QPushButton:hover { background: #15803d; }
        """)
        btn.clicked.connect(self._do_login)
        layout.addWidget(btn)

    def _do_login(self):
        username = self.inp_username.text().strip()
        password = self.inp_password.text()

        if not username:
            self.lbl_error.setText("Veuillez saisir votre identifiant.")
            return

        # Vérifier l'état du compte avant authenticate
        try:
            from db import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT first_login, actif FROM users WHERE username = ?",
                (username,))
            row = cur.fetchone()
            cur.close()

            if row is None:
                self.lbl_error.setText("Identifiant ou mot de passe incorrect.")
                return

            if not row[1]:  # actif = 0
                self.lbl_error.setText(
                    "Ce compte est désactivé.\n"
                    "Contactez votre administrateur.")
                return

            if row[0] == 1:  # first_login
                if not username:
                    self.lbl_error.setText("Veuillez saisir votre identifiant.")
                    return
                self._dialog_premiere_connexion(username)
                return

        except Exception as e:
            debug.debug(f"[login] Erreur vérif compte : {e}")

        if not password:
            self.lbl_error.setText("Veuillez saisir votre mot de passe.")
            return

        user = authenticate(username, password)
        if user:
            self.current_user = user
            self.accept()
        else:
            self.lbl_error.setText("Identifiant ou mot de passe incorrect.")
            self.inp_password.clear()

    def _dialog_premiere_connexion(self, username: str):
        dlg = QDialog(self)
        dlg.setWindowTitle("Première connexion")
        dlg.setMinimumWidth(380)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lbl = QLabel(
            f"Bienvenue !\n\n"
            f"Créez votre mot de passe pour le compte « {username} ».")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size: 13px;")
        lay.addWidget(lbl)

        form = QFormLayout()
        form.setSpacing(10)
        inp_p1 = QLineEdit()
        inp_p1.setEchoMode(QLineEdit.Password)
        inp_p1.setPlaceholderText("6 caractères minimum")
        inp_p1.setFixedHeight(32)
        inp_p2 = QLineEdit()
        inp_p2.setEchoMode(QLineEdit.Password)
        inp_p2.setPlaceholderText("Confirmer")
        inp_p2.setFixedHeight(32)
        form.addRow("Nouveau mot de passe *", inp_p1)
        form.addRow("Confirmer *", inp_p2)
        lbl_err = QLabel("")
        lbl_err.setStyleSheet("color: #DC2626; font-size: 11px;")
        form.addRow(lbl_err)
        lay.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Créer mon mot de passe")
        btns.button(QDialogButtonBox.Ok).setStyleSheet("""
            QPushButton { background:#16a34a; color:white;
                border-radius:4px; padding:4px 12px; font-weight:bold; }
            QPushButton:hover { background:#15803d; }
        """)
        btns.rejected.connect(dlg.reject)
        lay.addWidget(btns)

        def _valider():
            p1 = inp_p1.text()
            p2 = inp_p2.text()
            if len(p1) < 6:
                lbl_err.setText("6 caractères minimum.")
                return
            if p1 != p2:
                lbl_err.setText("Les mots de passe ne correspondent pas.")
                return
            try:
                from db import get_connection
                from views.login import hash_password
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET password_hash=?, first_login=0 "
                    "WHERE username=?",
                    (hash_password(p1), username))
                conn.commit()
                cur.close()
                debug.debug(f"[login] Mot de passe créé pour {username}")
                dlg.accept()
                user = authenticate(username, p1)
                if user:
                    self.current_user = user
                    self.accept()
            except Exception as e:
                debug.debug(f"[login] Erreur création mdp : {e}")
                lbl_err.setText(f"Erreur : {e}")

        btns.accepted.connect(_valider)
        inp_p2.returnPressed.connect(_valider)
        dlg.exec()

    def _demander_premiere_connexion(self):
        username = self.inp_username.text().strip()
        if not username:
            self.lbl_error.setText("Saisissez d'abord votre identifiant.")
            return
        try:
            from db import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "SELECT first_login, actif FROM users WHERE username = ?",
                (username,))
            row = cur.fetchone()
            cur.close()
            if not row:
                self.lbl_error.setText("Identifiant introuvable.")
                return
            if not row[1]:
                self.lbl_error.setText("Ce compte est désactivé.")
                return
            if row[0] != 1:
                self.lbl_error.setText(
                    "Ce compte a déjà un mot de passe défini.")
                return
            self._dialog_premiere_connexion(username)
        except Exception as e:
            self.lbl_error.setText(f"Erreur : {e}")