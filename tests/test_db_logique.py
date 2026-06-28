"""
Tests de la logique métier pure de db.py — sans lancer Qt, sans toucher
à la vraie base de données utilisateur (utilise une BDD SQLite en
mémoire, jetée à la fin de chaque test).

USAGE :
    cd ~/Bureau/gestion_fertilisants
    pip install pytest --break-system-packages
    python3 -m pytest tests/test_db_logique.py -v

⚠️ Ce fichier ne touche JAMAIS ~/.GestionFertilisants/gestion.db.
   Il monkey-patche db.get_connection() vers une base en mémoire
   à chaque test (fixture 'db_memoire').
"""

import sys
import os
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


@pytest.fixture
def db_memoire(monkeypatch):
    """Remplace get_connection() par une connexion SQLite en mémoire,
    avec le schéma complet initialisé, pour la durée du test."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    monkeypatch.setattr(db, "_conn", conn)
    monkeypatch.setattr(db, "get_connection", lambda: conn)

    cur = conn.cursor()
    for ddl in db._TABLES:
        cur.execute(ddl)
    for idx in db._INDEXES:
        cur.execute(idx)
    db.init_carnet_fertilisation(cur)  # ajoute colonnes fertilisants.origine, etc.
    cur.execute("INSERT INTO parametres_app (id) VALUES (1)")
    conn.commit()

    yield conn
    conn.close()


# ── Tests référentiel cultures (NPK partagé) ──────────────
class TestReferentielCultures:
    def test_creation_nouvelle_culture(self, db_memoire):
        cid = db.get_or_create_culture_ref("Tomate")
        assert cid is not None
        npk = db.get_npk_culture_ref("Tomate")
        assert npk == {"n": 0, "p": 0, "k": 0}

    def test_recherche_insensible_casse(self, db_memoire):
        db.get_or_create_culture_ref("Tomate")
        cid2 = db.get_or_create_culture_ref("TOMATE")
        cid3 = db.get_or_create_culture_ref("tomate")
        # Les 3 doivent pointer vers la même entrée
        cur = db_memoire.cursor()
        cur.execute("SELECT COUNT(*) FROM cultures WHERE LOWER(nom)='tomate'")
        assert cur.fetchone()[0] == 1

    def test_set_npk_culture_ref(self, db_memoire):
        db.set_npk_culture_ref("Carotte", 80, 65, 180)
        npk = db.get_npk_culture_ref("Carotte")
        assert npk == {"n": 80, "p": 65, "k": 180}

    def test_npk_espece_inexistante(self, db_memoire):
        npk = db.get_npk_culture_ref("EspeceQuiNExistePas")
        assert npk == {"n": 0, "p": 0, "k": 0}


# ── Tests permissions ──────────────────────────────────────
class TestPermissions:
    def _creer_user(self, conn, role="user"):
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (nom, prenom, username, password_hash, role)
            VALUES ('Test', 'User', 'test.user', 'x', ?)
        """, (role,))
        conn.commit()
        return cur.lastrowid

    def test_admin_a_toujours_tous_les_droits(self, db_memoire):
        admin = {"id": 1, "role": "admin"}
        assert db.peut_action(admin, "parcelles", "ecriture") is True
        assert db.peut_action(admin, "parcelles", "suppression") is True
        assert db.peut_action(admin, "admin", "ecriture") is True

    def test_user_sans_permission_definie_lecture_seule(self, db_memoire):
        uid = self._creer_user(db_memoire)
        user = {"id": uid, "role": "user"}
        assert db.peut_action(user, "parcelles", "lecture") is True
        assert db.peut_action(user, "parcelles", "ecriture") is False

    def test_set_permissions_et_relecture(self, db_memoire):
        uid = self._creer_user(db_memoire)
        user = {"id": uid, "role": "user"}
        db.set_permissions(uid, {
            "parcelles": {"lecture": True, "ecriture": True, "suppression": False}
        })
        assert db.peut_action(user, "parcelles", "ecriture") is True
        assert db.peut_action(user, "parcelles", "suppression") is False

    def test_init_permissions_defaut_admin(self, db_memoire):
        uid = self._creer_user(db_memoire, role="admin")
        db.init_permissions_defaut(uid, "admin")
        perms = db.get_permissions(uid)
        assert perms["parcelles"]["ecriture"] is True
        assert perms["parcelles"]["suppression"] is True

    def test_init_permissions_defaut_user(self, db_memoire):
        uid = self._creer_user(db_memoire)
        db.init_permissions_defaut(uid, "user")
        perms = db.get_permissions(uid)
        assert perms["parcelles"]["lecture"] is True
        assert perms["parcelles"]["ecriture"] is False


