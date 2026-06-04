# Licensed under PolyForm Noncommercial 1.0.0
# © 2026 Clément THIEULEUX

import sqlite3
import os
from pathlib import Path
import utils.debug as debug

APP_DIR = Path.home() / ".GestionFertilisants"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_FILE = str(APP_DIR / "gestion.db")
debug.debug(f"[DB] Chemin de la base de données : {DB_FILE}")

if not os.path.exists(DB_FILE):
    open(DB_FILE, "w").close()

_TABLES = [
    # ── Entreprise ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS entreprise (
        id                  INTEGER PRIMARY KEY CHECK(id = 1),
        nom                 TEXT(200) NOT NULL DEFAULT '',
        siret               TEXT(14)  DEFAULT NULL,
        adresse             TEXT(300) DEFAULT NULL,
        code_postal         TEXT(10)  DEFAULT NULL,
        ville               TEXT(150) DEFAULT NULL,
        telephone           TEXT(20)  DEFAULT NULL,
        email               TEXT(150) DEFAULT NULL,
        num_tva             TEXT(13)  DEFAULT NULL,
        num_bio             TEXT(50)  DEFAULT NULL,
        organisme_certif    TEXT(100) DEFAULT NULL,
        logo_path           TEXT(300) DEFAULT NULL,
        type_exploitation   TEXT      DEFAULT NULL,
        has_ruches          INTEGER   NOT NULL DEFAULT 0,
        num_napi            TEXT(12)  DEFAULT NULL,
        created_at          DATETIME  DEFAULT CURRENT_TIMESTAMP
    );
    """,
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
        auto_login                  INTEGER   NOT NULL DEFAULT 0,
        is_apiculteur               INTEGER   NOT NULL DEFAULT 0,
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
    # ── Doses par culture ─────────────────────
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
    # type_unite : maraichage | arbo | ruche | jachere | engrais_vert
    """
    CREATE TABLE IF NOT EXISTS parcelles (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        nom                TEXT(150) NOT NULL,
        type_unite         TEXT NOT NULL DEFAULT 'arbo',
        culture            TEXT(150) DEFAULT NULL,
        culture_reelle     TEXT(150) DEFAULT NULL,
        variete            TEXT(150) DEFAULT NULL,
        surface_ha         REAL      DEFAULT NULL,
        longueur_m         REAL      DEFAULT NULL,
        largeur_m          REAL      DEFAULT NULL,
        nb_planches        INTEGER   DEFAULT 1,
        nb_rangs           INTEGER   DEFAULT NULL,
        distance_plants_cm REAL      DEFAULT NULL,
        rendement_m2       REAL      DEFAULT NULL,
        densite_ha         REAL      DEFAULT NULL,
        rendement_ha       REAL      DEFAULT NULL,
        type_sol           TEXT(100) DEFAULT NULL,
        actif              INTEGER   NOT NULL DEFAULT 1,
        jachere            INTEGER   NOT NULL DEFAULT 0,
        melange_nom        TEXT(200) DEFAULT NULL,
        commune            TEXT(150) DEFAULT NULL,
        code_postal_parc   TEXT(5)   DEFAULT NULL,
        notes              TEXT      DEFAULT NULL,
        created_at         DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # ── Variétés engrais vert par parcelle ────
    """
    CREATE TABLE IF NOT EXISTS engrais_vert_varietes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id INTEGER   NOT NULL,
        variete     TEXT(150) NOT NULL,
        taux_pct    REAL      DEFAULT NULL,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
    );
    """,
    # ── Catégories PPP parcelle ───────────────
    """
    CREATE TABLE IF NOT EXISTS parcelle_categories_ppp (
        parcelle_id  INTEGER   NOT NULL,
        culture_ppp  TEXT(150) NOT NULL,
        PRIMARY KEY (parcelle_id, culture_ppp),
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
    );
    """,
    # ── Systèmes d'irrigation ─────────────────
    """
    CREATE TABLE IF NOT EXISTS irrigation_systemes (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id   INTEGER   NOT NULL,
        type_emetteur TEXT CHECK(type_emetteur IN
                          ('goutteur','asperseur','micro-asperseur',
                           'pivot','rampe','autre'))
                                NOT NULL DEFAULT 'goutteur',
        nb_emetteurs  INTEGER   NOT NULL DEFAULT 0,
        debit_lh      REAL      NOT NULL DEFAULT 0,
        description   TEXT(200) DEFAULT NULL,
        actif         INTEGER   NOT NULL DEFAULT 1,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
    );
    """,
    # ── Sessions d'irrigation ─────────────────
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
    # ── Ruches ────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ruches (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        nom               TEXT(150) NOT NULL,
        num_napi          TEXT(12)  DEFAULT NULL,
        parcelle_id       INTEGER   DEFAULT NULL,
        date_installation DATE      DEFAULT NULL,
        race_abeille      TEXT(100) DEFAULT NULL,
        type_ruche        TEXT(50)  DEFAULT NULL,
        actif             INTEGER   NOT NULL DEFAULT 1,
        notes             TEXT      DEFAULT NULL,
        created_at        DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE SET NULL
    );
    """,
    # ── Visites de ruches ─────────────────────
    """
    CREATE TABLE IF NOT EXISTS visites_ruches (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        ruche_id     INTEGER   NOT NULL,
        date_visite  DATE      NOT NULL,
        varroa_pct   REAL      DEFAULT NULL,
        etat_reine   TEXT CHECK(etat_reine IN
                         ('Présente','Absente','À remplacer','Inconnue'))
                               DEFAULT NULL,
        etat_couvain TEXT CHECK(etat_couvain IN
                         ('Bon','Lacunaire','Absent','Anormal'))
                               DEFAULT NULL,
        population   TEXT CHECK(population IN ('Forte','Moyenne','Faible'))
                               DEFAULT NULL,
        notes        TEXT      DEFAULT NULL,
        operateur_id INTEGER   DEFAULT NULL,
        created_at   DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ruche_id)     REFERENCES ruches(id) ON DELETE CASCADE,
        FOREIGN KEY (operateur_id) REFERENCES users(id)  ON DELETE SET NULL
    );
    """,
    # ── Interventions par visite ──────────────
    """
    CREATE TABLE IF NOT EXISTS interventions_ruches (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        visite_id  INTEGER   NOT NULL,
        type       TEXT CHECK(type IN (
                       'varroa','sirop','candi','pollen',
                       'antibiotique','miel','hausse','autre'))
                             NOT NULL,
        produit    TEXT(200) DEFAULT NULL,
        quantite   REAL      DEFAULT NULL,
        unite      TEXT(20)  DEFAULT NULL,
        notes      TEXT      DEFAULT NULL,
        created_at DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (visite_id) REFERENCES visites_ruches(id) ON DELETE CASCADE
    );
    """,
    # ── PPP Produits ──────────────────────────
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
    # ── PPP Usages ────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ppp_usages (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id      INTEGER   NOT NULL,
        culture         TEXT(150) NOT NULL,
        bio_agresseur   TEXT(200) DEFAULT 'Non précisé',
        dose            REAL      DEFAULT NULL,
        dose_unite      TEXT(50)  DEFAULT NULL,
        dar             INTEGER   DEFAULT NULL,
        nma             INTEGER   DEFAULT NULL,
        stade_min       TEXT(20)  DEFAULT NULL,
        stade_max       TEXT(20)  DEFAULT NULL,
        znt_eau         INTEGER   DEFAULT NULL,
        znt_arthropodes INTEGER   DEFAULT NULL,
        znt_plantes     INTEGER   DEFAULT NULL,
        condition_usage TEXT      DEFAULT NULL,
        mode            TEXT CHECK(mode IN ('bio','conventionnel','les deux'))
                                  NOT NULL DEFAULT 'conventionnel',
        FOREIGN KEY (produit_id) REFERENCES ppp_produits(id) ON DELETE CASCADE
    );
    """,
    # ── PPP Décisions ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS ppp_decisions (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        decideur_id    INTEGER   NOT NULL,
        produit_id     INTEGER   NOT NULL,
        usage_id       INTEGER   DEFAULT NULL,
        parcelle_id    INTEGER   DEFAULT NULL,
        culture        TEXT(150) NOT NULL,
        bio_agresseur  TEXT(200) DEFAULT NULL,
        dose_prescrite REAL      NOT NULL,
        unite          TEXT(20)  DEFAULT 'L/ha',
        date_prevue    DATE      DEFAULT NULL,
        statut         TEXT CHECK(statut IN
                           ('en_attente','en_cours','fait','annule'))
                                 NOT NULL DEFAULT 'en_attente',
        notes_decideur TEXT      DEFAULT NULL,
        created_at     DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (decideur_id) REFERENCES users(id)        ON DELETE RESTRICT,
        FOREIGN KEY (produit_id)  REFERENCES ppp_produits(id) ON DELETE RESTRICT,
        FOREIGN KEY (usage_id)    REFERENCES ppp_usages(id)   ON DELETE SET NULL,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id)    ON DELETE SET NULL
    );
    """,
    # ── PPP Traitements ───────────────────────
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
    "CREATE INDEX IF NOT EXISTS idx_cat_ppp_parcelle  ON parcelle_categories_ppp(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_ruches_parcelle   ON ruches(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_visites_ruche     ON visites_ruches(ruche_id);",
    "CREATE INDEX IF NOT EXISTS idx_visites_date      ON visites_ruches(date_visite);",
    "CREATE INDEX IF NOT EXISTS idx_interv_visite     ON interventions_ruches(visite_id);",
    "CREATE INDEX IF NOT EXISTS idx_ev_parcelle       ON engrais_vert_varietes(parcelle_id);",
]

# ── Migrations automatiques ───────────────────
_MIGRATIONS = {
    "entreprise": [
        ("type_exploitation", "TEXT DEFAULT NULL"),
        ("has_ruches",        "INTEGER NOT NULL DEFAULT 0"),
        ("num_napi",          "TEXT(12) DEFAULT NULL"),
    ],
    "users": [
        ("auto_login",    "INTEGER NOT NULL DEFAULT 0"),
        ("is_apiculteur", "INTEGER NOT NULL DEFAULT 0"),
        ("date_embauche", "DATE DEFAULT NULL"),
        ("telephone",     "TEXT(20) DEFAULT NULL"),
    ],
    "parcelles": [
        ("culture_reelle",      "TEXT DEFAULT NULL"),
        ("variete",             "TEXT DEFAULT NULL"),
        ("rendement_ha",        "REAL DEFAULT NULL"),
        ("densite_ha",          "REAL DEFAULT NULL"),
        ("nb_rangs",            "INTEGER DEFAULT NULL"),
        ("nb_planches",         "INTEGER DEFAULT 1"),
        ("distance_plants_cm",  "REAL DEFAULT NULL"),
        ("rendement_m2",        "REAL DEFAULT NULL"),
        ("jachere",             "INTEGER NOT NULL DEFAULT 0"),
        ("melange_nom",         "TEXT(200) DEFAULT NULL"),
        ("commune",             "TEXT(150) DEFAULT NULL"),
        ("code_postal_parc",    "TEXT(5) DEFAULT NULL"),
    ],
}

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
        debug.debug(f"[DB] Erreur connexion : {e}")
        raise


def _migrer_colonnes(cur, table: str, colonnes: list):
    cur.execute(f"PRAGMA table_info({table})")
    existantes = {row[1] for row in cur.fetchall()}
    for nom, definition in colonnes:
        if nom not in existantes:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {definition}")
            debug.debug(f"[migration] {table}.{nom} ajouté")


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    for ddl in _TABLES:
        cur.execute(ddl)
    for idx in _INDEXES:
        cur.execute(idx)
    for table, colonnes in _MIGRATIONS.items():
        _migrer_colonnes(cur, table, colonnes)
    conn.commit()
    debug.debug("[DB] Initialisation + migrations terminées.")


# ── Helpers ───────────────────────────────────
def is_first_launch() -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        users = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM entreprise")
        ent = cur.fetchone()[0]
        cur.close()
        return users == 0 and ent == 0
    except Exception:
        return True


def get_entreprise() -> dict:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM entreprise WHERE id = 1")
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else {}
    except Exception:
        return {}


def get_auto_login_user() -> dict | None:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE auto_login = 1 AND actif = 1 LIMIT 1")
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    except Exception:
        return None


def get_categories_ppp_parcelle(parcelle_id: int) -> list:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT culture_ppp FROM parcelle_categories_ppp "
            "WHERE parcelle_id = ? ORDER BY culture_ppp", (parcelle_id,))
        cats = [row[0] for row in cur.fetchall()]
        cur.close()
        return cats
    except Exception:
        return []


def set_categories_ppp_parcelle(parcelle_id: int, categories: list):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM parcelle_categories_ppp WHERE parcelle_id = ?",
            (parcelle_id,))
        for cat in categories:
            if cat.strip():
                cur.execute(
                    "INSERT OR IGNORE INTO parcelle_categories_ppp "
                    "(parcelle_id, culture_ppp) VALUES (?, ?)",
                    (parcelle_id, cat.strip()))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_categories_ppp : {e}")


def produit_homologue_pour_parcelle(produit_id: int, parcelle_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM parcelle_categories_ppp pcp
            JOIN ppp_usages u ON u.culture = pcp.culture_ppp
            WHERE pcp.parcelle_id = ? AND u.produit_id = ?
        """, (parcelle_id, produit_id))
        count = cur.fetchone()[0]
        cur.close()
        return count > 0
    except Exception:
        return False


def peut_supprimer_ruche(user: dict) -> bool:
    """Admin ou utilisateur marqué apiculteur."""
    return user.get("role") == "admin" or bool(user.get("is_apiculteur"))


def get_engrais_vert_varietes(parcelle_id: int) -> list:
    """Retourne les variétés d'engrais vert d'une parcelle."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, variete, taux_pct FROM engrais_vert_varietes "
            "WHERE parcelle_id = ? ORDER BY id", (parcelle_id,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception:
        return []


def set_engrais_vert_varietes(parcelle_id: int, varietes: list):
    """Remplace les variétés d'engrais vert d'une parcelle.
    varietes = [{"variete": str, "taux_pct": float|None}, ...]
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM engrais_vert_varietes WHERE parcelle_id = ?",
            (parcelle_id,))
        for v in varietes:
            nom = v.get("variete", "").strip()
            if nom:
                cur.execute(
                    "INSERT INTO engrais_vert_varietes "
                    "(parcelle_id, variete, taux_pct) VALUES (?, ?, ?)",
                    (parcelle_id, nom, v.get("taux_pct")))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_engrais_vert_varietes : {e}")