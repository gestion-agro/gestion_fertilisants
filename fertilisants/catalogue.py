# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from db import get_connection, peut_action
import utils.debug as debug
import traceback


class CatalogueFertilisants(QWidget):
    """Catalogue simple du stock de fertilisants de l'exploitation."""
    fertilisant_modifie = Signal()

    def __init__(self, current_user: dict, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self._peut_ecrire    = peut_action(current_user, "fertilisants", "ecriture")
        self._peut_supprimer = peut_action(current_user, "fertilisants", "suppression")
        self._build_ui()
        self.btn_ajouter.setVisible(self._peut_ecrire)
        self._charger()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        titre = QLabel("Catalogue des fertilisants")
        f = QFont(); f.setPointSize(15); f.setBold(True)
        titre.setFont(f)
        top.addWidget(titre)
        top.addStretch()
        self.btn_ajouter = QPushButton("+ Ajouter un fertilisant")
        self.btn_ajouter.clicked.connect(lambda: self._ouvrir_dialog())
        top.addWidget(self.btn_ajouter)
        root.addLayout(top)

        filtre = QHBoxLayout()
        self.inp_recherche = QLineEdit()
        self.inp_recherche.setPlaceholderText("Rechercher un fertilisant...")
        self.inp_recherche.textChanged.connect(self._filtrer)
        filtre.addWidget(self.inp_recherche)
        self.chk_uab = QCheckBox("UAB uniquement")
        self.chk_uab.stateChanged.connect(self._filtrer)
        filtre.addWidget(self.chk_uab)
        filtre.addStretch()
        root.addLayout(filtre)

        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["Nom", "N", "P", "K", "Prix", "Stock", "Cdtmt", "UAB", "Revendeur"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._menu_context)
        self.table.cellDoubleClicked.connect(
            lambda row, col: self._ouvrir_dialog(self.table.item(row, 0).data(Qt.UserRole))
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 9):
            hh.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

    def _charger(self):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM fertilisants ORDER BY nom")
            self._tous = [dict(r) for r in cur.fetchall()]
            cur.close()
            self._filtrer()
        except Exception as e:
            debug.debug(f"[catalogue_ferti] Erreur chargement : {e}")
            traceback.print_exc()

    def recharger(self):
        self._charger()

    def _filtrer(self):
        terme = self.inp_recherche.text().lower().strip()
        uab_only = self.chk_uab.isChecked()

        self.table.setRowCount(0)
        for f in self._tous:
            if terme and terme not in f["nom"].lower():
                continue
            if uab_only and not f.get("uab"):
                continue

            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(f["nom"]))
            self.table.setItem(r, 1, QTableWidgetItem(f"{f['n']}%"))
            self.table.setItem(r, 2, QTableWidgetItem(f"{f['p']}%"))
            self.table.setItem(r, 3, QTableWidgetItem(f"{f['k']}%"))
            self.table.setItem(r, 4, QTableWidgetItem(f"{f['prix']:.2f} €"))

            stock_kg = f["stock"] or 0
            cdt = f["conditionnement"] or 1
            sacs_pleins = int(stock_kg // cdt)
            reste_kg = stock_kg - (sacs_pleins * cdt)
            if reste_kg > 0.01:
                stock_txt = f"{stock_kg:.0f} {f['unite']} ({sacs_pleins} + {reste_kg:.0f}{f['unite']})"
            else:
                stock_txt = f"{stock_kg:.0f} {f['unite']} ({sacs_pleins} sacs)"
            stock_item = QTableWidgetItem(stock_txt)
            if stock_kg <= 0:
                stock_item.setForeground(QColor("#DC2626"))
            self.table.setItem(r, 5, stock_item)

            self.table.setItem(r, 6,
                QTableWidgetItem(f"{f['conditionnement']} {f['unite']}"))
            uab_txt = "✓ Bio" if f.get("uab") else "—"
            self.table.setItem(r, 7, QTableWidgetItem(uab_txt))
            self.table.setItem(r, 8,
                QTableWidgetItem(f.get("revendeur_nom") or "—"))
            self.table.item(r, 0).setData(Qt.UserRole, f["id"])

    def _menu_context(self, pos):
        row = self.table.rowAt(pos.y())
        if row < 0:
            return
        item = self.table.item(row, 0)
        fert_id = item.data(Qt.UserRole)
        menu = QMenu(self)
        if self._peut_ecrire:
            menu.addAction("Modifier", lambda: self._ouvrir_dialog(fert_id))
        if self._peut_supprimer:
            menu.addSeparator()
            menu.addAction("Supprimer", lambda: self._supprimer(fert_id))
        if not menu.isEmpty():
            menu.exec(self.table.viewport().mapToGlobal(pos))

    def _ouvrir_dialog(self, fert_id=None):
        dlg = DialogFertilisant(fert_id=fert_id, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._charger()
            self.fertilisant_modifie.emit()

    def _supprimer(self, fert_id: int):
        rep = QMessageBox.question(self, "Confirmer",
            "Supprimer ce fertilisant du catalogue ?")
        if rep == QMessageBox.Yes:
            try:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM fertilisants WHERE id=?", (fert_id,))
                conn.commit()
                cur.close()
                self._charger()
                self.fertilisant_modifie.emit()
            except Exception as e:
                QMessageBox.critical(self, "Erreur",
                    "Impossible de supprimer : ce fertilisant est peut-être "
                    "utilisé dans le carnet de fertilisation.\n" + str(e))


# ──────────────────────────────────────────────
# Dialog Fertilisant
# ──────────────────────────────────────────────
class DialogFertilisant(QDialog):
    def __init__(self, fert_id=None, parent=None):
        super().__init__(parent)
        self.fert_id = fert_id
        self.setWindowTitle(
            "Nouveau fertilisant" if not fert_id else "Modifier le fertilisant")
        self.setMinimumWidth(420)
        self._build_ui()
        if fert_id:
            self._charger(fert_id)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.inp_nom = QLineEdit()
        form.addRow("Nom *", self.inp_nom)

        self.combo_origine = QComboBox()
        self.combo_origine.addItem("Minéral", "mineral")
        self.combo_origine.addItem("Organique", "organique")
        form.addRow("Origine *", self.combo_origine)

        npk_w = QWidget()
        npk_lay = QHBoxLayout(npk_w)
        npk_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_n = QDoubleSpinBox()
        self.inp_n.setRange(0, 100)
        self.inp_n.setSuffix(" % N")
        self.inp_p = QDoubleSpinBox()
        self.inp_p.setRange(0, 100)
        self.inp_p.setSuffix(" % P")
        self.inp_k = QDoubleSpinBox()
        self.inp_k.setRange(0, 100)
        self.inp_k.setSuffix(" % K")
        npk_lay.addWidget(self.inp_n)
        npk_lay.addWidget(self.inp_p)
        npk_lay.addWidget(self.inp_k)
        form.addRow("Composition", npk_w)

        cdt_w = QWidget()
        cdt_lay = QHBoxLayout(cdt_w)
        cdt_lay.setContentsMargins(0, 0, 0, 0)
        self.inp_conditionnement = QDoubleSpinBox()
        self.inp_conditionnement.setRange(0.1, 99999)
        self.combo_unite = QComboBox()
        self.combo_unite.addItems(["kg", "L", "t"])
        cdt_lay.addWidget(self.inp_conditionnement)
        cdt_lay.addWidget(self.combo_unite)
        form.addRow("Conditionnement", cdt_w)

        self.inp_prix = QDoubleSpinBox()
        self.inp_prix.setRange(0, 99999)
        self.inp_prix.setDecimals(2)
        self.inp_prix.setSuffix(" € / conditionnement")
        form.addRow("Prix", self.inp_prix)

        self.inp_stock = QDoubleSpinBox()
        self.inp_stock.setRange(0, 999999)
        self.inp_stock.setDecimals(1)
        form.addRow("Stock disponible", self.inp_stock)

        self.chk_uab = QCheckBox("Utilisable en Agriculture Biologique (UAB)")
        form.addRow("", self.chk_uab)

        sep = QLabel("── Revendeur ──")
        sep.setStyleSheet("color:gray; font-size:11px;")
        form.addRow(sep)

        self.inp_revendeur_nom = QLineEdit()
        form.addRow("Nom", self.inp_revendeur_nom)
        self.inp_revendeur_tel = QLineEdit()
        form.addRow("Téléphone", self.inp_revendeur_tel)
        self.inp_revendeur_email = QLineEdit()
        form.addRow("Email", self.inp_revendeur_email)

        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._valider)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _charger(self, fert_id: int):
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM fertilisants WHERE id=?", (fert_id,))
            f = dict(cur.fetchone())
            cur.close()

            self.inp_nom.setText(f.get("nom", ""))
            idx = self.combo_origine.findData(f.get("origine", "mineral"))
            self.combo_origine.setCurrentIndex(max(0, idx))
            self.inp_n.setValue(f.get("n", 0))
            self.inp_p.setValue(f.get("p", 0))
            self.inp_k.setValue(f.get("k", 0))
            self.inp_conditionnement.setValue(f.get("conditionnement", 25))
            idx_u = self.combo_unite.findText(f.get("unite", "kg"))
            self.combo_unite.setCurrentIndex(max(0, idx_u))
            self.inp_prix.setValue(f.get("prix", 0))
            self.inp_stock.setValue(f.get("stock", 0))
            self.chk_uab.setChecked(bool(f.get("uab")))
            self.inp_revendeur_nom.setText(f.get("revendeur_nom") or "")
            self.inp_revendeur_tel.setText(f.get("revendeur_tel") or "")
            self.inp_revendeur_email.setText(f.get("revendeur_email") or "")
        except Exception:
            traceback.print_exc()

    def _valider(self):
        nom = self.inp_nom.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant", "Le nom est obligatoire.")
            return

        origine = self.combo_origine.currentData()
        n, p, k = self.inp_n.value(), self.inp_p.value(), self.inp_k.value()
        conditionnement = self.inp_conditionnement.value()
        unite = self.combo_unite.currentText()
        prix = self.inp_prix.value()
        stock = self.inp_stock.value()
        uab = 1 if self.chk_uab.isChecked() else 0
        rev_nom = self.inp_revendeur_nom.text().strip() or None
        rev_tel = self.inp_revendeur_tel.text().strip() or None
        rev_email = self.inp_revendeur_email.text().strip() or None

        try:
            conn = get_connection()
            cur = conn.cursor()
            if self.fert_id:
                cur.execute("""
                    UPDATE fertilisants SET
                        nom=?, n=?, p=?, k=?, conditionnement=?, unite=?,
                        prix=?, stock=?, uab=?, origine=?,
                        revendeur_nom=?, revendeur_tel=?, revendeur_email=?
                    WHERE id=?
                """, (nom, n, p, k, conditionnement, unite, prix, stock,
                      uab, origine, rev_nom, rev_tel, rev_email, self.fert_id))
            else:
                cur.execute("""
                    INSERT INTO fertilisants (
                        nom, n, p, k, conditionnement, unite, prix, stock,
                        uab, origine, revendeur_nom, revendeur_tel, revendeur_email
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (nom, n, p, k, conditionnement, unite, prix, stock,
                      uab, origine, rev_nom, rev_tel, rev_email))
            conn.commit()
            cur.close()
            self.accept()
        except Exception as e:
            msg = str(e)
            if "UNIQUE" in msg:
                QMessageBox.warning(self, "Erreur",
                    "Un fertilisant avec ce nom existe déjà.")
            else:
                QMessageBox.critical(self, "Erreur", msg)
            traceback.print_exc()