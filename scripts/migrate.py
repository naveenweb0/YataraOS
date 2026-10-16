#!/usr/bin/env python3
"""
YatraOS Database Migration Runner.
Applies versioned migrations transactionally to the SQLite database.
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def get_db_connection(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def ensure_migration_table(con: sqlite3.Connection) -> None:
    con.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)


def get_applied_migrations(con: sqlite3.Connection) -> set[str]:
    ensure_migration_table(con)
    rows = con.execute("SELECT version FROM schema_migrations;").fetchall()
    return {row[0] for row in rows}


def reconcile_sources_table(con: sqlite3.Connection) -> list[str]:
    """Safely adds missing reconciliation columns to the sources table."""
    columns_added = []
    cursor = con.execute("PRAGMA table_info(sources);")
    existing_cols = {row[1] for row in cursor.fetchall()}

    if "region" not in existing_cols:
        con.execute("ALTER TABLE sources ADD COLUMN region TEXT;")
        columns_added.append("region")

    if "attribution_required" not in existing_cols:
        con.execute("""
            ALTER TABLE sources ADD COLUMN attribution_required TEXT NOT NULL DEFAULT 'unknown'
            CHECK (attribution_required IN ('yes', 'no', 'conditional', 'unknown'));
        """)
        columns_added.append("attribution_required")

    return columns_added


def apply_migration_file(con: sqlite3.Connection, migration_file: Path, version: str) -> None:
    migration_name = migration_file.stem
    print(f"Applying migration: {migration_name} ...")
    
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    with con:
        # Step 1: Reconcile sources schema if needed
        reconcile_sources_table(con)
        
        # Step 2: Execute migration script
        con.executescript(sql)
        
        # Step 3: Record in schema_migrations
        con.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?);",
            (version, migration_name),
        )
        
        # Update user_version
        try:
            v_int = int(version.split("_")[0])
            con.execute(f"PRAGMA user_version = {v_int};")
        except ValueError:
            pass

    print(f"Successfully applied {migration_name}.")


def verify_fts5_triggers(con: sqlite3.Connection) -> bool:
    """Verifies that FTS5 triggers operate correctly on insert, update, and delete."""
    test_id = "__test_trigger_probe__"
    try:
        with con:
            # Test Insert
            con.execute("""
                INSERT INTO places (
                    place_id, canonical_name, alternate_names_json, region,
                    primary_category, short_description, historical_background
                ) VALUES (
                    ?, 'Probe Place', '["Probe Alt"]', 'Punjab',
                    'Heritage Site', 'Probe Short Description', 'Probe Historical Text'
                );
            """, (test_id,))

            match_insert = con.execute(
                "SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'Probe';"
            ).fetchone()[0]
            if match_insert == 0:
                return False

            # Test Update
            con.execute("""
                UPDATE places
                SET short_description = 'Updated Description ProbeText'
                WHERE place_id = ?;
            """, (test_id,))

            match_update = con.execute(
                "SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'ProbeText';"
            ).fetchone()[0]
            match_old = con.execute(
                "SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'Short';"
            ).fetchone()[0]
            if match_update == 0 or match_old != 0:
                return False

            # Test Delete
            con.execute("DELETE FROM places WHERE place_id = ?;", (test_id,))
            match_delete = con.execute(
                "SELECT COUNT(*) FROM places_fts WHERE places_fts MATCH 'ProbeText';"
            ).fetchone()[0]
            if match_delete != 0:
                return False

            return True
    except Exception as e:
        print(f"Trigger verification failed: {e}", file=sys.stderr)
        # Cleanup if rollback didn't remove probe
        try:
            con.execute("DELETE FROM places WHERE place_id = ?;", (test_id,))
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(description="YatraOS database migration runner.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("data/yatraos.sqlite"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=Path("database/migrations"),
        help="Directory containing SQL migrations",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show migration status without applying changes",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify FTS5 triggers and database integrity",
    )
    args = parser.parse_args()

    con = get_db_connection(args.db)
    ensure_migration_table(con)
    applied = get_applied_migrations(con)

    migration_files = sorted(args.migrations_dir.glob("*.sql"))

    if args.status:
        print(f"Database: {args.db}")
        print(f"PRAGMA user_version: {con.execute('PRAGMA user_version').fetchone()[0]}")
        print("Migrations status:")
        for mf in migration_files:
            v = mf.stem.split("_")[0]
            status = "APPLIED" if v in applied else "PENDING"
            print(f"  [{status}] {mf.name}")
        con.close()
        return

    # Apply pending migrations
    for mf in migration_files:
        version = mf.stem.split("_")[0]
        if version not in applied:
            apply_migration_file(con, mf, version)
        else:
            print(f"Migration {mf.name} already applied.")

    # Always verify FTS5 triggers and integrity after applying
    integrity = con.execute("PRAGMA integrity_check;").fetchone()[0]
    if integrity != "ok":
        con.close()
        raise SystemExit(f"Database integrity check failed: {integrity}")

    if not verify_fts5_triggers(con):
        con.close()
        raise SystemExit("FTS5 triggers verification failed!")

    print(f"Database {args.db} is up to date and verified.")
    con.close()


if __name__ == "__main__":
    main()
