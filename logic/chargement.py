# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import traceback
from db import get_connection
import utils.debug as debug


def charger_fertilisants(window):
    """
    Retourne la liste des fertilisants depuis SQLite.
    Format : liste de dicts compatibles avec l'ancien JSON.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nom, n AS N, p AS P, k AS K,
                   conditionnement, unite, prix, stock
            FROM fertilisants
            ORDER BY nom
        """)
        rows = [dict(row) for row in cur.fetchall()]
        cur.close()
        
        debug.debug(f"[chargement] {len(rows)} fertilisant(s) chargé(s)")
        return rows
    except Exception as e:
        traceback.print_exc()
        debug.debug(f"[chargement] Erreur fertilisants : {e}")
        return []


def charger_cultures(window):
    """
    Retourne les cultures depuis SQLite.
    Format : dict {nom: {N, P, K, surface, id}} compatible avec l'ancien JSON.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nom, besoin_n AS N, besoin_p AS P, besoin_k AS K, surface
            FROM cultures
            ORDER BY nom
        """)
        rows = cur.fetchall()
        cur.close()
        

        cultures = {}
        for row in rows:
            r = dict(row)
            cultures[r["nom"]] = {
                "id":      r["id"],
                "N":       r["N"],
                "P":       r["P"],
                "K":       r["K"],
                "surface": r["surface"],
            }

        debug.debug(f"[chargement] {len(cultures)} culture(s) chargée(s)")
        return cultures
    except Exception as e:
        traceback.print_exc()
        debug.debug(f"[chargement] Erreur cultures : {e}")
        return {}


def charger_doses_culture(culture_nom):
    """
    Retourne les doses enregistrées pour une culture donnée.
    Retourne une liste de dicts {fertilisant_id, nom, dose_kg_ha}.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT dc.fertilisant_id, f.nom, dc.dose_kg_ha
            FROM doses_culture dc
            JOIN cultures c     ON c.id = dc.culture_id
            JOIN fertilisants f ON f.id = dc.fertilisant_id
            WHERE c.nom = ?
        """, (culture_nom,))
        rows = [dict(row) for row in cur.fetchall()]
        cur.close()
        
        return rows
    except Exception as e:
        traceback.print_exc()
        debug.debug(f"[chargement] Erreur doses_culture : {e}")
        return []


# ─────────────────────────────────────────────
# Recharger les cultures
# ─────────────────────────────────────────────
def recharger_cultures(window):

    debug.debug("[chargement] Rechargement cultures")

    window.cultures = charger_cultures(window)

    remplir_tableaux(window)


# ─────────────────────────────────────────────
# Recharger les fertilisants
# ─────────────────────────────────────────────
def recharger_fertilisants(window):

    debug.debug("[chargement] Rechargement fertilisants")

    window.fert_base = charger_fertilisants(window)

    remplir_tableaux(window)


# ─────────────────────────────────────────────
# Charger les fertilisants pour une culture
# ─────────────────────────────────────────────
def charger_ferts_pour_culture(window, nom_culture):

    debug.debug(f"[chargement] Chargement fertilisants pour {nom_culture}")

    culture = window.cultures.get(nom_culture)

    if not culture:
        window.table_utiliser.setRowCount(0)
        return

    doses = charger_doses_culture(nom_culture)

    window.table_utiliser.setRowCount(0)
    window.table_doses_ha.setRowCount(0)
    window.table_doses_surface.setRowCount(0)

    resultats = []

    for fert in doses:

        nom = fert["nom"]
        dose = fert["dose_kg_ha"]

        fert_base = next(
            (f for f in window.fert_base if f["nom"] == nom),
            None
        )

        if not fert_base:
            continue

        # ─── table_utiliser ───

        row = window.table_utiliser.rowCount()
        window.table_utiliser.insertRow(row)

        window.table_utiliser.setItem(row, 0, QTableWidgetItem(nom))
        window.table_utiliser.setItem(row, 1, QTableWidgetItem(str(fert_base["N"])))
        window.table_utiliser.setItem(row, 2, QTableWidgetItem(str(fert_base["P"])))
        window.table_utiliser.setItem(row, 3, QTableWidgetItem(str(fert_base["K"])))

        # ─── calcul NPK réel ───

        N = dose * fert_base["N"] / 100
        P = dose * fert_base["P"] / 100
        K = dose * fert_base["K"] / 100

        resultats.append({
            "nom": nom,
            "doses_ha": dose,
            "N": N,
            "P": P,
            "K": K
        })

        # ─── table_doses_ha ───

        row = window.table_doses_ha.rowCount()
        window.table_doses_ha.insertRow(row)

        window.table_doses_ha.setItem(row, 0, QTableWidgetItem(nom))
        window.table_doses_ha.setItem(row, 1, QTableWidgetItem(f"{N:.1f}"))
        window.table_doses_ha.setItem(row, 2, QTableWidgetItem(f"{P:.1f}"))
        window.table_doses_ha.setItem(row, 3, QTableWidgetItem(f"{K:.1f}"))
        window.table_doses_ha.setItem(row, 4, QTableWidgetItem(f"{dose:.1f}"))

    calculer_doses_surface(window, resultats, culture)

    debug.debug("[chargement] Doses surface recalculées")