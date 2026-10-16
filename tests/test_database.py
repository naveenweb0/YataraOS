"""
Tests for YatraOS SQLite database integrity, constraints, triggers, and FTS5 synchronization.
"""

import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def test_db():
    """Provides an in-memory SQLite database initialized with schema and migration 001."""
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys = ON;")

    schema_path = Path("database/schema.sql")
    migration_path = Path("database/migrations/001_fts5_triggers_and_sources_reconciliation.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        con.executescript(f.read())

    # Check and conditionally add columns if not already in schema
    cols = {row[1] for row in con.execute("PRAGMA table_info(sources);").fetchall()}
    if "region" not in cols:
        con.execute("ALTER TABLE sources ADD COLUMN region TEXT;")
    if "attribution_required" not in cols:
        con.execute("""
            ALTER TABLE sources ADD COLUMN attribution_required TEXT NOT NULL DEFAULT 'unknown'
            CHECK (attribution_required IN ('yes', 'no', 'conditional', 'unknown'));
        """)

    with open(migration_path, "r", encoding="utf-8") as f:
        con.executescript(f.read())

    yield con
    con.close()


def test_database_integrity(test_db):
    """PRAGMA integrity_check must return 'ok'."""
    res = test_db.execute("PRAGMA integrity_check;").fetchone()[0]
    assert res == "ok"


def test_foreign_keys_enforced(test_db):
    """Foreign key constraint violations must raise IntegrityError."""
    # Attempt to insert a claim referencing non-existent place and source
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO source_claims (
                claim_id, place_id, source_id, field_name, claim_text, retrieved_at
            ) VALUES (
                'c_invalid', 'non_existent_place', 'non_existent_source', 'history', 'Test', '2026-10-17'
            );
        """)


def test_cascade_delete_place(test_db):
    """Deleting a place must cascade and delete linked categories and claims."""
    # 1. Insert source
    test_db.execute("""
        INSERT INTO sources (source_id, name, status, commercial_use_allowed, redistribution_allowed)
        VALUES ('src1', 'Test Source', 'approved', 'conditional', 'yes');
    """)

    # 2. Insert place
    test_db.execute("""
        INSERT INTO places (place_id, canonical_name, region, primary_category)
        VALUES ('p1', 'Test Place', 'Punjab', 'Fort');
    """)

    # 3. Insert category and claim
    test_db.execute("""
        INSERT INTO place_categories (place_id, category, is_primary) VALUES ('p1', 'Fort', 1);
    """)
    test_db.execute("""
        INSERT INTO source_claims (claim_id, place_id, source_id, field_name, claim_text, retrieved_at)
        VALUES ('c1', 'p1', 'src1', 'history', 'Ancient fort', '2026-10-17');
    """)

    assert test_db.execute("SELECT COUNT(*) FROM place_categories WHERE place_id = 'p1'").fetchone()[0] == 1
    assert test_db.execute("SELECT COUNT(*) FROM source_claims WHERE place_id = 'p1'").fetchone()[0] == 1

    # 4. Delete place
    test_db.execute("DELETE FROM places WHERE place_id = 'p1';")

    # Categories and claims must be automatically deleted via CASCADE
    assert test_db.execute("SELECT COUNT(*) FROM place_categories WHERE place_id = 'p1'").fetchone()[0] == 0
    assert test_db.execute("SELECT COUNT(*) FROM source_claims WHERE place_id = 'p1'").fetchone()[0] == 0


def test_duplicate_place_id_rejected(test_db):
    """Duplicate place_id must raise IntegrityError."""
    test_db.execute("""
        INSERT INTO places (place_id, canonical_name, region, primary_category)
        VALUES ('dup_place', 'First Place', 'Punjab', 'Temple');
    """)

    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO places (place_id, canonical_name, region, primary_category)
            VALUES ('dup_place', 'Duplicate Place', 'Punjab', 'Temple');
        """)


