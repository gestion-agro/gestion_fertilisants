from PySide6.QtCore import Qt

from utils.debug import debug

"""
aligner_table
"""

def aligner_table(table, nom="table"):
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if not item:
                continue

            if col == 0:
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            else:
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)

    debug(f"✅ Table '{nom}' alignée")