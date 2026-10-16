-- Migration 001: FTS5 Synchronisation Triggers and Sources Schema Reconciliation
-- Target database: data/yatraos.sqlite

PRAGMA foreign_keys = ON;

-- 1. Migration ledger table
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add reconciliation columns to sources if they do not exist
-- (Handled conditionally in migration runner for SQLite compatibility)

-- 3. Triggers for automatic FTS5 synchronisation with places
CREATE TRIGGER IF NOT EXISTS places_ai_fts AFTER INSERT ON places BEGIN
    INSERT INTO places_fts (
        rowid,
        place_id,
        canonical_name,
        alternate_names,
        short_description,
        historical_background,
        cultural_significance,
        locality,
        district,
        region
    ) VALUES (
        new.rowid,
        new.place_id,
        new.canonical_name,
        new.alternate_names_json,
        new.short_description,
        new.historical_background,
        new.cultural_significance,
        new.locality,
        new.district,
        new.region
    );
END;

CREATE TRIGGER IF NOT EXISTS places_ad_fts AFTER DELETE ON places BEGIN
    DELETE FROM places_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS places_au_fts AFTER UPDATE ON places BEGIN
    DELETE FROM places_fts WHERE rowid = old.rowid;
    INSERT INTO places_fts (
        rowid,
        place_id,
        canonical_name,
        alternate_names,
        short_description,
        historical_background,
        cultural_significance,
        locality,
        district,
        region
    ) VALUES (
        new.rowid,
        new.place_id,
        new.canonical_name,
        new.alternate_names_json,
        new.short_description,
        new.historical_background,
        new.cultural_significance,
        new.locality,
        new.district,
        new.region
    );
END;

-- 4. Safe one-time synchronisation and index rebuild
DELETE FROM places_fts;
INSERT INTO places_fts (
    rowid,
    place_id,
    canonical_name,
    alternate_names,
    short_description,
    historical_background,
    cultural_significance,
    locality,
    district,
    region
)
SELECT
    rowid,
    place_id,
    canonical_name,
    alternate_names_json,
    short_description,
    historical_background,
    cultural_significance,
    locality,
    district,
    region
FROM places;

INSERT INTO places_fts(places_fts) VALUES('rebuild');