def test_invalid_coordinates_rejected(test_db):
    """Latitude and longitude out of geographic bounds must be rejected by CHECK constraints."""
    # Invalid latitude > 90
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO places (place_id, canonical_name, region, primary_category, latitude, longitude)
            VALUES ('p_bad_lat', 'Bad Lat', 'Punjab', 'Temple', 95.0, 75.0);
        """)

    # Invalid latitude < -90
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO places (place_id, canonical_name, region, primary_category, latitude, longitude)
            VALUES ('p_bad_lat_neg', 'Bad Lat Neg', 'Punjab', 'Temple', -95.0, 75.0);
        """)

    # Invalid longitude > 180
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO places (place_id, canonical_name, region, primary_category, latitude, longitude)
            VALUES ('p_bad_lon', 'Bad Lon', 'Punjab', 'Temple', 30.0, 185.0);
        """)


def test_fts5_insert_synchronisation(test_db):
    """Inserting into places must automatically populate places_fts and match search queries."""
    test_db.execute("""
        INSERT INTO places (
            place_id, canonical_name, alternate_names_json, region, primary_category,
            short_description, historical_background
        ) VALUES (
            'harmandir_sahib', 'Sri Harmandir Sahib', '["Golden Temple", "Darbar Sahib"]',
            'Punjab', 'Gurudwara', 'Foremost spiritual center of Sikhism',
            'Founded by Guru Ram Das in 1577 CE'
        );
    """)

    # Search by canonical name
    res = test_db.execute("SELECT place_id FROM places_fts WHERE places_fts MATCH 'Harmandir';").fetchall()
    assert len(res) == 1 and res[0][0] == "harmandir_sahib"

    # Search by alternate name
    res_alt = test_db.execute("SELECT place_id FROM places_fts WHERE places_fts MATCH 'Golden';").fetchall()
    assert len(res_alt) == 1 and res_alt[0][0] == "harmandir_sahib"

    # Search by historical term
    res_hist = test_db.execute("SELECT place_id FROM places_fts WHERE places_fts MATCH '1577';").fetchall()
    assert len(res_hist) == 1 and res_hist[0][0] == "harmandir_sahib"


def test_fts5_update_synchronisation(test_db):
    """Updating a place must update search index and remove old tokens."""
    test_db.execute("""
        INSERT INTO places (
            place_id, canonical_name, region, primary_category, short_description
        ) VALUES (
            'p_update', 'Initial Place', 'Punjab', 'Fort', 'Initial unique description string'
        );
    """)

    assert test_db.execute("SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'unique';").fetchone()[0] == 1

    # Update description
    test_db.execute("""
        UPDATE places
        SET short_description = 'Revised completely novel content'
        WHERE place_id = 'p_update';
    """)

    # New term matches
    assert test_db.execute("SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'novel';").fetchone()[0] == 1
    # Old term must no longer match
    assert test_db.execute("SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'unique';").fetchone()[0] == 0


def test_fts5_delete_synchronisation(test_db):
    """Deleting a place must remove it from the FTS5 virtual table."""
    test_db.execute("""
        INSERT INTO places (
            place_id, canonical_name, region, primary_category, short_description
        ) VALUES (
            'p_del', 'Deletable Monument', 'Himachal Pradesh', 'Temple', 'DistinctiveSearchableToken'
        );
    """)

    assert test_db.execute("SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'DistinctiveSearchableToken';").fetchone()[0] == 1

    test_db.execute("DELETE FROM places WHERE place_id = 'p_del';")

    assert test_db.execute("SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'DistinctiveSearchableToken';").fetchone()[0] == 0


def test_itinerary_stop_order_unique(test_db):
    """Itinerary stops on the same day cannot share the same stop_order."""
    test_db.execute("""
        INSERT INTO places (place_id, canonical_name, region, primary_category)
        VALUES ('p_stop1', 'Stop One', 'Punjab', 'Fort'), ('p_stop2', 'Stop Two', 'Punjab', 'Temple');
    """)

    test_db.execute("""
        INSERT INTO itineraries (itinerary_id, title, duration_days)
        VALUES ('itin_1', 'Punjab Heritage Tour', 3);
    """)

    # First stop on Day 1, Order 1
    test_db.execute("""
        INSERT INTO itinerary_stops (stop_id, itinerary_id, place_id, day_number, stop_order)
        VALUES ('s1', 'itin_1', 'p_stop1', 1, 1);
    """)

    # Attempt to insert second stop with same day_number and stop_order
    with pytest.raises(sqlite3.IntegrityError):
        test_db.execute("""
            INSERT INTO itinerary_stops (stop_id, itinerary_id, place_id, day_number, stop_order)
            VALUES ('s2', 'itin_1', 'p_stop2', 1, 1);
        """)
