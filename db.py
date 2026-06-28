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

MODULES = [
    "fertilisants", "ppp_catalogue", "ppp_carnet",
    "entreprise", "parcelles", "irrigation", "ruches", "admin",
]

DEFAUTS_PERMISSIONS = {
    "admin": {m: {"lecture": 1, "ecriture": 1, "suppression": 1} for m in MODULES},
    "user":  {m: {"lecture": 1, "ecriture": 0, "suppression": 0} for m in MODULES},
    "apiculteur": {
        **{m: {"lecture": 1, "ecriture": 0, "suppression": 0} for m in MODULES},
        "ruches": {"lecture": 1, "ecriture": 1, "suppression": 1},
    },
}

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
    # ── Paramètres application ────────────────
    """
    CREATE TABLE IF NOT EXISTS parametres_app (
        id                      INTEGER PRIMARY KEY CHECK(id = 1),
        largeur_planche_defaut  REAL NOT NULL DEFAULT 1.20,
        passe_pied_defaut       REAL NOT NULL DEFAULT 0.40,
        tolerance_npk_pct       REAL NOT NULL DEFAULT 2.0
    );
    """,
    # ── Utilisateurs ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        id                          INTEGER PRIMARY KEY AUTOINCREMENT,
        nom                         TEXT(100) NOT NULL,
        prenom                      TEXT(100) NOT NULL,
        username                    TEXT(50)  NOT NULL UNIQUE,
        password_hash               TEXT(255) NOT NULL DEFAULT '',
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
        first_login                 INTEGER   NOT NULL DEFAULT 0,
        created_at                  DATETIME  DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # ── Permissions utilisateurs ──────────────
    """
    CREATE TABLE IF NOT EXISTS user_permissions (
        user_id     INTEGER NOT NULL,
        module      TEXT    NOT NULL,
        lecture     INTEGER NOT NULL DEFAULT 1,
        ecriture    INTEGER NOT NULL DEFAULT 0,
        suppression INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (user_id, module),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    # ── Cultures (référentiel fertilisation) ──
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
    # ── PARCELLES (surface uniquement) ────────
    """
    CREATE TABLE IF NOT EXISTS parcelles (
        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
        nom                TEXT(150) NOT NULL,
        type_sol           TEXT(100) DEFAULT NULL,
        surface_ha         REAL      DEFAULT NULL,
        has_ruches         INTEGER   NOT NULL DEFAULT 0,
        commune            TEXT(150) DEFAULT NULL,
        code_postal_parc   TEXT(5)   DEFAULT NULL,
        actif              INTEGER   NOT NULL DEFAULT 1,
        notes              TEXT      DEFAULT NULL,
        created_at         DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """,
    # ── CULTURES_PARCELLE ──────────────────────
    # categorie : maraichage | arbo | jachere | engrais_vert
    """
    CREATE TABLE IF NOT EXISTS cultures_parcelle (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        parcelle_id         INTEGER   NOT NULL,
        categorie           TEXT CHECK(categorie IN
                                ('maraichage','arbo','jachere','engrais_vert'))
                                      NOT NULL DEFAULT 'maraichage',
        espece              TEXT(150) DEFAULT NULL,
        variete             TEXT(150) DEFAULT NULL,

        -- communs maraîchage / arbo
        nb_rangs            INTEGER   DEFAULT NULL,
        distance_rangs      REAL      DEFAULT NULL,   -- cm (maraîchage) ou m (arbo)
        distance_plants     REAL      DEFAULT NULL,   -- cm (maraîchage) ou m (arbo, = entre arbres)

        -- maraîchage uniquement
        largeur_planche     REAL      DEFAULT NULL,   -- m
        longueur_planche    REAL      DEFAULT NULL,   -- m (saisie manuelle)
        nb_planches         INTEGER   DEFAULT NULL,   -- saisie manuelle
        passe_pied          REAL      DEFAULT NULL,   -- m
        rendement_ml        REAL      DEFAULT NULL,   -- kg/m linéaire
        prix_moyen_kg        REAL      DEFAULT NULL,   -- €/kg

        -- arbo uniquement
        rendement_ha        REAL      DEFAULT NULL,   -- t/ha
        prix_moyen_tonne     REAL      DEFAULT NULL,   -- €/t

        -- engrais vert
        melange_nom         TEXT(200) DEFAULT NULL,

        densite_calculee    REAL      DEFAULT NULL,   -- plants ou arbres /ha
        surface_occupee_m2  REAL      DEFAULT NULL,
        culture_ephy        TEXT(150) DEFAULT NULL,
        notes               TEXT      DEFAULT NULL,
        actif               INTEGER   NOT NULL DEFAULT 1,
        created_at          DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
    );
    """,
    # ── Variétés engrais vert ─────────────────
    """
    CREATE TABLE IF NOT EXISTS engrais_vert_varietes (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        culture_parcelle_id INTEGER   NOT NULL,
        variete             TEXT(150) NOT NULL,
        taux_pct            REAL      DEFAULT NULL,
        FOREIGN KEY (culture_parcelle_id) REFERENCES cultures_parcelle(id) ON DELETE CASCADE
    );
    """,
    # ── Catégories PPP (liées à culture_parcelle) ──
    """
    CREATE TABLE IF NOT EXISTS parcelle_categories_ppp (
        culture_parcelle_id INTEGER   NOT NULL,
        culture_ppp         TEXT(150) NOT NULL,
        PRIMARY KEY (culture_parcelle_id, culture_ppp),
        FOREIGN KEY (culture_parcelle_id) REFERENCES cultures_parcelle(id) ON DELETE CASCADE
    );
    """,
    # ── Systèmes d'irrigation (liés à la PARCELLE) ──
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
    # ── Liaison système irrigation ↔ cultures (N↔N) ──
    # Un système peut couvrir plusieurs cultures (ex: un asperseur pour 2 planches voisines)
    """
    CREATE TABLE IF NOT EXISTS irrigation_systeme_cultures (
        systeme_id          INTEGER NOT NULL,
        culture_parcelle_id INTEGER NOT NULL,
        PRIMARY KEY (systeme_id, culture_parcelle_id),
        FOREIGN KEY (systeme_id)          REFERENCES irrigation_systemes(id) ON DELETE CASCADE,
        FOREIGN KEY (culture_parcelle_id) REFERENCES cultures_parcelle(id)   ON DELETE CASCADE
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
    "CREATE INDEX IF NOT EXISTS idx_cat_ppp_cult      ON parcelle_categories_ppp(culture_parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_ruches_parcelle   ON ruches(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_visites_ruche     ON visites_ruches(ruche_id);",
    "CREATE INDEX IF NOT EXISTS idx_visites_date      ON visites_ruches(date_visite);",
    "CREATE INDEX IF NOT EXISTS idx_interv_visite     ON interventions_ruches(visite_id);",
    "CREATE INDEX IF NOT EXISTS idx_ev_culture        ON engrais_vert_varietes(culture_parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_permissions_user  ON user_permissions(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_cultures_parcelle ON cultures_parcelle(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_irrsysc_sys       ON irrigation_systeme_cultures(systeme_id);",
    "CREATE INDEX IF NOT EXISTS idx_irrsysc_cult      ON irrigation_systeme_cultures(culture_parcelle_id);",
]

_MIGRATIONS = {
    "entreprise": [
        ("type_exploitation", "TEXT DEFAULT NULL"),
        ("has_ruches",        "INTEGER NOT NULL DEFAULT 0"),
        ("num_napi",          "TEXT(12) DEFAULT NULL"),
    ],
    "users": [
        ("auto_login",    "INTEGER NOT NULL DEFAULT 0"),
        ("is_apiculteur", "INTEGER NOT NULL DEFAULT 0"),
        ("first_login",   "INTEGER NOT NULL DEFAULT 0"),
        ("date_embauche", "DATE DEFAULT NULL"),
        ("telephone",     "TEXT(20) DEFAULT NULL"),
    ],
    "parametres_app": [
        ("tolerance_npk_pct", "REAL NOT NULL DEFAULT 2.0"),
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


def _migrer_v2_cultures_parcelle(cur):
    """
    Migration v2 : ancien modèle cultures_parcelle (type normale/jachere/
    engrais_vert avec distance_plants_cm générique, rendement_m2/ha mélangés)
    vers le nouveau modèle avec categorie maraichage/arbo distincts et
    champs spécifiques par catégorie.

    Détectée par l'absence de la colonne 'categorie' (le nouveau schéma
    l'a, l'ancien avait 'type').
    """
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cultures_parcelle'")
    if not cur.fetchone():
        return  # table neuve, rien à migrer

    cur.execute("PRAGMA table_info(cultures_parcelle)")
    colonnes = {row[1] for row in cur.fetchall()}

    if "categorie" in colonnes:
        return  # déjà au nouveau format

    if "type" not in colonnes:
        return  # schéma inattendu, on n'y touche pas

    debug.debug("[migration v2] Ancien modèle cultures_parcelle détecté — migration...")

    cur.execute("""
        SELECT id, parcelle_id, type, espece, variete, nb_rangs,
               distance_rangs_cm, distance_plants_cm, largeur_planche,
               passe_pied, nb_planches, densite_calculee, rendement_m2,
               rendement_ha, culture_ephy, prix_moyen_vente, melange_nom,
               surface_occupee_m2, notes, actif
        FROM cultures_parcelle
    """)
    anciennes = [dict(r) for r in cur.fetchall()]

    cur.execute("ALTER TABLE cultures_parcelle RENAME TO cultures_parcelle_old_v2")

    cur.execute("""
        CREATE TABLE cultures_parcelle (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            parcelle_id         INTEGER   NOT NULL,
            categorie           TEXT NOT NULL DEFAULT 'maraichage',
            espece              TEXT(150) DEFAULT NULL,
            variete             TEXT(150) DEFAULT NULL,
            nb_rangs            INTEGER   DEFAULT NULL,
            distance_rangs      REAL      DEFAULT NULL,
            distance_plants     REAL      DEFAULT NULL,
            largeur_planche     REAL      DEFAULT NULL,
            longueur_planche    REAL      DEFAULT NULL,
            nb_planches         INTEGER   DEFAULT NULL,
            passe_pied          REAL      DEFAULT NULL,
            rendement_ml        REAL      DEFAULT NULL,
            prix_moyen_kg       REAL      DEFAULT NULL,
            rendement_ha        REAL      DEFAULT NULL,
            prix_moyen_tonne    REAL      DEFAULT NULL,
            melange_nom         TEXT(200) DEFAULT NULL,
            densite_calculee    REAL      DEFAULT NULL,
            surface_occupee_m2  REAL      DEFAULT NULL,
            culture_ephy        TEXT(150) DEFAULT NULL,
            notes               TEXT      DEFAULT NULL,
            actif               INTEGER   NOT NULL DEFAULT 1,
            created_at          DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (parcelle_id) REFERENCES parcelles(id) ON DELETE CASCADE
        );
    """)

    mapping_old_new = {}
    for c in anciennes:
        old_id = c["id"]
        old_type = c.get("type")
        # Ancien 'normale' devient 'maraichage' par défaut (c'était le seul
        # type concret géré avec planches dans l'ancien modèle)
        categorie = old_type if old_type in ("jachere", "engrais_vert") else "maraichage"

        cur.execute("""
            INSERT INTO cultures_parcelle (
                parcelle_id, categorie, espece, variete, nb_rangs,
                distance_rangs, distance_plants, largeur_planche,
                longueur_planche, nb_planches, passe_pied,
                rendement_ml, prix_moyen_kg, rendement_ha,
                melange_nom, densite_calculee, surface_occupee_m2,
                culture_ephy, notes, actif
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            c["parcelle_id"], categorie, c.get("espece"), c.get("variete"),
            c.get("nb_rangs"), c.get("distance_rangs_cm"), c.get("distance_plants_cm"),
            c.get("largeur_planche"), None, c.get("nb_planches"), c.get("passe_pied"),
            c.get("rendement_m2"), c.get("prix_moyen_vente"), c.get("rendement_ha"),
            c.get("melange_nom"), c.get("densite_calculee"), c.get("surface_occupee_m2"),
            c.get("culture_ephy"), c.get("notes"), c.get("actif", 1),
        ))
        mapping_old_new[old_id] = cur.lastrowid

    # Repointer engrais_vert_varietes et parcelle_categories_ppp
    cur.execute("SELECT id, culture_parcelle_id, variete, taux_pct FROM engrais_vert_varietes")
    anciennes_ev = cur.fetchall()
    cur.execute("DELETE FROM engrais_vert_varietes")
    for ev_id, old_cid, variete, taux in anciennes_ev:
        new_cid = mapping_old_new.get(old_cid)
        if new_cid:
            cur.execute("""
                INSERT INTO engrais_vert_varietes
                (culture_parcelle_id, variete, taux_pct) VALUES (?, ?, ?)
            """, (new_cid, variete, taux))

    cur.execute("SELECT culture_parcelle_id, culture_ppp FROM parcelle_categories_ppp")
    anciennes_ppp = cur.fetchall()
    cur.execute("DELETE FROM parcelle_categories_ppp")
    for old_cid, cat in anciennes_ppp:
        new_cid = mapping_old_new.get(old_cid)
        if new_cid:
            cur.execute("""
                INSERT OR IGNORE INTO parcelle_categories_ppp
                (culture_parcelle_id, culture_ppp) VALUES (?, ?)
            """, (new_cid, cat))

    cur.execute("DROP TABLE IF EXISTS cultures_parcelle_old_v2")
    debug.debug(f"[migration v2] {len(anciennes)} culture(s) migrée(s) vers le nouveau modèle.")


def _migrer_v2_parcelles_dimensions(cur):
    """
    Retire longueur_m/largeur_m de parcelles (remplacés par surface_ha
    uniquement). Si une parcelle avait L×l mais pas de surface_ha,
    calcule la surface équivalente avant de droper les colonnes.
    """
    cur.execute("PRAGMA table_info(parcelles)")
    colonnes = {row[1] for row in cur.fetchall()}
    if "longueur_m" not in colonnes:
        return  # déjà migré

    debug.debug("[migration v2] Retrait dimensions L×l des parcelles...")

    cur.execute("SELECT id, longueur_m, largeur_m, surface_ha FROM parcelles")
    rows = cur.fetchall()
    for pid, longueur, largeur, surface_ha in rows:
        if not surface_ha and longueur and largeur:
            nouvelle_surface = (longueur * largeur) / 10000  # m² -> ha
            cur.execute("UPDATE parcelles SET surface_ha=? WHERE id=?",
                        (nouvelle_surface, pid))

    cur.execute("PRAGMA foreign_keys = OFF;")
    cur.execute("ALTER TABLE parcelles RENAME TO parcelles_old_v2")
    cur.execute("""
        CREATE TABLE parcelles (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            nom                TEXT(150) NOT NULL,
            type_sol           TEXT(100) DEFAULT NULL,
            surface_ha         REAL      DEFAULT NULL,
            has_ruches         INTEGER   NOT NULL DEFAULT 0,
            commune            TEXT(150) DEFAULT NULL,
            code_postal_parc   TEXT(5)   DEFAULT NULL,
            actif              INTEGER   NOT NULL DEFAULT 1,
            notes              TEXT      DEFAULT NULL,
            created_at         DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        INSERT INTO parcelles
        (id, nom, type_sol, surface_ha, has_ruches, commune,
         code_postal_parc, actif, notes, created_at)
        SELECT id, nom, type_sol, surface_ha, has_ruches, commune,
               code_postal_parc, actif, notes, created_at
        FROM parcelles_old_v2
    """)
    cur.execute("DROP TABLE IF EXISTS parcelles_old_v2")
    cur.execute("PRAGMA foreign_keys = ON;")
    debug.debug(f"[migration v2] {len(rows)} parcelle(s) — dimensions retirées.")


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cultures_parcelle'")
    if cur.fetchone():
        cur.execute("PRAGMA foreign_keys = OFF;")
        _migrer_v2_cultures_parcelle(cur)
        _migrer_v2_parcelles_dimensions(cur)
        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON;")

    for ddl in _TABLES:
        cur.execute(ddl)
    for idx in _INDEXES:
        cur.execute(idx)
    for table, colonnes in _MIGRATIONS.items():
        _migrer_colonnes(cur, table, colonnes)

    init_carnet_fertilisation(cur)

    cur.execute("SELECT COUNT(*) FROM parametres_app")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO parametres_app (id) VALUES (1)")

    conn.commit()
    debug.debug("[DB] Initialisation + migrations terminées.")


# ── Helpers généraux ──────────────────────────
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


def get_parametres_app() -> dict:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM parametres_app WHERE id=1")
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else {
            "largeur_planche_defaut": 1.20, "passe_pied_defaut": 0.40,
            "tolerance_npk_pct": 2.0}
    except Exception:
        return {"largeur_planche_defaut": 1.20, "passe_pied_defaut": 0.40,
                "tolerance_npk_pct": 2.0}


def set_parametres_app(largeur_planche: float, passe_pied: float,
                        tolerance_npk_pct: float = None):
    try:
        conn = get_connection()
        cur = conn.cursor()
        if tolerance_npk_pct is not None:
            cur.execute("""
                UPDATE parametres_app
                SET largeur_planche_defaut=?, passe_pied_defaut=?,
                    tolerance_npk_pct=?
                WHERE id=1
            """, (largeur_planche, passe_pied, tolerance_npk_pct))
        else:
            cur.execute("""
                UPDATE parametres_app
                SET largeur_planche_defaut=?, passe_pied_defaut=?
                WHERE id=1
            """, (largeur_planche, passe_pied))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_parametres_app : {e}")


# ── Helpers PPP (liées à culture_parcelle) ────
def get_categories_ppp_culture(culture_parcelle_id: int) -> list:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT culture_ppp FROM parcelle_categories_ppp "
            "WHERE culture_parcelle_id = ? ORDER BY culture_ppp",
            (culture_parcelle_id,))
        cats = [row[0] for row in cur.fetchall()]
        cur.close()
        return cats
    except Exception:
        return []


def set_categories_ppp_culture(culture_parcelle_id: int, categories: list):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM parcelle_categories_ppp WHERE culture_parcelle_id = ?",
            (culture_parcelle_id,))
        for cat in categories:
            if cat.strip():
                cur.execute(
                    "INSERT OR IGNORE INTO parcelle_categories_ppp "
                    "(culture_parcelle_id, culture_ppp) VALUES (?, ?)",
                    (culture_parcelle_id, cat.strip()))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_categories_ppp_culture : {e}")


def produit_homologue_pour_culture(produit_id: int, culture_parcelle_id: int) -> bool:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM parcelle_categories_ppp pcp
            JOIN ppp_usages u ON u.culture = pcp.culture_ppp
            WHERE pcp.culture_parcelle_id = ? AND u.produit_id = ?
        """, (culture_parcelle_id, produit_id))
        count = cur.fetchone()[0]
        cur.close()
        return count > 0
    except Exception:
        return False


# ── Helpers ruches ────────────────────────────
def peut_supprimer_ruche(user: dict) -> bool:
    return user.get("role") == "admin" or bool(user.get("is_apiculteur"))


# ── Helpers engrais vert ──────────────────────
def get_engrais_vert_varietes(culture_parcelle_id: int) -> list:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, variete, taux_pct FROM engrais_vert_varietes "
            "WHERE culture_parcelle_id = ? ORDER BY id", (culture_parcelle_id,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception:
        return []


def set_engrais_vert_varietes(culture_parcelle_id: int, varietes: list):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM engrais_vert_varietes WHERE culture_parcelle_id = ?",
            (culture_parcelle_id,))
        for v in varietes:
            nom = v.get("variete", "").strip()
            if nom:
                cur.execute(
                    "INSERT INTO engrais_vert_varietes "
                    "(culture_parcelle_id, variete, taux_pct) VALUES (?, ?, ?)",
                    (culture_parcelle_id, nom, v.get("taux_pct")))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_engrais_vert_varietes : {e}")


def get_cultures_parcelle(parcelle_id: int) -> list:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM cultures_parcelle "
            "WHERE parcelle_id = ? AND actif = 1 ORDER BY id",
            (parcelle_id,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception:
        return []


def surface_occupee_parcelle(parcelle_id: int) -> float:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(SUM(surface_occupee_m2), 0) "
            "FROM cultures_parcelle WHERE parcelle_id=? AND actif=1",
            (parcelle_id,))
        total = cur.fetchone()[0]
        cur.close()
        return total or 0
    except Exception:
        return 0


# ── Helpers irrigation ↔ cultures ─────────────
def get_cultures_systeme(systeme_id: int) -> list:
    """Retourne les cultures couvertes par un système d'irrigation."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT cp.id, cp.espece, cp.variete, cp.categorie
            FROM irrigation_systeme_cultures isc
            JOIN cultures_parcelle cp ON cp.id = isc.culture_parcelle_id
            WHERE isc.systeme_id = ?
        """, (systeme_id,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception:
        return []


def set_cultures_systeme(systeme_id: int, culture_ids: list):
    """Remplace la liste des cultures couvertes par un système."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM irrigation_systeme_cultures WHERE systeme_id=?",
            (systeme_id,))
        for cid in culture_ids:
            cur.execute("""
                INSERT OR IGNORE INTO irrigation_systeme_cultures
                (systeme_id, culture_parcelle_id) VALUES (?, ?)
            """, (systeme_id, cid))
        conn.commit()
        cur.close()
    except Exception as e:
        debug.debug(f"[DB] Erreur set_cultures_systeme : {e}")


# ── Helpers permissions ───────────────────────
def get_permissions(user_id: int) -> dict:
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT module, lecture, ecriture, suppression "
            "FROM user_permissions WHERE user_id = ?", (user_id,))
        rows = cur.fetchall()
        cur.close()
        return {row[0]: {"lecture": bool(row[1]), "ecriture": bool(row[2]),
                         "suppression": bool(row[3])} for row in rows}
    except Exception:
        return {}


def set_permissions(user_id: int, permissions: dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        for module, perms in permissions.items():
            cur.execute("""
                INSERT INTO user_permissions
                (user_id, module, lecture, ecriture, suppression)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, module,
                  1 if perms.get("lecture", True) else 0,
                  1 if perms.get("ecriture", False) else 0,
                  1 if perms.get("suppression", False) else 0))
        conn.commit()
        cur.close()
        debug.debug(f"[DB] Permissions user {user_id} mises à jour")
    except Exception as e:
        debug.debug(f"[DB] Erreur set_permissions : {e}")


def init_permissions_defaut(user_id: int, role: str):
    defauts = DEFAUTS_PERMISSIONS.get(role, DEFAUTS_PERMISSIONS["user"])
    set_permissions(user_id, defauts)


def peut_action(user: dict, module: str, action: str = "lecture") -> bool:
    if user.get("role") == "admin":
        return True
    user_id = user.get("id")
    if not user_id:
        return False
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"SELECT {action} FROM user_permissions "
            "WHERE user_id = ? AND module = ?",
            (user_id, module))
        row = cur.fetchone()
        cur.close()
        if row is None:
            return action == "lecture"
        return bool(row[0])
    except Exception:
        return action == "lecture"


# ── Helpers référentiel cultures (NPK partagé Parcelles ↔ Fertilisants) ──
def get_or_create_culture_ref(nom_espece: str) -> int | None:
    """Retourne l'id de la culture dans le référentiel 'cultures'
    (table utilisée par le module Fertilisants), en la créant avec
    NPK=0 si elle n'existe pas encore (recherche insensible à la casse).
    """
    nom = (nom_espece or "").strip()
    if not nom:
        return None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM cultures WHERE LOWER(nom) = LOWER(?)", (nom,))
        row = cur.fetchone()
        if row:
            cur.close()
            return row[0]
        cur.execute(
            "INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k) "
            "VALUES (?, 0, 0, 0)", (nom,))
        conn.commit()
        new_id = cur.lastrowid
        cur.close()
        debug.debug(f"[DB] Référentiel culture créé : {nom} (id={new_id})")
        return new_id
    except Exception as e:
        debug.debug(f"[DB] Erreur get_or_create_culture_ref : {e}")
        return None


def get_npk_culture_ref(nom_espece: str) -> dict:
    """Retourne {'n':..,'p':..,'k':..} pour une espèce donnée, ou des
    zéros si elle n'existe pas encore dans le référentiel."""
    nom = (nom_espece or "").strip()
    if not nom:
        return {"n": 0, "p": 0, "k": 0}
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT besoin_n, besoin_p, besoin_k FROM cultures "
            "WHERE LOWER(nom) = LOWER(?)", (nom,))
        row = cur.fetchone()
        cur.close()
        if row:
            return {"n": row[0], "p": row[1], "k": row[2]}
        return {"n": 0, "p": 0, "k": 0}
    except Exception:
        return {"n": 0, "p": 0, "k": 0}


def set_npk_culture_ref(nom_espece: str, n: float, p: float, k: float):
    """Met à jour (ou crée) le NPK d'une espèce dans le référentiel."""
    nom = (nom_espece or "").strip()
    if not nom:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM cultures WHERE LOWER(nom) = LOWER(?)", (nom,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE cultures SET besoin_n=?, besoin_p=?, besoin_k=? "
                "WHERE id=?", (n, p, k, row[0]))
        else:
            cur.execute(
                "INSERT INTO cultures (nom, besoin_n, besoin_p, besoin_k) "
                "VALUES (?, ?, ?, ?)", (nom, n, p, k))
        conn.commit()
        cur.close()
        debug.debug(f"[DB] NPK mis à jour pour {nom} : N={n} P={p} K={k}")
    except Exception as e:
        debug.debug(f"[DB] Erreur set_npk_culture_ref : {e}")


