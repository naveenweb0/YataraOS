import sqlite3
from pathlib import Path

db_path = Path("data/yatraos.sqlite")

if not db_path.exists():
    raise SystemExit(f"Database missing: {db_path}")

con = sqlite3.connect(db_path)

expected = {
    "sources",
    "places",
    "place_categories",
    "source_claims",
    "visitor_details",
    "media_assets",
    "itineraries",
    "itinerary_stops",
    "places_fts",
}

tables = {
    row[0]
    for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
    )
}

missing = expected - tables
if missing:
    raise SystemExit(f"Missing database objects: {sorted(missing)}")

integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
if integrity != "ok":
    raise SystemExit(f"Database integrity failed: {integrity}")

# Verify that FTS5 can actually index and search text.
con.execute(
    "CREATE VIRTUAL TABLE temp.fts5_test USING fts5(content)"
)
con.execute(
    "INSERT INTO fts5_test(content) VALUES (?)",
    ("heritage culture travel",),
)
matches = con.execute(
    "SELECT COUNT(*) FROM fts5_test WHERE fts5_test MATCH ?",
    ("heritage",),
).fetchone()[0]

if matches != 1:
    raise SystemExit("FTS5 search test failed")

print("PASS: Database exists")
print("PASS: Required tables exist")
print("PASS: Database integrity is OK")
print("PASS: Full-text search works")
print(f"PASS: {len(expected)} required database objects found")

con.close()
