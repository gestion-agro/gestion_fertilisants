# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection
from views.login import hash_password, CERTIPHYTO_TYPES
import traceback


class AdminPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user

        # Vérification — seuls les admins accèdent à cette page
        if self.current_user.get("role") != "admin":
            layout = QVBoxLayout(self)
            lbl = QLabel("Accès réservé aux administrateurs.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 16px; color: red;")
            layout.addWidget(lbl)
            return

        self._build_ui()
        self._charger_users()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        titre = QLabel("Administration")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        tabs = QTabWidget()

        # ── Onglet Utilisateurs ───────────────
        tab_users = QWidget()
        lay_users = QVBoxLayout(tab_users)
        lay_users.setContentsMargins(8, 8, 8, 8)
        lay_users.setSpacing(8)

        top_u = QHBoxLayout()
        self.chk_inactifs = QCheckBox("Afficher les utilisateurs désactivés")
        self.chk_inactifs.stateChanged.connect(self._charger_users)
        top_u.addWidget(self.chk_inactifs)
        top_u.addStretch()
        btn_add_user = QPushButton("+ Nouvel utilisateur")
        btn_add_user.clicked.connect(lambda: self._dialog_user())
        top_u.addWidget(btn_add_user)
        lay_users.addLayout(top_u)

        self.table_users = QTableWidget(0, 8)
        self.table_users.setHorizontalHeaderLabels(
            ["Nom", "Prénom", "Identifiant", "Rôle",
             "CertiPhyto", "Expiration", "Apiculteur", "État"])
        self.table_users.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_users.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_users.setAlternatingRowColors(True)
        self.table_users.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_users.customContextMenuRequested.connect(self._menu_user)
        hh = self.table_users.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        lay_users.addWidget(self.table_users)
        tabs.addTab(tab_users, "Utilisateurs")

        root.addWidget(tabs, 1)

    def _charger_users(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.chk_inactifs.isChecked():
                cur.execute("SELECT * FROM users ORDER BY nom, prenom")
            else:
                cur.execute("SELECT * FROM users WHERE actif = 1 ORDER BY nom, prenom")
            rows = cur.fetchall()
            cur.close()

            self.table_users.setRowCount(0)
            for row in rows:
                u = dict(row)
                r = self.table_users.rowCount()
                self.table_users.insertRow(r)
                self.table_users.setItem(r, 0, QTableWidgetItem(u.get("nom", "")))
                self.table_users.setItem(r, 1, QTableWidgetItem(u.get("prenom", "")))
                self.table_users.setItem(r, 2, QTableWidgetItem(u.get("username", "")))
                role = "Admin" if u.get("role") == "admin" else "Utilisateur"
                self.table_users.setItem(r, 3, QTableWidgetItem(role))
                cipp = u.get("certiphyto_type") or "—"
                self.table_users.setItem(r, 4, QTableWidgetItem(cipp))
                exp = u.get("certiphyto_date_expiration") or "—"
                self.table_users.setItem(r, 5, QTableWidgetItem(exp))
                apic = "✓" if u.get("is_apiculteur") else "—"
                self.table_users.setItem(r, 6, QTableWidgetItem(apic))
                etat = "Actif" if u.get("actif", 1) else "Désactivé"
                self.table_users.setItem(r, 7, QTableWidgetItem(etat))
                self.table_users.item(r, 0).setData(Qt.UserRole, u["id"])

                if not u.get("actif", 1):
                    for col in range(8):
                        item = self.table_users.item(r, col)
                        if item:
                            item.setForeground(QColor("gray"))
        except Exception as e:
            traceback.print_exc()

    def _menu_user(self, pos):
        row = self.table_users.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_users.item(row, 0)
        user_id = item.data(Qt.UserRole)

        # Ne pas permettre de désactiver son propre compte
        if user_id == self.current_user.get("id"):
            return

        etat_item = self.table_users.item(row, 6)
        menu = QMenu(self)
        menu.addAction("Modifier", lambda: self._dialog_user(user_id))
        menu.addAction("Changer le mot de passe",
                       lambda: self._dialog_mdp(user_id))
        if etat_item and etat_item.text() == "Actif":
            menu.addAction("Désactiver", lambda: self._set_actif(user_id, False))
        else:
            menu.addAction("Réactiver", lambda: self._set_actif(user_id, True))
        menu.exec(self.table_users.viewport().mapToGlobal(pos))

    def _set_actif(self, user_id: int, actif: bool):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET actif = ? WHERE id = ?",
                        (1 if actif else 0, user_id))
            conn.commit()
            cur.close()
            self._charger_users()
        except Exception as e:
            traceback.print_exc()

    def _dialog_user(self, user_id=None):
        dlg = DialogUser(user_id=user_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger_users()

    def _dialog_mdp(self, user_id: int):
        dlg = DialogMdp(user_id=user_id, parent=self)
        dlg.exec()


# ──────────────────────────────────────────────
# Dialog création / modification utilisateur
# ──────────────────────────────────────────────
class DialogUser(QDialog):
    def __init__(self, user_id=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Utilisateur" if not user_id else "Modifier l'utilisateur")
        self.setMinimumWidth(460)
        self._build_ui()
        if user_id:
            self._charger(user_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_nom     = QLineEdit()
        self.inp_prenom  = QLineEdit()
        self.inp_user    = QLineEdit()
        self.inp_pass    = QLineEdit()
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass.setPlaceholderText("Laisser vide = inchangé" if self.user_id else "")
        self.inp_pass2   = QLineEdit()
        self.inp_pass2.setEchoMode(QLineEdit.Password)
        self.inp_tel     = QLineEdit()
        self.inp_cipp    = QLineEdit()
        self.combo_cipp_type = QComboBox()
        self.combo_cipp_type.addItem("— Non renseigné —", None)
        for t in CERTIPHYTO_TYPES:
            self.combo_cipp_type.addItem(t, t)
        self.inp_cipp_exp = QDateEdit()
        self.inp_cipp_exp.setDisplayFormat("dd/MM/yyyy")
        self.inp_cipp_exp.setCalendarPopup(True)
        self.inp_cipp_exp.setEnabled(False)
        self.combo_cipp_type.currentIndexChanged.connect(
            lambda i: self.inp_cipp_exp.setEnabled(i > 0))
        self.combo_role = QComboBox()
        self.combo_role.addItems(["user", "admin"])
        self.inp_embauche = QDateEdit()
        self.inp_embauche.setDisplayFormat("dd/MM/yyyy")
        self.inp_embauche.setCalendarPopup(True)
        self.inp_embauche.setSpecialValueText("—")
        self.inp_embauche.setDate(QDate(2000, 1, 1))

        form.addRow("Nom *",             self.inp_nom)
        form.addRow("Prénom *",          self.inp_prenom)
        form.addRow("Identifiant *",     self.inp_user)
        if not self.user_id:
            form.addRow("Mot de passe *",    self.inp_pass)
            form.addRow("Confirmer mdp *",   self.inp_pass2)
        form.addRow("Téléphone",         self.inp_tel)
        form.addRow("Date embauche",     self.inp_embauche)

        sep = QLabel("── CertiPhyto ──")
        sep.setStyleSheet("color: gray; font-size: 11px;")
        form.addRow(sep)
        form.addRow("N° CIPP",          self.inp_cipp)
        form.addRow("Type certificat",   self.combo_cipp_type)
        form.addRow("Date expiration",   self.inp_cipp_exp)
        form.addRow("Rôle",              self.combo_role)

        self.chk_apiculteur = QCheckBox("Apiculteur (peut gérer et supprimer les ruches)")
        form.addRow("", self.chk_apiculteur)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: red;")
        self.lbl_err.setWordWrap(True)
        form.addRow(self.lbl_err)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _charger(self, user_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            u = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(u.get("nom", ""))
            self.inp_prenom.setText(u.get("prenom", ""))
            self.inp_user.setText(u.get("username", ""))
            self.inp_user.setEnabled(False)
            self.inp_tel.setText(u.get("telephone") or "")
            self.inp_cipp.setText(u.get("certiphyto_cipp") or "")
            idx = self.combo_cipp_type.findData(u.get("certiphyto_type"))
            self.combo_cipp_type.setCurrentIndex(max(0, idx))
            if u.get("certiphyto_date_expiration"):
                self.inp_cipp_exp.setDate(
                    QDate.fromString(u["certiphyto_date_expiration"], "yyyy-MM-dd"))
            idx_role = self.combo_role.findText(u.get("role", "user"))
            self.combo_role.setCurrentIndex(max(0, idx_role))
            self.chk_apiculteur.setChecked(bool(u.get("is_apiculteur")))
            if u.get("date_embauche"):
                self.inp_embauche.setDate(
                    QDate.fromString(u["date_embauche"], "yyyy-MM-dd"))
        except Exception as e:
            traceback.print_exc()

    def _valider(self):
        nom     = self.inp_nom.text().strip()
        prenom  = self.inp_prenom.text().strip()
        username = self.inp_user.text().strip()

        if not nom or not prenom or not username:
            self.lbl_err.setText("Nom, prénom et identifiant sont obligatoires.")
            return

        if not self.user_id:
            pwd = self.inp_pass.text()
            pwd2 = self.inp_pass2.text()
            if not pwd:
                self.lbl_err.setText("Le mot de passe est obligatoire.")
                return
            if pwd != pwd2:
                self.lbl_err.setText("Les mots de passe ne correspondent pas.")
                return
            if len(pwd) < 6:
                self.lbl_err.setText("Le mot de passe doit faire au moins 6 caractères.")
                return

        cipp      = self.inp_cipp.text().strip() or None
        cipp_type = self.combo_cipp_type.currentData()
        cipp_exp  = (self.inp_cipp_exp.date().toString("yyyy-MM-dd")
                     if cipp_type else None)
        role      = self.combo_role.currentText()
        is_apiculteur = 1 if self.chk_apiculteur.isChecked() else 0
        tel       = self.inp_tel.text().strip() or None
        embauche  = self.inp_embauche.date().toString("yyyy-MM-dd")

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.user_id:
                cur.execute("""
                    UPDATE users SET nom=?, prenom=?,
                    certiphyto_cipp=?, certiphyto_type=?,
                    certiphyto_date_expiration=?, role=?,
                    telephone=?, date_embauche=?, is_apiculteur=? WHERE id=?
                """, (nom, prenom, cipp, cipp_type, cipp_exp,
                      role, tel, embauche, is_apiculteur, self.user_id))
            else:
                cur.execute("""
                    INSERT INTO users
                    (nom, prenom, username, password_hash,
                     certiphyto_cipp, certiphyto_type,
                     certiphyto_date_expiration, role,
                     telephone, date_embauche, is_apiculteur)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (nom, prenom, username,
                      hash_password(self.inp_pass.text()),
                      cipp, cipp_type, cipp_exp, role, tel, embauche, is_apiculteur))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            msg = str(e)
            if "UNIQUE" in msg:
                self.lbl_err.setText("Cet identifiant est déjà utilisé.")
            else:
                self.lbl_err.setText(f"Erreur : {e}")
            traceback.print_exc()


class DialogMdp(QDialog):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Changer le mot de passe")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.inp_pass  = QLineEdit(); self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass2 = QLineEdit(); self.inp_pass2.setEchoMode(QLineEdit.Password)
        self.lbl_err   = QLabel(""); self.lbl_err.setStyleSheet("color: red;")
        form.addRow("Nouveau mot de passe *", self.inp_pass)
        form.addRow("Confirmer *",           self.inp_pass2)
        form.addRow(self.lbl_err)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _valider(self):
        pwd = self.inp_pass.text()
        pwd2 = self.inp_pass2.text()
        if pwd != pwd2:
            self.lbl_err.setText("Les mots de passe ne correspondent pas.")
            return
        if len(pwd) < 6:
            self.lbl_err.setText("Minimum 6 caractères.")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash = ? WHERE id = ?",
                        (hash_password(pwd), self.user_id))
            conn.commit()
            cur.close()
            QMessageBox.information(self, "OK", "Mot de passe modifié.")
            self.accept()
        except Exception as e:
            traceback.print_exc()