# ── Catalogue Fertilisants enrichi ────────────
_MIGRATIONS_FERTILISANTS = [
    ("uab",              "INTEGER NOT NULL DEFAULT 0"),
    ("origine",          "TEXT CHECK(origine IN ('organique','mineral')) DEFAULT 'mineral'"),
    ("revendeur_nom",    "TEXT(150) DEFAULT NULL"),
    ("revendeur_tel",    "TEXT(20)  DEFAULT NULL"),
    ("revendeur_email",  "TEXT(150) DEFAULT NULL"),
]


def _migrer_fertilisants_v1(cur):
    _migrer_colonnes(cur, "fertilisants", _MIGRATIONS_FERTILISANTS)


_TABLE_CARNET_FERTI = """
    CREATE TABLE IF NOT EXISTS carnet_fertilisation (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        operateur_id        INTEGER   NOT NULL,
        parcelle_id         INTEGER   NOT NULL,
        culture_parcelle_id INTEGER   DEFAULT NULL,
        fertilisant_id      INTEGER   NOT NULL,
        date_apport         DATE      NOT NULL,
        dose_totale_kg      REAL      NOT NULL,
        surface_traitee_ha  REAL      NOT NULL,
        azote_apporte_kg    REAL      NOT NULL DEFAULT 0,
        phosphore_apporte_kg REAL     NOT NULL DEFAULT 0,
        potassium_apporte_kg REAL     NOT NULL DEFAULT 0,
        methode              TEXT(100) DEFAULT NULL,
        notes                TEXT      DEFAULT NULL,
        created_at           DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (operateur_id)        REFERENCES users(id)             ON DELETE RESTRICT,
        FOREIGN KEY (parcelle_id)         REFERENCES parcelles(id)         ON DELETE CASCADE,
        FOREIGN KEY (culture_parcelle_id) REFERENCES cultures_parcelle(id) ON DELETE SET NULL,
        FOREIGN KEY (fertilisant_id)      REFERENCES fertilisants(id)      ON DELETE RESTRICT
    );
"""

