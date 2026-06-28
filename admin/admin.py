# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import (get_connection, get_permissions, set_permissions,
                init_permissions_defaut, MODULES, DEFAUTS_PERMISSIONS)
from views.login import hash_password, CERTIPHYTO_TYPES
import utils.debug as debug
import traceback

# Labels lisibles pour les modules
MODULE_LABELS = {
    "fertilisants": "Fertilisants",
    "ppp_catalogue": "PPP — Catalogue",
    "ppp_carnet":    "PPP — Carnet",
    "entreprise":    "Entreprise",
    "parcelles":     "Parcelles",
    "irrigation":    "Irrigation",
    "ruches":        "Ruches",
    "admin":         "Administration",
}


class AdminPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user

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
        self.table_users.cellDoubleClicked.connect(
            lambda row, col: self._dialog_user(self.table_users.item(row, 0).data(Qt.UserRole))
        )
        hh = self.table_users.horizontalHeader()
        for i in range(8):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
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
                cur.execute(
                    "SELECT * FROM users WHERE actif=1 ORDER BY nom, prenom")
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
            debug.debug(f"[admin] Erreur chargement users : {e}")
            traceback.print_exc()

    def _menu_user(self, pos):
        row = self.table_users.rowAt(pos.y())
        if row < 0:
            return
        item = self.table_users.item(row, 0)
        user_id = item.data(Qt.UserRole)

        if user_id == self.current_user.get("id"):
            return

        etat_item = self.table_users.item(row, 7)
        est_actif = etat_item and etat_item.text() == "Actif"

        menu = QMenu(self)
        menu.addAction("Modifier",
            lambda: self._dialog_user(user_id))
        menu.addAction("Permissions",
            lambda: self._dialog_permissions(user_id))
        menu.addAction("Changer le mot de passe",
            lambda: self._dialog_mdp(user_id))
        menu.addSeparator()
        if est_actif:
            menu.addAction("Désactiver",
                lambda: self._set_actif(user_id, False))
        else:
            menu.addAction("Réactiver",
                lambda: self._set_actif(user_id, True))
        menu.addSeparator()
        act_sup = menu.addAction("🗑 Supprimer définitivement")
        act_sup.triggered.connect(lambda: self._supprimer_user(user_id))
        menu.exec(self.table_users.viewport().mapToGlobal(pos))

    def _set_actif(self, user_id: int, actif: bool):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE users SET actif=? WHERE id=?",
                        (1 if actif else 0, user_id))
            conn.commit()
            cur.close()
            self._charger_users()
        except Exception:
            traceback.print_exc()

    def _supprimer_user(self, user_id: int):
        rep = QMessageBox.warning(self, "Supprimer",
            "Supprimer définitivement cet utilisateur ?\n"
            "Toutes ses données associées seront perdues.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM users WHERE id=?", (user_id,))
                conn.commit()
                cur.close()
                self._charger_users()
            except Exception:
                traceback.print_exc()

    def _dialog_user(self, user_id=None):
        dlg = DialogUser(user_id=user_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            # Initialiser les permissions par défaut pour les nouveaux users
            if not user_id and dlg.new_user_id:
                role = dlg.role_selectionne
                init_permissions_defaut(dlg.new_user_id, role)
                debug.debug(f"[admin] Permissions défaut créées pour user {dlg.new_user_id} rôle={role}")
            self._charger_users()

    def _dialog_permissions(self, user_id: int):
        # Récupérer le nom de l'utilisateur
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT nom, prenom, role FROM users WHERE id=?",
                        (user_id,))
            row = cur.fetchone()
            cur.close()
            nom_user = f"{row[1]} {row[0]}" if row else f"User #{user_id}"
            role_user = row[2] if row else "user"
        except Exception:
            nom_user = f"User #{user_id}"
            role_user = "user"

        dlg = DialogPermissions(
            user_id=user_id,
            nom_user=nom_user,
            role_user=role_user,
            parent=self)
        dlg.exec()

    def _dialog_mdp(self, user_id: int):
        dlg = DialogMdp(user_id=user_id, parent=self)
        dlg.exec()


