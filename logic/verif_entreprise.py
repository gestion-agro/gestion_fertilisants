# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX
"""
Vérification des informations de l'entreprise :
1. Validation SIRET locale (algorithme de Luhn)
2. Vérification Agence BIO (API publique, sans clé)
3. Vérification Sirene INSEE (optionnelle, nécessite une clé API)
"""

import requests
import utils.debug as debug


# ── 1. Validation SIRET (Luhn) ───────────────
def valider_siret(siret: str) -> tuple[bool, str]:
    """Vérifie qu'un SIRET est mathématiquement valide via l'algorithme
    de Luhn (pas d'appel réseau — validation purement locale).

    Retourne (valide: bool, message: str).
    """
    s = (siret or "").strip().replace(" ", "")
    if not s.isdigit():
        return False, "Le SIRET ne doit contenir que des chiffres."
    if len(s) != 14:
        return False, f"Le SIRET doit contenir 14 chiffres (actuellement {len(s)})."

    # Algorithme de Luhn adapté au SIRET
    total = 0
    for i, digit in enumerate(reversed(s)):
        n = int(digit)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n

    if total % 10 != 0:
        return False, "Le SIRET est invalide (clé de contrôle incorrecte)."
    return True, "SIRET valide."


# ── 2. Vérification Agence BIO ────────────────
AGENCE_BIO_URL = "https://opendata.agencebio.org/api/gouv/operateurs/"