_INDEXES_CARNET_FERTI = [
    "CREATE INDEX IF NOT EXISTS idx_carnetferti_parcelle ON carnet_fertilisation(parcelle_id);",
    "CREATE INDEX IF NOT EXISTS idx_carnetferti_date     ON carnet_fertilisation(date_apport);",
    "CREATE INDEX IF NOT EXISTS idx_carnetferti_ope       ON carnet_fertilisation(operateur_id);",
]


def init_carnet_fertilisation(cur):
    cur.execute(_TABLE_CARNET_FERTI)
    for idx in _INDEXES_CARNET_FERTI:
        cur.execute(idx)
    _migrer_fertilisants_v1(cur)


# ── Helpers carnet fertilisation ──────────────
SEUIL_AZOTE_ORGANIQUE_HA_AN = 170   # kg N/ha/an — directive nitrates (effluents élevage)
SEUIL_FRACTIONNEMENT_KG     = 100   # kg N max par apport (sauf maïs)
SEUIL_FRACTIONNEMENT_MAIS   = 50    # kg N max au 1er apport sur maïs


def calculer_azote_apporte(fertilisant_n_pct: float, dose_totale_kg: float) -> float:
    """N total (kg) = dose épandue (kg) × %N / 100."""
    return (fertilisant_n_pct or 0) / 100 * (dose_totale_kg or 0)


