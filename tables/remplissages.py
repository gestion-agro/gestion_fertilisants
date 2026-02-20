# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

import utils.debug as debug

from tables.tables import aligner_table

""" 
remplir_tableaux
remplir_tables_doses_ha
setup_table_header
_clear_table
vider_table_calcul
vider_table_milieu
 """

# ----------------------
# Remplissage des tableaux
def remplir_tableaux(window):
    debug.debug("=== remplir_tableaux ===")

    # --------- Fertilisants ----------
    debug.debug("→ Remplissage tableau fertiliants")
    window.table_fertilisants.setRowCount(0)

    # trier la liste des fertilisants par nom
    ferts_tries = sorted(window.fert_base, key=lambda x: x.get("nom", "").lower())
    debug.debug(f"{len(ferts_tries)} fertiliant(s) à afficher")

    for i, fert in enumerate(ferts_tries):
        row = window.table_fertilisants.rowCount()
        window.table_fertilisants.insertRow(row)

        nom = fert.get("nom", "")
        window.table_fertilisants.setItem(row, 0, QTableWidgetItem(nom))
        window.table_fertilisants.setItem(row, 1, QTableWidgetItem(str(fert.get("N", 0))))
        window.table_fertilisants.setItem(row, 2, QTableWidgetItem(str(fert.get("P", 0))))
        window.table_fertilisants.setItem(row, 3, QTableWidgetItem(str(fert.get("K", 0))))
        window.table_fertilisants.setItem(
            row, 4,
            QTableWidgetItem(f"{fert.get('conditionnement', 1)} {fert.get('unite', 'kg')}")
        )
        window.table_fertilisants.setItem(row, 5, QTableWidgetItem(str(fert.get("prix", 0.0))))
        
        chk = QCheckBox()
        chk.setChecked(True)

        cell_widget = QWidget()
        layout = QHBoxLayout(cell_widget)
        layout.addWidget(chk)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(layout)

        window.table_fertilisants.setCellWidget(row, 6, cell_widget)

        debug.debug(
            f" [{row}] Fertilisant affiché :",
            nom,
            f"NPK=({fert.get('N')},{fert.get('P')},{fert.get('K')})",
            f"prix={fert.get('prix')}"
        )

    # --------- Cultures ----------
    debug.debug("→ Remplissage tableau cultures")
    window.table_cultures.setRowCount(0)

    cultures_tries = sorted(window.cultures.items(), key=lambda x: x[0].lower())
    debug.debug(f"{len(cultures_tries)} culture(s) à afficher")

    # trier les cultures par nom
    for i, (nom, culture) in enumerate(cultures_tries):
        row = window.table_cultures.rowCount()
        window.table_cultures.insertRow(row)

        window.table_cultures.setItem(row, 0, QTableWidgetItem(nom))
        window.table_cultures.setItem(row, 1, QTableWidgetItem(str(culture.get("N", 0))))
        window.table_cultures.setItem(row, 2, QTableWidgetItem(str(culture.get("P", 0))))
        window.table_cultures.setItem(row, 3, QTableWidgetItem(str(culture.get("K", 0))))
        window.table_cultures.setItem(row, 4, QTableWidgetItem(str(culture.get("surface", 10000))))

        debug.debug(
            f"  [{row}] Culture affichée :",
            nom,
            f"NPK=({culture.get('N')},{culture.get('P')},{culture.get('K')})",
            f"surface={culture.get('surface', 10000)}"
        )
    
    # --------- Alignements ---------
    aligner_table(window.table_cultures, "table_cultures")
    aligner_table(window.table_doses_ha, "table_doses_ha")
    aligner_table(window.table_doses_surface, "table_doses_surface")
    aligner_table(window.table_utiliser, "table_utiliser")
    aligner_table(window.table_fertilisants, "table_fertiliants")

    debug.debug("=== Fin remplir_tableaux ===")
# ----------------------

# Remplissage des doses par ha dans table_doses_ha
# ----------------------
def remplir_table_doses_ha(window, resultats):
    debug.debug("\n=== remplir_table_doses_ha ===")
    total_N = total_P = total_K = 0

    for r in resultats:
        debug.debug(f"Fertil. {r['nom']} → N={r['N']} P={r['P']} K={r['K']} doses_ha={r['doses_ha']}")
        row = window.table_doses_ha.rowCount()
        window.table_doses_ha.insertRow(row)

        window.table_doses_ha.setItem(row, 0, QTableWidgetItem(r["nom"]))
        window.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{r['N']:.1f}"))
        window.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{r['P']:.1f}"))
        window.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{r['K']:.1f}"))
        window.table_doses_ha.setItem(row, 4, QTableWidgetItem(f"{r['doses_ha']:.1f}"))

        total_N += r["N"]
        total_P += r["P"]
        total_K += r["K"]

    # Ligne TOTAL
    row = window.table_doses_ha.rowCount()
    window.table_doses_ha.insertRow(row)
    debug.debug(f"Ligne TOTAL → N={total_N} P={total_P} K={total_K}")

    window.table_doses_ha.setItem(row, 0, QTableWidgetItem("TOTAL"))
    window.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{total_N:.1f}"))
    window.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{total_P:.1f}"))
    window.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{total_K:.1f}"))
    window.table_doses_ha.setItem(row, 4, QTableWidgetItem(""))

    font = QFont()
    font.setBold(True)

    for col in range(window.table_doses_ha.columnCount()):
        item = window.table_doses_ha.item(row, col)
        if item:
            item.setFont(font)
            item.setBackground(QBrush(QColor("#e6e6e6")))

    window.table_doses_ha.setRowHeight(row, 32)
    aligner_table(window.table_doses_ha,"table_doses_ha")

# ----------------------
# fonction qui centralise l'ajustement des colonnes
# ----------------------
def setup_table_header(window, table, stretch_col=0):
    """
    Configure le header d'une table : 
    - La colonne stretch_col prend tout l'espace restant
    - Les autres colonnes s'ajustent automatiquement au contenu
    """
    header = table.horizontalHeader()
    for col in range(table.columnCount()):
        if col == stretch_col:
            header.setSectionResizeMode(col, QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
# ----------------------

# Fonction de vidage de tableaux
# ----------------------
def _clear_table(window, table):
    if table is not None:
        table.setRowCount(0)
# ----------------------

# Vider tableau calculs
# ----------------------
def vider_table_calcul(window):
    debug.debug("Action : Vider calculs (résultats)")

    # Table dose ha
    _clear_table(window, window.table_doses_ha)

    # Table dose surface
    _clear_table(window, window.table_doses_surface)

    QMessageBox.information(
        window,
        "Tableaux vidés",
        "Les tableaux intermédiaires ont été vidés"
        )
    
    window.table_modifiees = True
    debug.debug("Tableaux calculs supprimé -> table_modifier = True")
# ----------------------

# Vider tableau fertilisant (tableu_utilise, table_doses_ha, table_doses_surface)
# ----------------------
def vider_table_milieux(window):
    debug.debug("Action : Vider tableaux (millieux)")

    # Table fertiliants utilisés
    _clear_table(window, window.table_utiliser)

    # Table dose ha
    _clear_table(window, window.table_doses_ha)

    # Table dose surface
    _clear_table(window, window.table_doses_surface)

    QMessageBox.information(
        window,
        "Tableaux vidés",
        "Les tableaux intermédiaires ont été vidés"
        )
    
    window.table_modifiees = True
    debug.debug("Tableaux intermédiaires supprimé -> table_modifier = True")
# ----------------------