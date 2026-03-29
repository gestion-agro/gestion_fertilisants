# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import zipfile
import io
import csv
import requests
import traceback
import sqlite3
import utils.debug as debug
from db import DB_FILE

EPHY_ZIP_URL = "https://www.data.gouv.fr/api/1/datasets/r/cb51408e-2b97-43a4-94e2-c0de5c3bf5b2"


def count_produits() -> int:
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ppp_produits")
        n = cur.fetchone()[0]
        cur.close()
        conn.close()
        return n
    except Exception:
        return 0


def telecharger_ephy(progress_callback=None) -> bytes:
    debug.debug("[ephy] Téléchargement du ZIP e-phy...")
    r = requests.get(EPHY_ZIP_URL, stream=True, timeout=120)
    r.raise_for_status()

    total = int(r.headers.get("content-length", 0))
    downloaded = 0
    chunks = []

    for chunk in r.iter_content(chunk_size=65536):
        chunks.append(chunk)
        downloaded += len(chunk)
        if progress_callback and total:
            pct = int(downloaded / total * 100)
            progress_callback(pct)

    debug.debug(f"[ephy] ZIP téléchargé ({downloaded // 1024} Ko)")
    return b"".join(chunks)


def importer_depuis_zip(zip_bytes: bytes, progress_callback=None) -> tuple[int, int]:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    nb_produits = 0
    nb_usages = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        debug.debug(f"[ephy] Fichiers dans le ZIP : {namelist}")

        produit_csv = next(
            (n for n in namelist if n.lower() == "produits_utf8.csv"), None)
        usage_csv = next(
            (n for n in namelist
             if n.lower() == "usages_des_produits_autorises_utf8.csv"), None)
        if not usage_csv:
            usage_csv = next(
                (n for n in namelist
                 if n.lower() == "produits_usages_utf8.csv"), None)
        conditions_csv = next(
            (n for n in namelist
             if n.lower() == "produits_condition_emploi_utf8.csv"), None)

        # ── Conditions d'emploi en mémoire ────
        conditions_par_amm = {}
        if conditions_csv:
            with zf.open(conditions_csv) as f:
                reader = csv.DictReader(
                    io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";")
                for row in reader:
                    amm  = (row.get("numero AMM") or "").strip()
                    cond = (row.get("condition d’emploi libelle") or "").strip()
                    # debug.debug(f"[ephy] Condition d'emploi pour AMM {amm} : {cond}")
                    if amm and cond:
                        conditions_par_amm.setdefault(amm, []).append(cond)

        # ── Produits ──────────────────────────
        # Filtre : on n'importe QUE les produits AUTORISE
        if produit_csv:
            debug.debug(f"[ephy] Import produits depuis {produit_csv}")
            with zf.open(produit_csv) as f:
                reader = csv.DictReader(
                    io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";")
                for i, row in enumerate(reader):
                    etat = (row.get("Etat d’autorisation") or "").strip().upper()

                    type = (row.get("type produit") or "").strip().upper()

                    # ← filtre strict sur AUTORISE uniquement
                    if etat != "AUTORISE":
                        continue

                    # Filtre strict sur PPP uniquement
                    if type != "PPP":
                        continue

                    nom      = (row.get("nom produit") or "").strip()
                    amm      = (row.get("numero AMM") or "").strip()
                    sa       = (row.get("Substances actives") or "").strip()
                    mentions = (row.get("mentions autorisees") or "").lower()
                    bio_ok   = 1 if "agriculture biologique" in mentions else 0

                    if not nom or not amm:
                        continue

                    conds = conditions_par_amm.get(amm, [])
                    conditions_txt = "\n".join(conds) if conds else None
                    # debug.debug(f"[ephy] Import du produit {nom} (AMM {amm}) - BIO compatible : {bio_ok} - Conditions : {conditions_txt or 'Aucune'}")

                    cur.execute("""
                        INSERT INTO ppp_produits
                            (nom_commercial, num_amm, substance_active,
                             bio_compatible, unite_dose, conditions_emploi)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(num_amm) DO UPDATE SET
                            nom_commercial    = excluded.nom_commercial,
                            substance_active  = excluded.substance_active,
                            bio_compatible    = excluded.bio_compatible,
                            conditions_emploi = excluded.conditions_emploi
                    """, (nom, amm, sa or None, bio_ok, "L/ha", conditions_txt))
                    nb_produits += 1

                    if progress_callback and i % 500 == 0:
                        progress_callback(i)
        else:
            debug.debug("[ephy] ERREUR : produits_utf8.csv introuvable")

        # ── Usages — vider avant réimport ─────
        cur.execute("DELETE FROM ppp_usages")
        debug.debug("[ephy] Usages existants supprimés avant réimport")

        if usage_csv:
            debug.debug(f"[ephy] Import usages depuis {usage_csv}")
            with zf.open(usage_csv) as f:
                reader = csv.DictReader(
                    io.TextIOWrapper(f, encoding="utf-8-sig"), delimiter=";")
                for row in reader:
                    amm        = (row.get("numero AMM") or "").strip()
                    usage_id   = (row.get("identifiant usage") or "").strip()
                    dose_txt   = (row.get("dose retenue") or "").strip().replace(",", ".")
                    dose_unite = (row.get("dose retenue unite") or "").strip()
                    etat_usage = (row.get("etat usage") or "").strip().upper()
                    dar        = (row.get("delai avant recolte jour") or "").strip()
                    nma        = (row.get("nombre max d'application") or "").strip()
                    stade_min  = (row.get("stade cultural min (BBCH)") or "").strip()
                    stade_max  = (row.get("stade cultural max (BBCH)") or "").strip()
                    znt_eau    = (row.get("ZNT aquatique (en m)") or "").strip()
                    znt_arthro = (row.get("ZNT arthropodes non cibles (en m)") or "").strip()
                    znt_plant  = (row.get("ZNT plantes non cibles (en m)") or "").strip()
                    cond_usage = (row.get("condition emploi") or "").strip()

                    # ← filtre strict sur AUTORISE uniquement
                    if etat_usage != "AUTORISÉ":
                        continue

                    if not amm or not usage_id:
                        continue

                    parts = usage_id.split("*")
                    culture       = parts[0].strip() if len(parts) > 0 else None
                    bio_agresseur = parts[2].strip() if len(parts) > 2 else "Non précisé"
                    if not bio_agresseur:
                        bio_agresseur = "Non précisé"

                    if not culture:
                        continue

                    cur.execute(
                        "SELECT id, bio_compatible FROM ppp_produits WHERE num_amm = ?",
                        (amm,))
                    prod_row = cur.fetchone()
                    if not prod_row:
                        continue
                    produit_id  = prod_row[0]
                    bio_produit = prod_row[1]
                    mode = "bio" if bio_produit else "conventionnel"

                    try:
                        dose = float(dose_txt) if dose_txt else None
                    except ValueError:
                        dose = None

                    def _int(v):
                        try:
                            return int(v) if v else None
                        except ValueError:
                            return None

                    cur.execute("""
                        INSERT INTO ppp_usages
                            (produit_id, culture, bio_agresseur,
                             dose, dose_unite, dar, nma,
                             stade_min, stade_max,
                             znt_eau, znt_arthropodes, znt_plantes,
                             condition_usage, mode)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (produit_id, culture, bio_agresseur,
                          dose, dose_unite or None,
                          _int(dar), _int(nma),
                          stade_min or None, stade_max or None,
                          _int(znt_eau), _int(znt_arthro), _int(znt_plant),
                          cond_usage or None, mode))
                    nb_usages += 1
        else:
            debug.debug("[ephy] ERREUR : fichier usages introuvable")

    conn.commit()
    cur.close()
    conn.close()
    debug.debug(f"[ephy] Import terminé : {nb_produits} produits, {nb_usages} usages")
    return nb_produits, nb_usages