def cumul_azote_organique_ha_an(parcelle_id: int, annee: int) -> float:
    """Cumul d'azote organique (kg N/ha) épandu sur une parcelle pour une
    année donnée, ramené à l'hectare par une règle de trois sur la
    surface réellement traitée à chaque apport.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT cf.azote_apporte_kg, cf.surface_traitee_ha
            FROM carnet_fertilisation cf
            JOIN fertilisants f ON f.id = cf.fertilisant_id
            WHERE cf.parcelle_id = ?
              AND f.origine = 'organique'
              AND strftime('%Y', cf.date_apport) = ?
        """, (parcelle_id, str(annee)))
        rows = cur.fetchall()
        cur.close()

        total_n_par_ha = 0.0
        for azote_kg, surface_ha in rows:
            if surface_ha and surface_ha > 0:
                # Règle de trois : ramène l'apport à un équivalent /ha
                total_n_par_ha += azote_kg / surface_ha
        return total_n_par_ha
    except Exception as e:
        debug.debug(f"[DB] Erreur cumul_azote_organique_ha_an : {e}")
        return 0.0


def verifier_depassement_azote(parcelle_id: int, annee: int,
                                 nouvel_apport_n_kg: float = 0,
                                 nouvelle_surface_ha: float = 0) -> dict:
    """Vérifie si l'ajout d'un nouvel apport organique dépasserait le
    plafond réglementaire de 170 kg N organique/ha/an sur la parcelle.

    Retourne {'cumul_actuel':.., 'apport_ramene_ha':.., 'nouveau_total':..,
              'depassement': bool, 'seuil': 170}
    """
    cumul_actuel = cumul_azote_organique_ha_an(parcelle_id, annee)
    apport_ramene_ha = (nouvel_apport_n_kg / nouvelle_surface_ha
                        if nouvelle_surface_ha and nouvelle_surface_ha > 0
                        else 0)
    nouveau_total = cumul_actuel + apport_ramene_ha
    return {
        "cumul_actuel": round(cumul_actuel, 1),
        "apport_ramene_ha": round(apport_ramene_ha, 1),
        "nouveau_total": round(nouveau_total, 1),
        "depassement": nouveau_total > SEUIL_AZOTE_ORGANIQUE_HA_AN,
        "seuil": SEUIL_AZOTE_ORGANIQUE_HA_AN,
    }


