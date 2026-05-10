# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtCore import Signal
from PySide6.QtWidgets import *
from PySide6.QtGui import QDoubleValidator

from db import get_connection
import utils.debug as debug
import traceback


class AjouterCultureWindow(QWidget):
    culture_ajoute = Signal()

    def __init__(self, culture=None):
        super().__init__()
        self.editing = culture
        self.setWindowTitle(
            "Modifier une culture" if culture else "Ajouter une culture")
        self.resize(320, 220)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        val_npk     = QDoubleValidator(0.0, 9999.0, 1, self)
        val_surface = QDoubleValidator(0.0, 999999.0, 1, self)

        self.nom_input = QLineEdit()
        self.n_input   = QLineEdit(); self.n_input.setValidator(val_npk)
        self.p_input   = QLineEdit(); self.p_input.setValidator(val_npk)
        self.k_input   = QLineEdit(); self.k_input.setValidator(val_npk)
        self.surface   = QLineEdit(); self.surface.setValidator(val_surface)
        self.surface.setPlaceholderText("en m²")

        form.addRow("Nom :",         self.nom_input)
        form.addRow("N :",           self.n_input)
        form.addRow("P :",           self.p_input)
        form.addRow("K :",           self.k_input)
        form.addRow("Surface (m²) :", self.surface)
        layout.addLayout(form)

        # Pré-remplissage si modification
        if self.editing:
            self.nom_input.setText(self.editing.get("nom", ""))
            self.n_input.setText(str(self.editing.get("N", "")))
            self.p_input.setText(str(self.editing.get("P", "")))
            self.k_input.setText(str(self.editing.get("K", "")))
            self.surface.setText(str(self.editing.get("surface", "")))

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
            n       = round(float(self.n_input.text().replace(",", ".")), 1)
            p       = round(float(self.p_input.text().replace(",", ".")), 1)
            k       = round(float(self.k_input.text().replace(",", ".")), 1)
            surface = round(float(self.surface.text().replace(",", ".")), 1)
        except ValueError:
            QMessageBox.warning(self, "Erreur",
                "Tous les champs numériques doivent être valides.")
            return

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
                cur.execute("""
                    UPDATE cultures
                    SET nom=?, besoin_n=?, besoin_p=?, besoin_k=?, surface=?
                    WHERE id=?
                """, (nom, n, p, k, surface, self.editing["id"]))
            else:
                cur.execute(
                    "SELECT COUNT(*) FROM cultures WHERE nom = ?", (nom,))
                if cur.fetchone()[0] > 0:
                    QMessageBox.warning(self, "Erreur",
                        "Cette culture existe déjà.")
                    cur.close()
                    return

                cur.execute("""
                    INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k, surface)
                    VALUES (?, ?, ?, ?, ?)
                """, (nom, n, p, k, surface))

            conn.commit()
            cur.close()
            debug.debug(f"[culture] '{nom}' sauvegardée en BDD")
            self.culture_ajoute.emit()
            self.close()

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Erreur BDD", str(e))