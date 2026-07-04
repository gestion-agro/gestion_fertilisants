# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import json, os
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, DB_FILE, get_parametres_app, set_parametres_app
import utils.debug as debug
import traceback

# Fichier de config local (hors BDD)
CONFIG_FILE = os.path.join(os.path.dirname(DB_FILE), "config.json")


def lire_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ecrire_config(data: dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class ParametresPage(QWidget):
    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._build_ui()
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        titre = QLabel("Paramètres")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        root.addWidget(titre)

        tabs = QTabWidget()

        # ── Onglet Mon compte ─────────────────
        tab_compte = QWidget()
        lay = QFormLayout(tab_compte)
        lay.setSpacing(12)
        lay.setContentsMargins(16, 16, 16, 16)

        self.lbl_nom_complet = QLabel("—")
        self.lbl_username    = QLabel("—")
        self.lbl_role        = QLabel("—")
        self.lbl_cipp        = QLabel("—")
        self.lbl_cipp_exp    = QLabel("—")

        for lbl in (self.lbl_nom_complet, self.lbl_username, self.lbl_role,
                    self.lbl_cipp, self.lbl_cipp_exp):
            lbl.setStyleSheet("font-size: 13px;")

        lay.addRow("Nom complet :",     self.lbl_nom_complet)
        lay.addRow("Identifiant :",     self.lbl_username)
        lay.addRow("Rôle :",            self.lbl_role)
        lay.addRow("CertiPhyto :",      self.lbl_cipp)
        lay.addRow("Expiration CIPP :", self.lbl_cipp_exp)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        lay.addRow(sep)

        btn_mdp = QPushButton("Changer mon mot de passe")
        btn_mdp.clicked.connect(self._changer_mdp)
        lay.addRow(btn_mdp)

        tabs.addTab(tab_compte, "Mon compte")

        # ── Onglet Connexion ──────────────────
        tab_connexion = QWidget()
        lay2 = QVBoxLayout(tab_connexion)
        lay2.setContentsMargins(16, 16, 16, 16)
        lay2.setSpacing(12)

        # Connexion automatique
        group_auto = QGroupBox("Connexion automatique")
        g_lay = QFormLayout(group_auto)
        g_lay.setSpacing(10)

        self.chk_auto = QCheckBox("Activer la connexion automatique pour ce compte")
        self.chk_auto.stateChanged.connect(self._on_auto_changed)
        g_lay.addRow(self.chk_auto)

        info = QLabel(
            "Si activé, l'application se connectera automatiquement "
            "à votre compte au démarrage sans demander de mot de passe.")
        info.setWordWrap(True)
        info.setStyleSheet("color: palette(mid); font-size: 12px;")
        g_lay.addRow(info)

        lay2.addWidget(group_auto)

        # Admin : choisir le user par défaut
        if self.current_user.get("role") == "admin":
            group_default = QGroupBox("Utilisateur par défaut (Admin)")
            gd_lay = QFormLayout(group_default)
            gd_lay.setSpacing(10)

            lbl_info_admin = QLabel(
                "En mode connexion automatique, quel utilisateur "
                "est connecté par défaut au démarrage ?")
            lbl_info_admin.setWordWrap(True)
            lbl_info_admin.setStyleSheet("color: palette(mid); font-size: 12px;")
            gd_lay.addRow(lbl_info_admin)

            self.combo_default_user = QComboBox()
            self.combo_default_user.addItem("— Aucun (demander à la connexion) —", None)
            gd_lay.addRow("Utilisateur par défaut :", self.combo_default_user)

            btn_save_default = QPushButton("Enregistrer")
            btn_save_default.clicked.connect(self._sauver_default_user)
            gd_lay.addRow(btn_save_default)

            lay2.addWidget(group_default)

        lay2.addStretch()
        tabs.addTab(tab_connexion, "Connexion")

        # ── Onglet Application (admin uniquement) ──
        if self.current_user.get("role") == "admin":
            tab_app = self._build_tab_application()
            tabs.addTab(tab_app, "Application")

        root.addWidget(tabs, 1)

    def _build_tab_application(self) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(16)

        # ── Réglages planches/passe-pied/tolérance ──
        group_culture = QGroupBox("Valeurs par défaut — Cultures")
        gc_lay = QFormLayout(group_culture)
        gc_lay.setSpacing(10)

        self.inp_largeur_planche = QDoubleSpinBox()
        self.inp_largeur_planche.setRange(0.10, 10)
        self.inp_largeur_planche.setDecimals(2)
        self.inp_largeur_planche.setSuffix(" m")
        gc_lay.addRow("Largeur de planche par défaut", self.inp_largeur_planche)

        self.inp_passe_pied = QDoubleSpinBox()
        self.inp_passe_pied.setRange(0, 5)
        self.inp_passe_pied.setDecimals(2)
        self.inp_passe_pied.setSuffix(" m")
        gc_lay.addRow("Passe-pied par défaut", self.inp_passe_pied)

        self.inp_tolerance = QDoubleSpinBox()
        self.inp_tolerance.setRange(0, 50)
        self.inp_tolerance.setDecimals(1)
        self.inp_tolerance.setSuffix(" %")
        gc_lay.addRow("Tolérance calcul NPK (mode auto)", self.inp_tolerance)

        info_tol = QLabel(
            "Marge acceptée entre les besoins NPK demandés et la dose "
            "calculée automatiquement. Une valeur trop basse peut rendre "
            "le calcul automatique impossible avec un stock limité.")
        info_tol.setWordWrap(True)
        info_tol.setStyleSheet("color: palette(mid); font-size: 11px;")
        gc_lay.addRow(info_tol)

        lay.addWidget(group_culture)

        # ── Export PDF contrôleur bio ──
        group_export = QGroupBox("Export PDF carnet — Contrôleur bio")
        ge_lay = QVBoxLayout(group_export)
        ge_lay.setSpacing(8)

        info_export = QLabel(
            "Colonnes incluses dans l'export PDF du carnet de traitements "
            "(Date, Parcelle, Culture, Produit, Dose, Opérateur et Signature "
            "sont toujours inclus).")
        info_export.setWordWrap(True)
        info_export.setStyleSheet("color: palette(mid); font-size: 11px;")
        ge_lay.addWidget(info_export)

        self.chk_export_amm = QCheckBox("N° AMM du produit")
        self.chk_export_dar = QCheckBox("DAR (délai avant récolte)")
        self.chk_export_bio_agr = QCheckBox("Bio-agresseur ciblé")
        self.chk_export_meteo = QCheckBox("Conditions météo (T°, vent, nébulosité)")
        self.chk_export_epi = QCheckBox("EPI utilisés")

        for chk in (self.chk_export_amm, self.chk_export_dar,
                    self.chk_export_bio_agr, self.chk_export_meteo,
                    self.chk_export_epi):
            ge_lay.addWidget(chk)

        orientation_w = QWidget()
        orientation_lay = QHBoxLayout(orientation_w)
        orientation_lay.setContentsMargins(0, 4, 0, 0)
        orientation_lay.addWidget(QLabel("Orientation de la page :"))
        self.combo_orientation = QComboBox()
        self.combo_orientation.addItem("Portrait", "portrait")
        self.combo_orientation.addItem("Paysage", "paysage")
        orientation_lay.addWidget(self.combo_orientation)
        orientation_lay.addStretch()
        ge_lay.addWidget(orientation_w)

        lay.addWidget(group_export)

        btn_save = QPushButton("Enregistrer les paramètres")
        btn_save.setStyleSheet("""
            QPushButton { background:#16a34a; color:white;
                border-radius:4px; padding:6px 16px; font-weight:bold; }
            QPushButton:hover { background:#15803d; }
        """)
        btn_save.clicked.connect(self._sauver_parametres_app)
        lay.addWidget(btn_save)

        lay.addStretch()
        return widget

    def _charger(self):
        u = self.current_user
        self.lbl_nom_complet.setText(f"{u.get('prenom','')} {u.get('nom','')}")
        self.lbl_username.setText(u.get("username", "—"))
        self.lbl_role.setText("Administrateur" if u.get("role") == "admin" else "Utilisateur")
        cipp = u.get("certiphyto_type") or "Non renseigné"
        if u.get("certiphyto_cipp"):
            cipp += f" — N° {u['certiphyto_cipp']}"
        self.lbl_cipp.setText(cipp)
        self.lbl_cipp_exp.setText(u.get("certiphyto_date_expiration") or "—")

        # Connexion auto
        cfg = lire_config()
        auto_user = cfg.get("auto_login_username")
        self.chk_auto.blockSignals(True)
        self.chk_auto.setChecked(auto_user == u.get("username"))
        self.chk_auto.blockSignals(False)

        # Combo user par défaut (admin)
        if self.current_user.get("role") == "admin" and hasattr(self, "combo_default_user"):
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("SELECT id, username, prenom, nom FROM users "
                            "WHERE actif = 1 ORDER BY nom, prenom")
                rows = cur.fetchall()
                cur.close()
                self.combo_default_user.clear()
                self.combo_default_user.addItem("— Aucun —", None)
                for row in rows:
                    label = f"{row[2]} {row[3]} ({row[1]})"
                    self.combo_default_user.addItem(label, row[1])
                current_default = cfg.get("auto_login_username")
                if current_default:
                    idx = self.combo_default_user.findData(current_default)
                    if idx >= 0:
                        self.combo_default_user.setCurrentIndex(idx)
            except Exception:
                traceback.print_exc()

        # Paramètres app (admin)
        if self.current_user.get("role") == "admin" and hasattr(self, "inp_largeur_planche"):
            params = get_parametres_app()
            self.inp_largeur_planche.setValue(params.get("largeur_planche_defaut", 1.20))
            self.inp_passe_pied.setValue(params.get("passe_pied_defaut", 0.40))
            self.inp_tolerance.setValue(params.get("tolerance_npk_pct", 2.0))
            self.chk_export_amm.setChecked(bool(params.get("export_inclure_amm")))
            self.chk_export_dar.setChecked(bool(params.get("export_inclure_dar")))
            self.chk_export_bio_agr.setChecked(bool(params.get("export_inclure_bio_agr")))
            self.chk_export_meteo.setChecked(bool(params.get("export_inclure_meteo")))
            self.chk_export_epi.setChecked(bool(params.get("export_inclure_epi")))
            idx_orient = self.combo_orientation.findData(
                params.get("export_orientation", "portrait"))
            if idx_orient >= 0:
                self.combo_orientation.setCurrentIndex(idx_orient)

    def _on_auto_changed(self, state):
        cfg = lire_config()
        if state == Qt.Checked.value if hasattr(Qt.Checked, 'value') else 2:
            cfg["auto_login_username"] = self.current_user.get("username")
            QMessageBox.information(self, "Connexion auto",
                "Connexion automatique activée pour votre compte.")
        else:
            if cfg.get("auto_login_username") == self.current_user.get("username"):
                cfg.pop("auto_login_username", None)
        ecrire_config(cfg)

    def _sauver_default_user(self):
        if not hasattr(self, "combo_default_user"):
            return
        username = self.combo_default_user.currentData()
        cfg = lire_config()
        if username:
            cfg["auto_login_username"] = username
        else:
            cfg.pop("auto_login_username", None)
        ecrire_config(cfg)
        QMessageBox.information(self, "OK",
            f"Utilisateur par défaut : {username or 'aucun'}.")

    def _sauver_parametres_app(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE parametres_app SET
                    largeur_planche_defaut=?, passe_pied_defaut=?,
                    tolerance_npk_pct=?, export_inclure_amm=?,
                    export_inclure_dar=?, export_inclure_bio_agr=?,
                    export_inclure_meteo=?, export_inclure_epi=?,
                    export_orientation=?
                WHERE id=1
            """, (
                self.inp_largeur_planche.value(),
                self.inp_passe_pied.value(),
                self.inp_tolerance.value(),
                1 if self.chk_export_amm.isChecked() else 0,
                1 if self.chk_export_dar.isChecked() else 0,
                1 if self.chk_export_bio_agr.isChecked() else 0,
                1 if self.chk_export_meteo.isChecked() else 0,
                1 if self.chk_export_epi.isChecked() else 0,
                self.combo_orientation.currentData(),
            ))
            conn.commit()
            cur.close()
            debug.debug("[parametres] Paramètres application enregistrés")
            QMessageBox.information(self, "Enregistré",
                "Paramètres de l'application mis à jour.")
        except Exception as e:
            debug.debug(f"[parametres] Erreur sauvegarde : {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur", str(e))

    def _changer_mdp(self):
        from admin.admin import DialogMdp
        dlg = DialogMdp(user_id=self.current_user["id"], parent=self)
        dlg.exec()