def verifier_agence_bio(num_bio: str = None, siret: str = None,
                         nom: str = None, organisme_certif: str = None,
                         timeout: int = 8) -> dict:
    """Interroge l'API publique de l'Agence BIO pour vérifier l'existence
    et la cohérence des informations de l'opérateur bio.

    Retourne un dict :
    {
        "ok": bool,
        "trouve": bool,
        "nom_officiel": str | None,
        "siret_officiel": str | None,
        "organisme_certif_officiel": str | None,
        "date_engagement": str | None,
        "activites": list,
        "alertes": [str],   # incohérences détectées
        "erreur": str | None,
    }
    """
    resultat = {
        "ok": False,
        "trouve": False,
        "nom_officiel": None,
        "siret_officiel": None,
        "organisme_certif_officiel": None,
        "date_engagement": None,
        "activites": [],
        "alertes": [],
        "erreur": None,
    }

    if not num_bio and not siret:
        resultat["erreur"] = "Aucun N° bio ni SIRET fourni pour la recherche."
        return resultat

    # Paramètre de recherche : num_bio en priorité, sinon siret
    params = {}
    if num_bio:
        params["numeroBio"] = num_bio.strip()
    elif siret:
        params["siret"] = siret.strip()

    try:
        debug.debug(f"[verif_bio] Requête Agence BIO : {params}")
        resp = requests.get(AGENCE_BIO_URL, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        resultat["erreur"] = "Impossible de joindre l'API Agence BIO (pas de connexion internet)."
        return resultat
    except requests.exceptions.Timeout:
        resultat["erreur"] = "L'API Agence BIO ne répond pas (timeout)."
        return resultat
    except Exception as e:
        resultat["erreur"] = f"Erreur API Agence BIO : {e}"
        return resultat

    items = data if isinstance(data, list) else data.get("items", [])
    if not items:
        resultat["trouve"] = False
        resultat["erreur"] = (
            f"Aucun opérateur bio trouvé pour "
            f"{'N° bio ' + num_bio if num_bio else 'SIRET ' + siret}.")
        return resultat

    op = items[0]
    resultat["trouve"] = True
    resultat["ok"] = True

    # Extraction des infos officielles
    nom_officiel = op.get("raisonSociale") or op.get("denominationCourante") or ""
    siret_officiel = op.get("siret") or ""
    date_engagement = op.get("dateEngagement") or ""

    # Organisme certificateur
    certificats = op.get("certificats") or []
    oc_officiel = ""
    if certificats:
        oc_officiel = certificats[0].get("organisme") or ""

    # Activités certifiées
    activites = [a.get("activite", "") for a in op.get("activitesBio", [])]

    # État de certification et lien certificat
    etat_certif = ""
    lien_certif = None
    if certificats:
        etat_certif = certificats[0].get("etatCertification") or ""
        lien_certif = certificats[0].get("url")

    # État de production (AB / C1 / C2 / C3)
    etats_prod = set()
    for prod in (op.get("productions") or []):
        for ep in (prod.get("etatProductions") or []):
            ep_val = ep.get("etatProduction")
            if ep_val:
                etats_prod.add(ep_val)
    etat_production = ("AB" if "AB" in etats_prod
                       else ", ".join(sorted(etats_prod)) if etats_prod
                       else "—")

    resultat.update({
        "nom_officiel": nom_officiel,
        "siret_officiel": siret_officiel,
        "organisme_certif_officiel": oc_officiel,
        "date_engagement": date_engagement,
        "activites": activites,
        "etat_certif": etat_certif,
        "etat_production": etat_production,
        "lien_certificat": lien_certif,
        "actif": etat_certif in ("ENGAGEE", "AB", "ACTIVE"),
        "numero_bio_trouve": str(op.get("numeroBio") or ""),
        "adresses": op.get("adressesOperateurs") or [],
    })

    # ── Vérifications de cohérence ──
    alertes = []

    # Nom
    if nom and nom_officiel:
        nom_clean = nom.strip().lower().replace("  ", " ")
        nom_off_clean = nom_officiel.strip().lower().replace("  ", " ")
        if nom_clean not in nom_off_clean and nom_off_clean not in nom_clean:
            alertes.append(
                f"⚠ Nom différent — votre saisie : « {nom} » / "
                f"Agence BIO : « {nom_officiel} »")

    # SIRET
    if siret and siret_officiel:
        if siret.strip() != siret_officiel.strip():
            alertes.append(
                f"⚠ SIRET différent — votre saisie : {siret} / "
                f"Agence BIO : {siret_officiel}")

    # Organisme certificateur
    if organisme_certif and oc_officiel:
        oc_clean = organisme_certif.strip().lower()
        oc_off_clean = oc_officiel.strip().lower()
        if oc_clean not in oc_off_clean and oc_off_clean not in oc_clean:
            alertes.append(
                f"⚠ Organisme certificateur différent — votre saisie : "
                f"« {organisme_certif} » / Agence BIO : « {oc_officiel} »")

    resultat["alertes"] = alertes
    debug.debug(f"[verif_bio] Résultat : {resultat}")
    return resultat


# ── 3. Vérification Sirene INSEE (optionnelle) ──
SIRENE_URL = "https://api.insee.fr/api-sirene/3.11/siret/{siret}"


def verifier_sirene(siret: str, api_key: str,
                     nom: str = None, timeout: int = 8) -> dict:
    """Interroge l'API Sirene INSEE pour vérifier le SIRET et la raison
    sociale. Nécessite une clé API INSEE (configurable dans Paramètres).

    Retourne un dict :
    {
        "ok": bool,
        "actif": bool,
        "nom_officiel": str | None,
        "adresse_officielle": str | None,
        "activite_principale": str | None,
        "alertes": [str],
        "erreur": str | None,
    }
    """
    resultat = {
        "ok": False,
        "actif": False,
        "nom_officiel": None,
        "adresse_officielle": None,
        "activite_principale": None,
        "alertes": [],
        "erreur": None,
    }

    s = (siret or "").strip()
    if not s or len(s) != 14:
        resultat["erreur"] = "SIRET invalide ou manquant."
        return resultat
    if not api_key:
        resultat["erreur"] = (
            "Clé API INSEE non configurée. "
            "Ajoutez-la dans Paramètres → Application → Clé API INSEE.")
        return resultat

    headers = {"X-INSEE-Api-Key-Integration": api_key.strip()}
    url = SIRENE_URL.format(siret=s)

    try:
        debug.debug(f"[verif_sirene] Requête INSEE : {url}")
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 401:
            resultat["erreur"] = "Clé API INSEE invalide ou expirée."
            return resultat
        if resp.status_code == 404:
            resultat["erreur"] = f"SIRET {s} introuvable dans le répertoire Sirene."
            return resultat
        if resp.status_code == 429:
            resultat["erreur"] = "Quota API INSEE dépassé (30 requêtes/minute). Réessayez dans 1 minute."
            return resultat
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        resultat["erreur"] = "Impossible de joindre l'API INSEE (pas de connexion internet)."
        return resultat
    except requests.exceptions.Timeout:
        resultat["erreur"] = "L'API INSEE ne répond pas (timeout)."
        return resultat
    except Exception as e:
        resultat["erreur"] = f"Erreur API INSEE : {e}"
        return resultat

    etab = data.get("etablissement", {})
    ul = etab.get("uniteLegale", {})

    # État administratif (A = Actif, F = Fermé)
    etat = etab.get("etatAdministratifEtablissement", "F")
    resultat["actif"] = (etat == "A")
    if not resultat["actif"]:
        resultat["alertes"].append(
            "⚠ Cet établissement est FERMÉ dans le répertoire Sirene.")

    # Nom officiel
    nom_officiel = (
        ul.get("denominationUniteLegale")
        or ul.get("nomUniteLegale")
        or ""
    )
    resultat["nom_officiel"] = nom_officiel

    # Adresse
    adr = etab.get("adresseEtablissement", {})
    voie = " ".join(filter(None, [
        adr.get("numeroVoieEtablissement"),
        adr.get("typeVoieEtablissement"),
        adr.get("libelleVoieEtablissement"),
    ]))
    cp   = adr.get("codePostalEtablissement", "")
    ville = adr.get("libelleCommuneEtablissement", "")
    resultat["adresse_officielle"] = f"{voie}, {cp} {ville}".strip(", ")

    # Activité principale (code APE)
    resultat["activite_principale"] = (
        etab.get("activitePrincipaleEtablissement")
        or ul.get("activitePrincipaleUniteLegale")
        or "—")

    # Vérification cohérence nom
    if nom and nom_officiel:
        nom_clean = nom.strip().lower()
        nom_off_clean = nom_officiel.strip().lower()
        if nom_clean not in nom_off_clean and nom_off_clean not in nom_clean:
            resultat["alertes"].append(
                f"⚠ Nom différent — votre saisie : « {nom} » / "
                f"INSEE : « {nom_officiel} »")

    resultat["ok"] = True
    debug.debug(f"[verif_sirene] Résultat : {resultat}")
    return resultat