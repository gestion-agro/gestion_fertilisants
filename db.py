# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import sqlite3
import os
import sys
from pathlib import Path
import utils.debug as debug

# BDD persistante dans le profil utilisateur
# Linux/Mac : ~/.GestionFertilisants/gestion.db
# Windows    : C:\Users\<user>\.GestionFertilisants\gestion.db
# Le chemin est indépendant de l'endroit ou est l'exe est installé

APP_DIR  = Path.home() / ".GestionFertilisants"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = str(APP_DIR / "gestion.db")
debug.debug(f"[DB] Chemin de la base de données : {DB_FILE}")


if not os.path.exists(DB_FILE):
    debug.debug(f"[DB] Base de données non trouvée, création du fichier {DB_FILE}")
    open(DB_FILE, "w").close()

_TABLES = [
    # ── Utilisateurs ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        nom                         TEXT(100) NOT NULL,
        prenom                      TEXT(100) NOT NULL,
        username                    TEXT(50)  NOT NULL UNIQUE,
        password_hash               TEXT(255) NOT NULL,
        certiphyto_cipp             TEXT(50)  DEFAULT NULL,
        certiphyto_type             TEXT CHECK(
            certiphyto_type IN ('CON','DESA','DENSA','OPE','MV/V')
        ) DEFAULT NULL,
        certiphyto_date_expiration  DATE      DEFAULT NULL,
        role                        TEXT CHECK(role IN ('admin','user'))
                                              NOT NULL DEFAULT 'user',
        actif                       INTEGER   NOT NULL DEFAULT 1,
        telephone                   TEXT(20)  DEFAULT NULL,
        date_embauche               DATE      DEFAULT NULL,
        created_at                  DATETIME  DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── Cultures ──────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS cultures (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        nom        TEXT(150) NOT NULL UNIQUE,
        besoin_n   REAL      NOT NULL DEFAULT 0,
        besoin_p   REAL      NOT NULL DEFAULT 0,
        besoin_k   REAL      NOT NULL DEFAULT 0,
        surface    REAL      NOT NULL DEFAULT 10000,
        created_at DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── Fertilisants ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS fertilisants (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        nom             TEXT(150) NOT NULL UNIQUE,
        n               REAL      NOT NULL DEFAULT 0,
        p               REAL      NOT NULL DEFAULT 0,
        k               REAL      NOT NULL DEFAULT 0,
        conditionnement REAL      NOT NULL DEFAULT 25,
        unite           TEXT(10)  NOT NULL DEFAULT 'kg',
        prix            REAL      NOT NULL DEFAULT 0,
        stock           REAL      NOT NULL DEFAULT 0,
        created_at      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── Doses enregistrées par culture ────────
    """
    CREATE TABLE IF NOT EXISTS doses_culture (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        culture_id     INTEGER NOT NULL,
        fertilisant_id INTEGER NOT NULL,
        dose_kg_ha     REAL    NOT NULL DEFAULT 0,
        updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (culture_id)     REFERENCES cultures(id)     ON DELETE CASCADE,
        FOREIGN KEY (fertilisant_id) REFERENCES fertilisants(id) ON DELETE CASCADE,
        UNIQUE(culture_id, fertilisant_id)
    );
    """,

    # ── Parcelles ─────────────────────────────
    # type_unite : 'parcelle' (arbo/grandes cultures) ou 'planche' (maraîchage)
    # Pour les parcelles : surface_ha renseignée directement
    # Pour les planches  : longueur_m × largeur_m → surface calculée à l'affichage
    """
    CREATE TABLE IF NOT EXISTS parcelles (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        nom          TEXT(150) NOT NULL,
        type_unite   TEXT CHECK(type_unite IN ('parcelle','planche'))
                               NOT NULL DEFAULT 'parcelle',
        culture      TEXT(150) DEFAULT NULL,
        surface_ha   REAL      DEFAULT NULL,
        longueur_m   REAL      DEFAULT NULL,
        largeur_m    REAL      DEFAULT NULL,
        type_sol     TEXT(100) DEFAULT NULL,
        actif        INTEGER   NOT NULL DEFAULT 1,
        notes        TEXT      DEFAULT NULL,
        created_at   DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── Systèmes d'irrigation par parcelle ────
    # Une parcelle peut avoir plusieurs systèmes (goutteurs + asperseurs)
    """
    CREATE TABLE IF NOT EXISTS irrigation_systemes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id     INTEGER   NOT NULL,
        type_emetteur   TEXT CHECK(type_emetteur IN
                            ('goutteur','asperseur','micro-asperseur',
                             'pivot','rampe','autre'))
                                  NOT NULL DEFAULT 'goutteur',
        nb_emetteurs    INTEGER   NOT NULL DEFAULT 0,
        debit_lh        REAL      NOT NULL DEFAULT 0,
        description     TEXT(200) DEFAULT NULL,
        actif           INTEGER   NOT NULL DEFAULT 1,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
    );
    """,

    # ── Sessions d'irrigation ─────────────────
    # Chaque ligne = une session sur un système donné
    # Volume calculé = (duree_min / 60) × nb_emetteurs × debit_lh
    """
    CREATE TABLE IF NOT EXISTS irrigations (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id      INTEGER   NOT NULL,
        systeme_id       INTEGER   NOT NULL,
        user_id          INTEGER   NOT NULL,
        date_heure       DATETIME  NOT NULL,
        duree_min        INTEGER   NOT NULL DEFAULT 0,
        volume_calcule_l REAL      DEFAULT NULL,
        notes            TEXT      DEFAULT NULL,
        created_at       DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)           ON DELETE RESTRICT,
        FOREIGN KEY (systeme_id)  REFERENCES irrigation_systemes(id) ON DELETE RESTRICT,
        FOREIGN KEY (user_id)     REFERENCES users(id)               ON DELETE RESTRICT
    );
    """,

    # ── Produits phytosanitaires ───────────────
    """
    CREATE TABLE IF NOT EXISTS ppp_produits (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_commercial    TEXT(200) NOT NULL,
        num_amm           TEXT(50)  DEFAULT NULL UNIQUE,
        substance_active  TEXT      DEFAULT NULL,
        bio_compatible    INTEGER   NOT NULL DEFAULT 0,
        unite_dose        TEXT(20)  DEFAULT 'L/ha',
        conditions_emploi TEXT      DEFAULT NULL,
        created_at        DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,

    # ── Usages homologués ──────────────────────
    """
    CREATE TABLE IF NOT EXISTS ppp_usages (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id       INTEGER   NOT NULL,
        culture          TEXT(150) NOT NULL,
        bio_agresseur    TEXT(200) DEFAULT 'Non précisé',
        dose             REAL      DEFAULT NULL,
        dose_unite       TEXT(50)  DEFAULT NULL,
        dar              INTEGER   DEFAULT NULL,
        nma              INTEGER   DEFAULT NULL,
        stade_min        TEXT(20)  DEFAULT NULL,
        stade_max        TEXT(20)  DEFAULT NULL,
        znt_eau          INTEGER   DEFAULT NULL,
        znt_arthropodes  INTEGER   DEFAULT NULL,
        znt_plantes      INTEGER   DEFAULT NULL,
        condition_usage  TEXT      DEFAULT NULL,
        mode             TEXT CHECK(mode IN ('bio','conventionnel','les deux'))
                                   NOT NULL DEFAULT 'conventionnel',
        FOREIGN KEY (produit_id) REFERENCES ppp_produits(id) ON DELETE CASCADE
    );
    """,

    # ── Décisions de traitement ───────────────
    # Créées par CON/DESA/DENSA, exécutées par OPE ou eux-mêmes
    """
    CREATE TABLE IF NOT EXISTS ppp_decisions (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        decideur_id     INTEGER   NOT NULL,
        produit_id      INTEGER   NOT NULL,
        usage_id        INTEGER   DEFAULT NULL,
        parcelle_id     INTEGER   DEFAULT NULL,
        culture         TEXT(150) NOT NULL,
        bio_agresseur   TEXT(200) DEFAULT NULL,
        dose_prescrite  REAL      NOT NULL,
        unite           TEXT(20)  DEFAULT 'L/ha',
        date_prevue     DATE      DEFAULT NULL,
        statut          TEXT CHECK(statut IN
                            ('en_attente','en_cours','fait','annule'))
                                  NOT NULL DEFAULT 'en_attente',
        notes_decideur  TEXT      DEFAULT NULL,
        created_at      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decideur_id) REFERENCES users(id)        ON DELETE RESTRICT,
        FOREIGN KEY (produit_id)  REFERENCES ppp_produits(id) ON DELETE RESTRICT,
        FOREIGN KEY (usage_id)    REFERENCES ppp_usages(id)   ON DELETE SET NULL,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)    ON DELETE SET NULL
    );
    """,

    # ── Carnet de traitements ─────────────────
    # Lié à une décision (obligatoire pour OPE, optionnel pour CON/DESA/DENSA)
    """
    CREATE TABLE IF NOT EXISTS ppp_traitements (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id        INTEGER   DEFAULT NULL,
        operateur_id       INTEGER   NOT NULL,
        parcelle_id        INTEGER   DEFAULT NULL,
        produit_id         INTEGER   NOT NULL,
        culture            TEXT(150) NOT NULL,
        bio_agresseur      TEXT(200) DEFAULT NULL,
        dose_appliquee     REAL      NOT NULL,
        unite              TEXT(20)  DEFAULT 'L/ha',
        surface_traitee_ha REAL      DEFAULT NULL,
        date_traitement    DATE      NOT NULL,
        meteo_temperature  REAL      DEFAULT NULL,
        meteo_vent         TEXT CHECK(meteo_vent IN
                               ('Calme','Faible','Modéré','Fort'))
                               DEFAULT NULL,
        meteo_nebulosite   TEXT CHECK(meteo_nebulosite IN
                               ('Dégagé','Peu nuageux','Nuageux','Couvert'))
                               DEFAULT NULL,
        epi_utilises       INTEGER   NOT NULL DEFAULT 0,
        signature_nom      TEXT(150) DEFAULT NULL,
        signature_date     DATE      DEFAULT NULL,
        signature_dessin   BLOB      DEFAULT NULL,
        notes              TEXT      DEFAULT NULL,
        created_at         DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decision_id)  REFERENCES ppp_decisions(id)  ON DELETE SET NULL,
        FOREIGN KEY (operateur_id) REFERENCES users(id)          ON DELETE RESTRICT,
        FOREIGN KEY (parcelle_id)  REFERENCES parcelles(id)      ON DELETE SET NULL,
        FOREIGN KEY (produit_id)   REFERENCES ppp_produits(id)   ON DELETE RESTRICT
    );
    """,
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_usages_produit    ON ppp_usages(produit_id);",
    "CREATE INDEX IF NOT EXISTS idx_usages_culture    ON ppp_usages(culture);",
    "CREATE INDEX IF NOT EXISTS idx_usages_bio_agr    ON ppp_usages(bio_agresseur);",
    "CREATE INDEX IF NOT EXISTS idx_produits_nom      ON ppp_produits(nom_commercial);",
    "CREATE INDEX IF NOT EXISTS idx_irrigations_parc  ON irrigations(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_irrigations_date  ON irrigations(date_heure);",
    "CREATE INDEX IF NOT EXISTS idx_decisions_statut  ON ppp_decisions(statut);",
    "CREATE INDEX IF NOT EXISTS idx_traitements_date  ON ppp_traitements(date_traitement);",
    "CREATE INDEX IF NOT EXISTS idx_traitements_ope   ON ppp_traitements(operateur_id);",
]

_conn = None

def get_connection():
    global _conn
    try:
        if _conn is None:
            _conn = sqlite3.connect(DB_FILE)
            _conn.row_factory = sqlite3.Row
            _conn.execute("PRAGMA foreign_keys = ON;")
            _conn.execute("PRAGMA journal_mode = WAL;")
            debug.debug("[DB] Connexion SQLite établie.")
        return _conn
    except Exception as e:
        debug.debug(f"[DB] Erreur de connexion : {e}")
        raise


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    for ddl in _TABLES:
        cur.execute(ddl)
    for idx in _INDEXES:
        cur.execute(idx)
    conn.commit()
    debug.debug("[DB] Initialisation terminée.")