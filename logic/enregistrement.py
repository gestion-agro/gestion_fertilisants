# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

from db import get_connection
from logic.chargement import charger_fertilisants, charger_cultures
from tables.remplissages import remplir_tableaux
import utils.debug as debug


def enregistrer_fertilisant(window, fert: dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fertilisants (nom, n, p, k, conditionnement, unite, prix, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(nom) DO UPDATE SET
                n               = excluded.n,
                p               = excluded.p,
                k               = excluded.k,
                conditionnement = excluded.conditionnement,
                unite           = excluded.unite,
                prix            = excluded.prix,
                stock           = excluded.stock
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
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM fertilisants WHERE nom = ?", (nom,))
        conn.commit()
        cur.close()
        debug.debug(f"[enregistrement] Fertilisant '{nom}' supprimé")
        window.fert_base = charger_fertilisants(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur suppression fertilisant : {e}")


def enregistrer_culture(window, culture: dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k, surface)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(nom) DO UPDATE SET
                besoin_n = excluded.besoin_n,
                besoin_p = excluded.besoin_p,
                besoin_k = excluded.besoin_k,
                surface  = excluded.surface
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
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM cultures WHERE nom = ?", (nom,))
        conn.commit()
        cur.close()
        debug.debug(f"[enregistrement] Culture '{nom}' supprimée")
        window.cultures = charger_cultures(window)
        remplir_tableaux(window)
    except Exception as e:
        debug.debug(f"[enregistrement] Erreur suppression culture : {e}")


def enregistrer_doses_culture(window):
    """
    Sauvegarde les fertilisants utilisés + leurs doses pour la culture active.

    Logique :
    - Source principale : table_doses_ha (fertilisant + dose calculée)
    - Si table_doses_ha est vide mais table_utiliser ne l'est pas :
      on sauvegarde les fertilisants avec dose = 0 (ajoutés mais pas calculés)
    - Supprime d'abord les anciennes entrées pour cette culture
      puis réinsère — évite les doublons et prend en compte les suppressions
    """
    if not window.culture_active:
        debug.debug("[enregistrement] Aucune culture active")
        return

    culture_nom = window.culture_active

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Récupère l'id de la culture
        cur.execute("SELECT id FROM cultures WHERE nom = ?", (culture_nom,))
        row = cur.fetchone()
        if not row:
            debug.debug(f"[enregistrement] Culture '{culture_nom}' introuvable")
            return
        culture_id = row[0]

        # ── Construire la liste à sauvegarder ──────────────────────────
        # Priorité : table_doses_ha (a les doses calculées)
        # Fallback  : table_utiliser avec dose = 0

        doses_a_sauvegarder = {}  # {nom_fertilisant: dose}

        table_ha = window.table_doses_ha
        if table_ha.rowCount() > 0:
            for r in range(table_ha.rowCount()):
                nom_item  = table_ha.item(r, 0)
                dose_item = table_ha.item(r, 4)
                if not nom_item:
                    continue
                nom = nom_item.text()
                try:
                    dose = float(dose_item.text().replace(",", ".")) \
                           if dose_item else 0.0
                except ValueError:
                    dose = 0.0
                doses_a_sauvegarder[nom] = dose
        else:
            # Pas encore calculé — sauvegarder depuis table_utiliser avec dose 0
            table_u = window.table_utiliser
            for r in range(table_u.rowCount()):
                nom_item = table_u.item(r, 0)
                if nom_item:
                    doses_a_sauvegarder[nom_item.text()] = 0.0

        if not doses_a_sauvegarder:
            # Rien à sauvegarder — supprimer les anciennes entrées
            cur.execute(
                "DELETE FROM doses_culture WHERE culture_id = ?", (culture_id,))
            conn.commit()
            cur.close()
            debug.debug(f"[enregistrement] Doses de '{culture_nom}' vidées")
            from views.fertilisants_utilises import mark_doses_modifiees
            mark_doses_modifiees(window, False)
            window.table_modifiees = False
            return

        # ── Supprimer les anciennes entrées ────────────────────────────
        cur.execute(
            "DELETE FROM doses_culture WHERE culture_id = ?", (culture_id,))

        # ── Réinsérer ─────────────────────────────────────────────────
        for nom_fert, dose in doses_a_sauvegarder.items():
            cur.execute(
                "SELECT id FROM fertilisants WHERE nom = ?", (nom_fert,))
            frow = cur.fetchone()
            if not frow:
                debug.debug(f"[enregistrement] Fertilisant '{nom_fert}' introuvable")
                continue
            fertilisant_id = frow[0]

            cur.execute("""
                INSERT INTO doses_culture (culture_id, fertilisant_id, dose_kg_ha)
                VALUES (?, ?, ?)
            """, (culture_id, fertilisant_id, dose))

        conn.commit()
        cur.close()

        debug.debug(
            f"[enregistrement] {len(doses_a_sauvegarder)} dose(s) "
            f"sauvegardées pour '{culture_nom}'")

        from views.fertilisants_utilises import mark_doses_modifiees
        mark_doses_modifiees(window, False)
        window.table_modifiees = False

    except Exception as e:
        debug.debug(f"[enregistrement] Erreur doses_culture : {e}")
        import traceback
        traceback.print_exc()