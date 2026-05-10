# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtCore import Signal
from PySide6.QtWidgets import *
from PySide6.QtGui import QDoubleValidator, QIntValidator

from db import get_connection
import utils.debug as debug
import traceback


class AjouterFertilisantWindow(QWidget):
    fertilisant_ajoute = Signal()

    def __init__(self, fertilisant=None):
        super().__init__()
        self.editing = fertilisant
        self.setWindowTitle(
            "Modifier un fertilisant" if fertilisant else "Ajouter un fertilisant")
        self.resize(320, 240)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        val_npk   = QDoubleValidator(0.0, 100.0, 2, self)
        val_condi = QIntValidator(0, 100000, self)
        val_prix  = QDoubleValidator(0.0, 99999.0, 2, self)

        self.nom_input   = QLineEdit()
        self.n_input     = QLineEdit(); self.n_input.setValidator(val_npk)
        self.p_input     = QLineEdit(); self.p_input.setValidator(val_npk)
        self.k_input     = QLineEdit(); self.k_input.setValidator(val_npk)
        self.condi_input = QLineEdit(); self.condi_input.setValidator(val_condi)
        self.liste       = QComboBox(); self.liste.addItems(["kg", "L"])
        self.prix_input  = QLineEdit(); self.prix_input.setValidator(val_prix)

        hbox = QHBoxLayout()
        hbox.addWidget(self.condi_input, 3)
        hbox.addWidget(self.liste, 1)

        form.addRow("Nom :",            self.nom_input)
        form.addRow("N :",              self.n_input)
        form.addRow("P :",              self.p_input)
        form.addRow("K :",              self.k_input)
        form.addRow("Conditionnement :", hbox)
        form.addRow("Prix unitaire :",  self.prix_input)
        layout.addLayout(form)

        # Pré-remplissage si modification
        if self.editing:
            self.nom_input.setText(self.editing.get("nom", ""))
            self.n_input.setText(str(self.editing.get("N", "")))
            self.p_input.setText(str(self.editing.get("P", "")))
            self.k_input.setText(str(self.editing.get("K", "")))
            self.condi_input.setText(str(self.editing.get("conditionnement", "")))
            idx = self.liste.findText(self.editing.get("unite", "kg"))
            if idx >= 0:
                self.liste.setCurrentIndex(idx)
            self.prix_input.setText(str(self.editing.get("prix", "")))

        btn_save = QPushButton("Enregistrer")
        btn_save.clicked.connect(self.enregistrer)
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.close)
        layout.addWidget(btn_save)
        layout.addWidget(btn_cancel)

    def enregistrer(self):
        nom = self.nom_input.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return

        try:
            n     = round(float(self.n_input.text().replace(",", ".")), 2)
            p     = round(float(self.p_input.text().replace(",", ".")), 2)
            k     = round(float(self.k_input.text().replace(",", ".")), 2)
            condi = int(float(self.condi_input.text().replace(",", ".")))
            prix  = round(float(self.prix_input.text().replace(",", ".")), 2)
        except ValueError:
            QMessageBox.warning(self, "Erreur",
                "Tous les champs numériques doivent être valides.")
            return

        unite = self.liste.currentText()

        if self.editing:
            reply = QMessageBox.question(
                self, "Confirmation",
                f"Modifier « {self.editing['nom']} » ?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        try:
            conn = get_connection()
            cur  = conn.cursor()

            if self.editing:
                # Mise à jour — on autorise le renommage
                cur.execute("""
                    UPDATE fertilisants
                    SET nom=?, n=?, p=?, k=?,
                        conditionnement=?, unite=?, prix=?
                    WHERE id=?
                """, (nom, n, p, k, condi, unite, prix,
                      self.editing["id"]))
            else:
                # Vérification doublon
                cur.execute(
                    "SELECT COUNT(*) FROM fertilisants WHERE nom = ?", (nom,))
                if cur.fetchone()[0] > 0:
                    QMessageBox.warning(self, "Erreur",
                        "Ce fertilisant existe déjà.")
                    cur.close()
                    return

                cur.execute("""
                    INSERT INTO fertilisants
                        (nom, n, p, k, conditionnement, unite, prix, stock)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, (nom, n, p, k, condi, unite, prix))

            conn.commit()
            cur.close()
            debug.debug(f"[fertilisant] '{nom}' sauvegardé en BDD")
            self.fertilisant_ajoute.emit()
            self.close()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur BDD", str(e))