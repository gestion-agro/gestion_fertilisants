# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from db import get_connection
from logic.chargement import charger_fertilisants, charger_cultures
from tables.remplissages import remplir_tableaux
import utils.debug as debug


# ─────────────────────────────────────────────
# Fertilisants
# ─────────────────────────────────────────────

def enregistrer_fertilisant(window, fert: dict):
    """
    Insère ou met à jour un fertilisant.
    fert = {nom, N, P, K, conditionnement, unite, prix, stock}
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fertilisants (nom, n, p, k, conditionnement, unite, prix, stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                n               = VALUES(n),
                p               = VALUES(p),
                k               = VALUES(k),
                conditionnement = VALUES(conditionnement),
                unite           = VALUES(unite),
                prix            = VALUES(prix),
                stock           = VALUES(stock)
        """, (
            fert.get("nom"),
            fert.get("N", 0),
            fert.get("P", 0),
            fert.get("K", 0),
            fert.get("conditionnement", 25),
            fert.get("unite", "kg"),
            fert.get("prix", 0),
            fert.get("stock", 0),
        ))
        conn.commit()
        cur.close()
        
        debug.debug(f"[enregistrement] Fertilisant '{fert.get('nom')}' sauvegardé")
        window.fert_base = charger_fertilisants(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur fertilisant : {e}")


def supprimer_fertilisant(window, nom: str):
    """Supprime un fertilisant par son nom."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM fertilisants WHERE nom = %s", (nom,))
        conn.commit()
        cur.close()
        
        debug.debug(f"[enregistrement] Fertilisant '{nom}' supprimé")
        window.fert_base = charger_fertilisants(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur suppression fertilisant : {e}")


# ─────────────────────────────────────────────
# Cultures
# ─────────────────────────────────────────────

def enregistrer_culture(window, culture: dict):
    """
    Insère ou met à jour une culture.
    culture = {nom, N, P, K, surface}
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k, surface)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                besoin_n = VALUES(besoin_n),
                besoin_p = VALUES(besoin_p),
                besoin_k = VALUES(besoin_k),
                surface  = VALUES(surface)
        """, (
            culture.get("nom"),
            culture.get("N", 0),
            culture.get("P", 0),
            culture.get("K", 0),
            culture.get("surface", 10000),
        ))
        conn.commit()
        cur.close()
        
        debug.debug(f"[enregistrement] Culture '{culture.get('nom')}' sauvegardée")
        window.cultures = charger_cultures(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur culture : {e}")


def supprimer_culture(window, nom: str):
    """Supprime une culture par son nom (cascade sur doses_culture)."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cultures WHERE nom = %s", (nom,))
        conn.commit()
        cur.close()
        
        debug.debug(f"[enregistrement] Culture '{nom}' supprimée")
        window.cultures = charger_cultures(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur suppression culture : {e}")


# ─────────────────────────────────────────────
# Doses par culture
# ─────────────────────────────────────────────

def enregistrer_doses_culture(window):
    """
    Sauvegarde les doses de la table_doses_ha pour la culture active.
    Compatible avec l'appel existant depuis le bouton 'Enregistrer'.
    """
    if not window.culture_active:
        debug.debug("[enregistrement] Aucune culture active")
        return

    culture_nom = window.culture_active

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Récupère l'id de la culture
        cur.execute("SELECT id FROM cultures WHERE nom = %s", (culture_nom,))
        row = cur.fetchone()
        if not row:
            debug.debug(f"[enregistrement] Culture '{culture_nom}' introuvable en BDD")
            return
        culture_id = row[0]

        # Parcours de la table doses_ha
        table = window.table_doses_ha
        for r in range(table.rowCount()):
            nom_fert  = table.item(r, 0).text() if table.item(r, 0) else None
            dose_item = table.item(r, 4)
            if not nom_fert or not dose_item:
                continue
            try:
                dose = float(dose_item.text().replace(",", "."))
            except ValueError:
                continue

            # Récupère l'id du fertilisant
            cur.execute("SELECT id FROM fertilisants WHERE nom = %s", (nom_fert,))
            frow = cur.fetchone()
            if not frow:
                continue
            fertilisant_id = frow[0]

            cur.execute("""
                INSERT INTO doses_culture (culture_id, fertilisant_id, dose_kg_ha)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE dose_kg_ha = VALUES(dose_kg_ha)
            """, (culture_id, fertilisant_id, dose))

        conn.commit()
        cur.close()
        
        debug.debug(f"[enregistrement] Doses de '{culture_nom}' sauvegardées")
        from views.fertilisants_utilises import mark_doses_modifiees
        mark_doses_modifiees(window, False)

    except Exception as e:
        debug.debug(f"[enregistrement] Erreur doses_culture : {e}")