# ── Tests carnet fertilisation / azote ────────────────────
class TestCarnetFertilisation:
    def _creer_parcelle(self, conn, surface_ha=1.0):
        cur = conn.cursor()
        cur.execute("INSERT INTO parcelles (nom, surface_ha) VALUES ('P1', ?)",
                    (surface_ha,))
        conn.commit()
        return cur.lastrowid

    def _creer_fertilisant_organique(self, conn, n_pct=4.0):
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO fertilisants (nom, n, p, k, origine)
            VALUES ('Fumier', ?, 2, 3, 'organique')
        """, (n_pct,))
        conn.commit()
        return cur.lastrowid

    def _creer_user(self, conn):
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (nom, prenom, username, password_hash, role)
            VALUES ('Op', 'Test', 'op.test', 'x', 'user')
        """)
        conn.commit()
        return cur.lastrowid

    def test_calculer_azote_apporte(self, db_memoire):
        # 4% N sur 100kg de produit = 4kg d'azote
        assert db.calculer_azote_apporte(4.0, 100) == 4.0
        assert db.calculer_azote_apporte(0, 100) == 0
        assert db.calculer_azote_apporte(4.0, 0) == 0

    def test_cumul_azote_organique_regle_de_trois(self, db_memoire):
        """Vérifie que le cumul ramène bien chaque apport à l'hectare
        via une règle de trois sur la surface RÉELLEMENT traitée,
        pas sur la surface totale de la parcelle."""
        pid = self._creer_parcelle(db_memoire, surface_ha=2.0)
        fid = self._creer_fertilisant_organique(db_memoire)
        uid = self._creer_user(db_memoire)

        cur = db_memoire.cursor()
        # Apport de 20 kg N sur seulement 0.5 ha (pas toute la parcelle)
        cur.execute("""
            INSERT INTO carnet_fertilisation
            (operateur_id, parcelle_id, fertilisant_id, date_apport,
             dose_totale_kg, surface_traitee_ha, azote_apporte_kg)
            VALUES (?, ?, ?, '2026-06-01', 500, 0.5, 20)
        """, (uid, pid, fid))
        db_memoire.commit()

        cumul = db.cumul_azote_organique_ha_an(pid, 2026)
        # Règle de trois : 20 kg N / 0.5 ha = 40 kg N/ha équivalent
        assert cumul == 40.0

    def test_verifier_depassement_azote_sous_seuil(self, db_memoire):
        pid = self._creer_parcelle(db_memoire)
        check = db.verifier_depassement_azote(pid, 2026, 50, 1.0)
        assert check["depassement"] is False
        assert check["nouveau_total"] == 50.0

    def test_verifier_depassement_azote_au_dessus_seuil(self, db_memoire):
        pid = self._creer_parcelle(db_memoire)
        check = db.verifier_depassement_azote(pid, 2026, 200, 1.0)
        assert check["depassement"] is True
        assert check["seuil"] == 170

    def test_verifier_fractionnement_normal(self, db_memoire):
        res = db.verifier_fractionnement(80, "Tomate")
        assert res["depassement"] is False
        assert res["est_mais"] is False

    def test_verifier_fractionnement_depasse(self, db_memoire):
        res = db.verifier_fractionnement(150, "Tomate")
        assert res["depassement"] is True
        assert res["seuil"] == 100

    def test_verifier_fractionnement_mais_seuil_different(self, db_memoire):
        res = db.verifier_fractionnement(60, "Maïs")
        assert res["est_mais"] is True
        assert res["depassement"] is True  # 60 > 50 pour maïs
        assert res["seuil"] == 50


# ── Tests engrais vert ─────────────────────────────────────
class TestEngraisVert:
    def _creer_culture_parcelle(self, conn):
        cur = conn.cursor()
        cur.execute("INSERT INTO parcelles (nom, surface_ha) VALUES ('P1', 1.0)")
        pid = cur.lastrowid
        cur.execute("""
            INSERT INTO cultures_parcelle (parcelle_id, categorie, melange_nom)
            VALUES (?, 'engrais_vert', 'Mélange test')
        """, (pid,))
        conn.commit()
        return cur.lastrowid

    def test_set_et_get_varietes(self, db_memoire):
        cid = self._creer_culture_parcelle(db_memoire)
        db.set_engrais_vert_varietes(cid, [
            {"variete": "Phacélie", "taux_pct": 60},
            {"variete": "Vesce", "taux_pct": 40},
        ])
        varietes = db.get_engrais_vert_varietes(cid)
        assert len(varietes) == 2
        noms = {v["variete"] for v in varietes}
        assert noms == {"Phacélie", "Vesce"}

    def test_set_varietes_remplace_les_anciennes(self, db_memoire):
        cid = self._creer_culture_parcelle(db_memoire)
        db.set_engrais_vert_varietes(cid, [{"variete": "A", "taux_pct": 100}])
        db.set_engrais_vert_varietes(cid, [{"variete": "B", "taux_pct": 100}])
        varietes = db.get_engrais_vert_varietes(cid)
        assert len(varietes) == 1
        assert varietes[0]["variete"] == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
