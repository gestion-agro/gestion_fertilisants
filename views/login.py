# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import bcrypt
import traceback
from db import get_connection
import utils.debug as debug

import re

CERTIPHYTO_TYPES = [
    "CON",
    "DESA",
    "DENSA",
    "OPE",
    "MV/V",
]

DROITS = {
    "CON": {
        "catalogue":       True,
        "aide_decision":   True,
        "carnet_lecture":  True,
        "carnet_ecriture": False,
        "carnet_amm_only": False,
        "peut_decider":     True,
    },
    "DESA": {
        "catalogue":       True,
        "aide_decision":   True,
        "carnet_lecture":  True,
        "carnet_ecriture": True,
        "carnet_amm_only": False,
        "peut_decider":     True,
    },
    "DENSA": {
        "catalogue":       True,
        "aide_decision":   True,
        "carnet_lecture":  True,
        "carnet_ecriture": True,
        "carnet_amm_only": False,
        "peut_decider":     True,
    },
    "OPE": {
        "catalogue":       True,
        "aide_decision":   False,
        "carnet_lecture":  True,
        "carnet_ecriture": True,
        "carnet_amm_only": True,
        "peut_decider":     False,
    },
    "MV/V": {
        "catalogue":       False,
        "aide_decision":   False,
        "carnet_lecture":  False,
        "carnet_ecriture": False,
        "carnet_amm_only": False,
        "peut_decider":     False,
    },
    None: {
        "catalogue":       True,
        "aide_decision":   True,
        "carnet_lecture":  True,
        "carnet_ecriture": False,
        "carnet_amm_only": False,
        "peut_decider":     False,
    },
}


def get_droits(user: dict) -> dict:
    if user and user.get("role") == "admin":
        return {k: True for k in DROITS["DESA"]}
    cipp_type = user.get("certiphyto_type") if user else None
    return DROITS.get(cipp_type, DROITS[None])


def peut(user: dict, droit: str) -> bool:
    return get_droits(user).get(droit, False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verifier_cipp(cipp):
    pattern = r"^[A-Z]{2}-\d{4}-\d{6}$"
    return bool(re.match(pattern, cipp))

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def authenticate(username: str, password: str) -> dict | None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        cur.close()
        
        if row and verify_password(password, row["password_hash"]):
            user = dict(row)  # sqlite3.Row -> dict pour pouvoir utiliser .get()
            debug.debug(f"[login] Connexion réussie : {username}")
            return user
        debug.debug(f"[login] Échec connexion : {username}")
        return None
    except Exception as e:
        traceback.print_exc()
        debug.debug(f"[login] Erreur : {e}")
        return None


def create_user(nom, prenom, username, password,
                certiphyto_cipp=None, certiphyto_type=None,
                certiphyto_expiration=None, role="user"):
    if not username or not password:
        return False, "Nom d'utilisateur et mot de passe obligatoires."
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users
                (nom, prenom, username, password_hash,
                 certiphyto_cipp, certiphyto_type, certiphyto_date_expiration, role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nom, prenom, username, hash_password(password),
              certiphyto_cipp or None, certiphyto_type or None,
              certiphyto_expiration or None, role))
        conn.commit()
        cur.close()
        
        debug.debug(f"[login] Utilisateur '{username}' créé")
        return True, ""
    except Exception as e:
        traceback.print_exc()
        msg = str(e)
        if "UNIQUE constraint failed" in msg:
            return False, "Ce nom d'utilisateur est déjà utilisé."
        return False, f"Erreur : {e}"


def count_users() -> int:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        row = cur.fetchone()
        cur.close()
        
        return row[0] if row else 0
    except Exception:
        traceback.print_exc()
        return 0