# ──────────────────────────────────────────────
# Dialog Permissions (matrice module × action)
# ──────────────────────────────────────────────
class DialogPermissions(QDialog):
    def __init__(self, user_id: int, nom_user: str,
                 role_user: str, parent=None):
        super().__init__(parent)
        self.user_id  = user_id
        self.role_user = role_user
        self.setWindowTitle(f"Permissions — {nom_user}")
        self.setMinimumWidth(520)
        self._checkboxes = {}  # {(module, action): QCheckBox}
        self._build_ui()
        self._charger()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Info rôle
        if self.role_user == "admin":
            lbl_info = QLabel(
                "ℹ Les administrateurs ont tous les droits — "
                "les permissions ne s'appliquent pas.")
            lbl_info.setStyleSheet(
                "background:#FEF3C7; border:1px solid #F59E0B; "
                "border-radius:4px; padding:6px; color:#92400E;")
            lbl_info.setWordWrap(True)
            layout.addWidget(lbl_info)

        # Boutons rapides
        quick = QHBoxLayout()
        btn_tout_lire = QPushButton("Lecture seule (tout)")
        btn_tout_lire.clicked.connect(lambda: self._appliquer_preset("lecture"))
        btn_tout_ecrire = QPushButton("Lecture + Écriture")
        btn_tout_ecrire.clicked.connect(lambda: self._appliquer_preset("ecriture"))
        btn_defaut = QPushButton("Réinitialiser défauts")
        btn_defaut.clicked.connect(self._appliquer_defauts)
        quick.addWidget(btn_tout_lire)
        quick.addWidget(btn_tout_ecrire)
        quick.addWidget(btn_defaut)
        layout.addLayout(quick)

        # Table matrice
        self.table = QTableWidget(len(MODULES), 3)
        self.table.setHorizontalHeaderLabels(["Lecture", "Écriture", "Suppression"])
        self.table.setVerticalHeaderLabels(
            [MODULE_LABELS.get(m, m) for m in MODULES])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for row, module in enumerate(MODULES):
            for col, action in enumerate(["lecture", "ecriture", "suppression"]):
                chk = QCheckBox()
                chk.setEnabled(self.role_user != "admin")
                # Centrer la checkbox
                cell = QWidget()
                cell_lay = QHBoxLayout(cell)
                cell_lay.addWidget(chk)
                cell_lay.setAlignment(Qt.AlignCenter)
                cell_lay.setContentsMargins(0, 0, 0, 0)
                self.table.setCellWidget(row, col, cell)
                self._checkboxes[(module, action)] = chk

                # Désactiver suppression si écriture décochée
                if action == "suppression":
                    ecriture_chk = self._checkboxes.get((module, "ecriture"))
                    if ecriture_chk:
                        ecriture_chk.toggled.connect(
                            lambda checked, c=chk: c.setEnabled(
                                checked and self.role_user != "admin"))

        layout.addWidget(self.table)

        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _charger(self):
        perms = get_permissions(self.user_id)
        debug.debug(f"[admin] Permissions chargées pour user {self.user_id}: {perms}")

        for row, module in enumerate(MODULES):
            module_perms = perms.get(module, {})
            for col, action in enumerate(["lecture", "ecriture", "suppression"]):
                chk = self._checkboxes.get((module, action))
                if chk:
                    # Si pas de permissions définies, appliquer défauts
                    if not module_perms:
                        defauts = DEFAUTS_PERMISSIONS.get(
                            self.role_user, DEFAUTS_PERMISSIONS["user"])
                        val = defauts.get(module, {}).get(action, False)
                    else:
                        val = module_perms.get(action, action == "lecture")
                    chk.setChecked(bool(val))

    def _appliquer_preset(self, niveau: str):
        for module in MODULES:
            for col, action in enumerate(["lecture", "ecriture", "suppression"]):
                chk = self._checkboxes.get((module, action))
                if chk and chk.isEnabled():
                    if niveau == "lecture":
                        chk.setChecked(action == "lecture")
                    elif niveau == "ecriture":
                        chk.setChecked(action in ("lecture", "ecriture"))

    def _appliquer_defauts(self):
        defauts = DEFAUTS_PERMISSIONS.get(
            self.role_user, DEFAUTS_PERMISSIONS["user"])
        for module in MODULES:
            for action in ["lecture", "ecriture", "suppression"]:
                chk = self._checkboxes.get((module, action))
                if chk and chk.isEnabled():
                    val = defauts.get(module, {}).get(action, False)
                    chk.setChecked(bool(val))

    def _valider(self):
        perms = {}
        for module in MODULES:
            perms[module] = {
                action: self._checkboxes[(module, action)].isChecked()
                for action in ["lecture", "ecriture", "suppression"]
            }
        set_permissions(self.user_id, perms)
        debug.debug(f"[admin] Permissions sauvegardées pour user {self.user_id}")
        self.accept()