def verifier_fractionnement(azote_kg: float, espece: str = "") -> dict:
    """Vérifie le respect de la règle de fractionnement des apports azotés.
    Maïs : max 50 kg N au 1er apport. Autres cultures : max 100 kg N/apport.
    """
    est_mais = "mais" in (espece or "").lower().replace("ï", "i")
    seuil = SEUIL_FRACTIONNEMENT_MAIS if est_mais else SEUIL_FRACTIONNEMENT_KG
    return {
        "seuil": seuil,
        "depassement": (azote_kg or 0) > seuil,
        "est_mais": est_mais,
    }


def get_historique_fertilisation(parcelle_id: int = None,
                                   date_debut: str = None,
                                   date_fin: str = None) -> list:
    try:
        conn = get_connection()
        cur = conn.cursor()
        sql = """
            SELECT cf.id, cf.date_apport, p.nom AS parcelle_nom,
                   cp.espece, cp.variete, f.nom AS fertilisant_nom,
                   cf.dose_totale_kg, cf.surface_traitee_ha,
                   cf.azote_apporte_kg, cf.phosphore_apporte_kg,
                   cf.potassium_apporte_kg, cf.methode, cf.notes,
                   u.prenom || ' ' || u.nom AS operateur,
                   f.origine, cf.parcelle_id
            FROM carnet_fertilisation cf
            JOIN parcelles p     ON p.id = cf.parcelle_id
            LEFT JOIN cultures_parcelle cp ON cp.id = cf.culture_parcelle_id
            JOIN fertilisants f  ON f.id = cf.fertilisant_id
            JOIN users u         ON u.id = cf.operateur_id
            WHERE 1=1
        """
        params = []
        if parcelle_id:
            sql += " AND cf.parcelle_id = ?"
            params.append(parcelle_id)
        if date_debut:
            sql += " AND cf.date_apport >= ?"
            params.append(date_debut)
        if date_fin:
            sql += " AND cf.date_apport <= ?"
            params.append(date_fin)
        sql += " ORDER BY cf.date_apport DESC"
        cur.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception as e:
        debug.debug(f"[DB] Erreur get_historique_fertilisation : {e}")
        return []