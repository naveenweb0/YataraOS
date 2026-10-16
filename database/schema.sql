PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    publisher TEXT,
    source_url TEXT,
    region TEXT,
    source_type TEXT NOT NULL DEFAULT 'unknown',
    access_method TEXT NOT NULL DEFAULT 'unknown',
    licence_or_terms TEXT,
    commercial_use_allowed TEXT NOT NULL DEFAULT 'unknown'
        CHECK (commercial_use_allowed IN ('yes','no','conditional','unknown')),
    redistribution_allowed TEXT NOT NULL DEFAULT 'unknown'
        CHECK (redistribution_allowed IN ('yes','no','conditional','unknown')),
    attribution_required TEXT NOT NULL DEFAULT 'unknown'
        CHECK (attribution_required IN ('yes','no','conditional','unknown')),
    attribution_text TEXT,
    rate_limits TEXT,
    checked_at TEXT,
    refresh_method TEXT,
    status TEXT NOT NULL DEFAULT 'proposed'
        CHECK (status IN ('proposed','approved','blocked','needs_review')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    alternate_names_json TEXT NOT NULL DEFAULT '[]',
    region TEXT NOT NULL,
    state_or_territory TEXT,
    district TEXT,
    locality TEXT,
    latitude REAL,
    longitude REAL,
    primary_category TEXT NOT NULL,
    short_description TEXT,
    historical_background TEXT,
    cultural_significance TEXT,
    estimated_visit_min INTEGER,
    accessibility_notes TEXT,
    visitor_notes TEXT,
    data_confidence TEXT NOT NULL DEFAULT 'provisional'
        CHECK (data_confidence IN ('verified','provisional','conflicting','unknown')),
    last_verified_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),
    CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),
    CHECK (estimated_visit_min IS NULL OR estimated_visit_min >= 0)
);

CREATE INDEX IF NOT EXISTS idx_places_region ON places(region);
CREATE INDEX IF NOT EXISTS idx_places_category ON places(primary_category);
CREATE INDEX IF NOT EXISTS idx_places_name ON places(canonical_name);

CREATE TABLE IF NOT EXISTS place_categories (
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0,1)),
    PRIMARY KEY (place_id, category)
);

CREATE TABLE IF NOT EXISTS source_claims (
    claim_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    field_name TEXT NOT NULL,
    claim_text TEXT NOT NULL,
    source_quote_or_excerpt TEXT,
    source_published_at TEXT,
    retrieved_at TEXT NOT NULL,
    last_verified_at TEXT,
    confidence TEXT NOT NULL DEFAULT 'provisional'
        CHECK (confidence IN ('verified','provisional','conflicting','unknown')),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_claims_place ON source_claims(place_id);
CREATE INDEX IF NOT EXISTS idx_claims_source ON source_claims(source_id);

CREATE TABLE IF NOT EXISTS visitor_details (
    place_id TEXT PRIMARY KEY REFERENCES places(place_id) ON DELETE CASCADE,
    opening_hours_json TEXT,
    entry_fee_amount REAL,
    entry_fee_currency TEXT DEFAULT 'INR',
    fee_notes TEXT,
    seasonality_notes TEXT,
    contact_or_booking_url TEXT,
    details_verified_at TEXT,
    details_source_claim_id TEXT REFERENCES source_claims(claim_id)
);

CREATE TABLE IF NOT EXISTS media_assets (
    media_id TEXT PRIMARY KEY,
    place_id TEXT NOT NULL REFERENCES places(place_id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    local_path TEXT,
    original_url TEXT,
    creator TEXT,
    licence TEXT NOT NULL DEFAULT 'unknown',
    attribution_text TEXT,
    retrieved_at TEXT,
    redistribution_allowed TEXT NOT NULL DEFAULT 'unknown'
        CHECK (redistribution_allowed IN ('yes','no','conditional','unknown')),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS itineraries (
    itinerary_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    start_date TEXT,
    duration_days INTEGER NOT NULL CHECK (duration_days > 0),
    starting_point TEXT,
    travel_mode TEXT NOT NULL DEFAULT 'unknown',
    budget_amount REAL,
    budget_currency TEXT DEFAULT 'INR',
    preferences_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','reviewed','approved','archived')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS itinerary_stops (
    stop_id TEXT PRIMARY KEY,
    itinerary_id TEXT NOT NULL REFERENCES itineraries(itinerary_id) ON DELETE CASCADE,
    place_id TEXT NOT NULL REFERENCES places(place_id),
    day_number INTEGER NOT NULL CHECK (day_number > 0),
    stop_order INTEGER NOT NULL CHECK (stop_order > 0),
    planned_arrival TEXT,
    planned_departure TEXT,
    planned_visit_min INTEGER,
    travel_from_previous_min INTEGER,
    route_distance_m REAL,
    notes TEXT,
    UNIQUE (itinerary_id, day_number, stop_order)
);

CREATE INDEX IF NOT EXISTS idx_stops_itinerary_day
    ON itinerary_stops(itinerary_id, day_number, stop_order);

CREATE VIRTUAL TABLE IF NOT EXISTS places_fts USING fts5(
    place_id UNINDEXED,
    canonical_name,
    alternate_names,
    short_description,
    historical_background,
    cultural_significance,
    locality,
    district,
    region
);

-- Triggers for automatic FTS5 synchronisation
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