# ──────────────────────────────────────────────
# Dialog création / modification utilisateur
# ──────────────────────────────────────────────
class DialogUser(QDialog):
    def __init__(self, user_id=None, parent=None):
        super().__init__(parent)
        self.user_id         = user_id
        self.new_user_id     = None   # rempli après création
        self.role_selectionne = "user"
        self.setWindowTitle(
            "Nouvel utilisateur" if not user_id else "Modifier l'utilisateur")
        self.setMinimumWidth(480)
        self._build_ui()
        if user_id:
            self._charger(user_id)

    def _build_ui(self):
        root = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(10)
        form.setContentsMargins(8, 8, 8, 8)

        self.inp_nom    = QLineEdit()
        self.inp_prenom = QLineEdit()
        self.inp_user   = QLineEdit()
        self.inp_tel    = QLineEdit()

        self.inp_cipp = QLineEdit()
        self.inp_cipp.setInputMask("AA-0000-000000")
        self.inp_cipp.setPlaceholderText("Ex: AA-0000-000000")

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

        form.addRow("Nom *",         self.inp_nom)
        form.addRow("Prénom *",      self.inp_prenom)
        form.addRow("Identifiant *", self.inp_user)

        if not self.user_id:
            lbl_mdp = QLabel(
                "L'utilisateur créera son mot de passe à sa première connexion.")
            lbl_mdp.setStyleSheet(
                "color:#16a34a; font-size:11px; font-style:italic;")
            lbl_mdp.setWordWrap(True)
            form.addRow("Mot de passe", lbl_mdp)

        form.addRow("Téléphone",     self.inp_tel)
        form.addRow("Date embauche", self.inp_embauche)

        sep = QLabel("── CertiPhyto ──")
        sep.setStyleSheet("color:gray; font-size:11px;")
        form.addRow(sep)
        form.addRow("N° CIPP",          self.inp_cipp)
        form.addRow("Type certificat",  self.combo_cipp_type)
        form.addRow("Date expiration",  self.inp_cipp_exp)
        form.addRow("Rôle",             self.combo_role)

        self.chk_apiculteur = QCheckBox(
            "Apiculteur (peut gérer et supprimer les ruches)")
        form.addRow("", self.chk_apiculteur)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:red;")
        self.lbl_err.setWordWrap(True)
        form.addRow(self.lbl_err)

        scroll.setWidget(w)
        root.addWidget(scroll, 1)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _charger(self, user_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
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
        except Exception:
            traceback.print_exc()

    def _valider(self):
        nom      = self.inp_nom.text().strip()
        prenom   = self.inp_prenom.text().strip()
        username = self.inp_user.text().strip()

        if not nom or not prenom or not username:
            self.lbl_err.setText(
                "Nom, prénom et identifiant sont obligatoires.")
            return

        cipp      = self.inp_cipp.text().strip() or None
        cipp_type = self.combo_cipp_type.currentData()
        cipp_exp  = (self.inp_cipp_exp.date().toString("yyyy-MM-dd")
                     if cipp_type else None)
        role      = self.combo_role.currentText()
        self.role_selectionne = role
        is_apic   = 1 if self.chk_apiculteur.isChecked() else 0
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
                    telephone=?, date_embauche=?, is_apiculteur=?
                    WHERE id=?
                """, (nom, prenom, cipp, cipp_type, cipp_exp,
                      role, tel, embauche, is_apic, self.user_id))
            else:
                cur.execute("""
                    INSERT INTO users
                    (nom, prenom, username, password_hash, first_login,
                     certiphyto_cipp, certiphyto_type,
                     certiphyto_date_expiration, role,
                     telephone, date_embauche, is_apiculteur)
                    VALUES (?, ?, ?, '', 1, ?, ?, ?, ?, ?, ?, ?)
                """, (nom, prenom, username,
                      cipp, cipp_type, cipp_exp,
                      role, tel, embauche, is_apic))
                self.new_user_id = cur.lastrowid
                debug.debug(f"[admin] Nouvel user créé id={self.new_user_id}")
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


# ──────────────────────────────────────────────
# Dialog changement mot de passe
# ──────────────────────────────────────────────
class DialogMdp(QDialog):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle("Changer le mot de passe")
        self.setMinimumWidth(340)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.inp_pass  = QLineEdit()
        self.inp_pass.setEchoMode(QLineEdit.Password)
        self.inp_pass2 = QLineEdit()
        self.inp_pass2.setEchoMode(QLineEdit.Password)
        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color:red;")
        form.addRow("Nouveau mot de passe *", self.inp_pass)
        form.addRow("Confirmer *",            self.inp_pass2)
        form.addRow(self.lbl_err)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _valider(self):
        pwd  = self.inp_pass.text()
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
            cur.execute(
                "UPDATE users SET password_hash=?, first_login=0 WHERE id=?",
                (hash_password(pwd), self.user_id))
            conn.commit()
            cur.close()
            QMessageBox.information(self, "OK", "Mot de passe modifié.")
            self.accept()
        except Exception:
            traceback.print_exc()