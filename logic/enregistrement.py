# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import utils.debug as debug

import json

from paths import TOTAL_LABEL, CULTURE_FILE

from views.fertilisants_utilises import mark_doses_modifiees

def enregistrer_doses_culture(window, clavier=False):
    if clavier:
        debug.debug("Depuis raccourci clavier")

    if not window.culture_active:
        debug.debug("⚠️ Aucune culture active, rien à enregistrer")
        return

    culture = window.cultures.get(window.culture_active)
    if not culture:
        debug.debug(f"⚠️ Culture '{window.culture_active}' introuvable")
        return

    fertilisants = []
    debug.debug(f"=== Enregistrement des doses pour '{window.culture_active}' ===")

    # ======================
    # Cas 1 : doses ha calculées
    # ======================
    doses_trouvees = False
    for row in range(window.table_doses_ha.rowCount()):
        nom_item = window.table_doses_ha.item(row, 0)

        if nom_item is None:
            continue

        nom = nom_item.text()
        if nom == TOTAL_LABEL:
            continue

        dose_item = window.table_doses_ha.item(row, 4)
        if dose_item is None:
            continue

        try:
            doses_ha = float(dose_item.text())
        except ValueError:
            doses_ha = 0
        
        fertilisants.append({
            "nom": nom,
            "doses_ha": doses_ha
        })

        doses_trouvees = True
        debug.debug(f" Dose calculée : {nom} = {doses_ha} kg/ha")

    # ======================
    # Cas 2 : pas de doses mais fertilisant
    # ======================
    if not doses_trouvees:
        debug.debug("Aucune dose calculés, vérification des fertilisants utilisés")

        for row in range(window.table_utiliser.rowCount()):
            nom_item = window.table_utiliser.item(row, 0)
            if nom_item is None:
                continue
            
            nom = nom_item.text()
            fertilisants.append({
                "nom": nom,
                "doses_ha": None
            })

            debug.debug(f" Fertilisants enregistré sans dose : {nom}")

    # ======================
    # Cas 3 : rien à enregistrer -> suppression des fertilisant dans CULTURE_FILES
    # ======================
    if not fertilisants:
        debug.debug("Aucun fertilisants à enregistrer → culture vidée")
        culture["fertilisants_utilises"] = fertilisants
        return
    
    # ======================
    # Sauvegarde JSON
    # ======================
    culture["fertilisants_utilises"] = fertilisants
    debug.debug(f"→ {len(fertilisants)} fertilisants affectés à '{window.culture_active}'")

    try:
        with open(CULTURE_FILE, "w", encoding="utf-8") as f:
            json.dump(window.cultures, f, indent=2, ensure_ascii=False)

            #QMessageBox.information(window, "Culture enregistré", "La culture à bien été enregistré")

            debug.debug(f" Enregistrement OK ({len(fertilisants)} fertilisants)")

    except Exception as e:
        debug.debug(f"Erreur sauvegarde : {e}")
    
    mark_doses_modifiees(window, False)
    debug.debug("Suppression de l'affiche de lbl_modifie")

    debug.debug("Culture enregistrer -> table_modifier = False")
    window.table_modifiees = False
# ----------------------