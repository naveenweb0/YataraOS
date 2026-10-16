#!/usr/bin/env python3
"""
YatraOS Production Data Ingestion Pipeline.
Validates sources and places before importing into SQLite.
"""

import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from validator import validate_dataset


def load_sources_from_csv(csv_path: Path) -> list[dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Source registry CSV missing: {csv_path}")
    sources = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {k.strip(): (v.strip() if v is not None else "") for k, v in row.items()}
            # Normalize field names
            if "source_name" in cleaned and "name" not in cleaned:
                cleaned["name"] = cleaned["source_name"]
            if "checked_on" in cleaned and "checked_at" not in cleaned:
                cleaned["checked_at"] = cleaned["checked_on"]
            sources.append(cleaned)
    return sources


def load_places_from_json(json_path: Path) -> list[dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"Places JSON missing: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "places" in data:
            return data["places"]
        else:
            raise ValueError(f"Unrecognized JSON structure in {json_path}")


def ingest_data(
    db_path: Path,
    sources: list[dict[str, Any]],
    places: list[dict[str, Any]],
    dry_run: bool = False,
) -> None:
    # Step 1: Strict validation
    report = validate_dataset(sources, places, for_production=True)
    if report.warnings:
        print(f"Validation warnings ({len(report.warnings)}):")
        for w in report.warnings:
            print(f"  [WARN] {w}")

    if not report.is_valid:
        print(f"Validation failed with {len(report.errors)} errors:", file=sys.stderr)
        for err in report.errors:
            print(
                f"  [ERROR] {err.entity_type.upper()} '{err.entity_id}' field '{err.field_name}': {err.message}",
                file=sys.stderr,
            )
        sys.exit(1)

    print(f"Validation PASSED: {len(sources)} sources, {len(places)} places verified.")

    if dry_run:
        print("Dry run requested. No changes committed.")
        return

    # Step 2: Transactional database ingestion
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = ON;")

    try:
        with con:
            # Upsert sources
            for s in sources:
                con.execute("""
                    INSERT INTO sources (
                        source_id, name, publisher, source_url, region,
                        source_type, access_method, licence_or_terms,
                        commercial_use_allowed, redistribution_allowed,
                        attribution_required, attribution_text, rate_limits,
                        refresh_method, checked_at, status, notes, updated_at
                    ) VALUES (
                        :source_id, :name, :publisher, :source_url, :region,
                        :source_type, :access_method, :licence_or_terms,
                        :commercial_use_allowed, :redistribution_allowed,
                        :attribution_required, :attribution_text, :rate_limits,
                        :refresh_method, :checked_at, :status, :notes, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT(source_id) DO UPDATE SET
                        name = excluded.name,
                        publisher = excluded.publisher,
                        source_url = excluded.source_url,
                        region = excluded.region,
                        source_type = excluded.source_type,
                        access_method = excluded.access_method,
                        licence_or_terms = excluded.licence_or_terms,
                        commercial_use_allowed = excluded.commercial_use_allowed,
                        redistribution_allowed = excluded.redistribution_allowed,
                        attribution_required = excluded.attribution_required,
                        attribution_text = excluded.attribution_text,
                        rate_limits = excluded.rate_limits,
                        refresh_method = excluded.refresh_method,
                        checked_at = excluded.checked_at,
                        status = excluded.status,
                        notes = excluded.notes,
                        updated_at = CURRENT_TIMESTAMP;
                """, {
                    "source_id": s["source_id"],
                    "name": s["name"],
                    "publisher": s.get("publisher"),
                    "source_url": s.get("source_url"),
                    "region": s.get("region"),
                    "source_type": s.get("source_type", "unknown"),
                    "access_method": s.get("access_method", "unknown"),
                    "licence_or_terms": s.get("licence_or_terms"),
                    "commercial_use_allowed": s.get("commercial_use_allowed", "unknown"),
                    "redistribution_allowed": s.get("redistribution_allowed", "unknown"),
                    "attribution_required": s.get("attribution_required", "unknown"),
                    "attribution_text": s.get("attribution_text"),
                    "rate_limits": s.get("rate_limits"),
                    "refresh_method": s.get("refresh_method"),
                    "checked_at": s.get("checked_at"),
                    "status": s.get("status", "proposed"),
                    "notes": s.get("notes"),
                })

            # Upsert places
            for p in places:
                alt_names = p.get("alternate_names_json")
                if isinstance(alt_names, list):
                    alt_names_str = json.dumps(alt_names, ensure_ascii=False)
                elif isinstance(alt_names, str):
                    alt_names_str = alt_names
                else:
                    alt_names_str = "[]"

                con.execute("""
                    INSERT INTO places (
                        place_id, canonical_name, alternate_names_json, region,
                        state_or_territory, district, locality, latitude, longitude,
                        primary_category, short_description, historical_background,
                        cultural_significance, estimated_visit_min, accessibility_notes,
                        visitor_notes, data_confidence, last_verified_at, updated_at
                    ) VALUES (
                        :place_id, :canonical_name, :alternate_names_json, :region,
                        :state_or_territory, :district, :locality, :latitude, :longitude,
                        :primary_category, :short_description, :historical_background,
                        :cultural_significance, :estimated_visit_min, :accessibility_notes,
                        :visitor_notes, :data_confidence, :last_verified_at, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT(place_id) DO UPDATE SET
                        canonical_name = excluded.canonical_name,
                        alternate_names_json = excluded.alternate_names_json,
                        region = excluded.region,
                        state_or_territory = excluded.state_or_territory,
                        district = excluded.district,
                        locality = excluded.locality,
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        primary_category = excluded.primary_category,
                        short_description = excluded.short_description,
                        historical_background = excluded.historical_background,
                        cultural_significance = excluded.cultural_significance,
                        estimated_visit_min = excluded.estimated_visit_min,
                        accessibility_notes = excluded.accessibility_notes,
                        visitor_notes = excluded.visitor_notes,
                        data_confidence = excluded.data_confidence,
                        last_verified_at = excluded.last_verified_at,
                        updated_at = CURRENT_TIMESTAMP;
                """, {
                    "place_id": p["place_id"],
                    "canonical_name": p["canonical_name"],
                    "alternate_names_json": alt_names_str,
                    "region": p["region"],
                    "state_or_territory": p.get("state_or_territory"),
                    "district": p.get("district"),
                    "locality": p.get("locality"),
                    "latitude": p.get("latitude"),
                    "longitude": p.get("longitude"),
                    "primary_category": p["primary_category"],
                    "short_description": p.get("short_description"),
                    "historical_background": p.get("historical_background"),
                    "cultural_significance": p.get("cultural_significance"),
                    "estimated_visit_min": p.get("estimated_visit_min"),
                    "accessibility_notes": p.get("accessibility_notes"),
                    "visitor_notes": p.get("visitor_notes"),
                    "data_confidence": p.get("data_confidence", "provisional"),
                    "last_verified_at": p.get("last_verified_at"),
                })

                # Insert categories
                categories = p.get("categories", [p["primary_category"]])
                for cat in categories:
                    is_prim = 1 if cat == p["primary_category"] else 0
                    con.execute("""
                        INSERT INTO place_categories (place_id, category, is_primary)
                        VALUES (?, ?, ?)
                        ON CONFLICT(place_id, category) DO UPDATE SET is_primary = excluded.is_primary;
                    """, (p["place_id"], cat, is_prim))

                # Insert source claims
                for i, c in enumerate(p.get("claims", [])):
                    claim_id = c.get("claim_id") or f"{p['place_id']}_c_{i+1}"
                    con.execute("""
                        INSERT INTO source_claims (
                            claim_id, place_id, source_id, field_name, claim_text,
                            source_quote_or_excerpt, source_published_at, retrieved_at,
                            last_verified_at, confidence, notes
                        ) VALUES (
                            :claim_id, :place_id, :source_id, :field_name, :claim_text,
                            :source_quote_or_excerpt, :source_published_at, :retrieved_at,
                            :last_verified_at, :confidence, :notes
                        )
                        ON CONFLICT(claim_id) DO UPDATE SET
                            field_name = excluded.field_name,
                            claim_text = excluded.claim_text,
                            source_quote_or_excerpt = excluded.source_quote_or_excerpt,
                            source_published_at = excluded.source_published_at,
                            retrieved_at = excluded.retrieved_at,
                            last_verified_at = excluded.last_verified_at,
                            confidence = excluded.confidence,
                            notes = excluded.notes;
                    """, {
                        "claim_id": claim_id,
                        "place_id": p["place_id"],
                        "source_id": c["source_id"],
                        "field_name": c["field_name"],
                        "claim_text": c["claim_text"],
                        "source_quote_or_excerpt": c.get("source_quote_or_excerpt"),
                        "source_published_at": c.get("source_published_at"),
                        "retrieved_at": c.get("retrieved_at", "2026-10-17"),
                        "last_verified_at": c.get("last_verified_at"),
                        "confidence": c.get("confidence", "provisional"),
                        "notes": c.get("notes"),
                    })

                # Insert visitor details if available
                v_det = p.get("visitor_details")
                if v_det:
                    con.execute("""
                        INSERT INTO visitor_details (
                            place_id, opening_hours_json, entry_fee_amount, entry_fee_currency,
                            fee_notes, seasonality_notes, contact_or_booking_url, details_verified_at,
                            details_source_claim_id
                        ) VALUES (
                            :place_id, :opening_hours_json, :entry_fee_amount, :entry_fee_currency,
                            :fee_notes, :seasonality_notes, :contact_or_booking_url, :details_verified_at,
                            :details_source_claim_id
                        )
                        ON CONFLICT(place_id) DO UPDATE SET
                            opening_hours_json = excluded.opening_hours_json,
                            entry_fee_amount = excluded.entry_fee_amount,
                            entry_fee_currency = excluded.entry_fee_currency,
                            fee_notes = excluded.fee_notes,
                            seasonality_notes = excluded.seasonality_notes,
                            contact_or_booking_url = excluded.contact_or_booking_url,
                            details_verified_at = excluded.details_verified_at,
                            details_source_claim_id = excluded.details_source_claim_id;
                    """, {
                        "place_id": p["place_id"],
                        "opening_hours_json": v_det.get("opening_hours_json"),
                        "entry_fee_amount": v_det.get("entry_fee_amount"),
                        "entry_fee_currency": v_det.get("entry_fee_currency", "INR"),
                        "fee_notes": v_det.get("fee_notes"),
                        "seasonality_notes": v_det.get("seasonality_notes"),
                        "contact_or_booking_url": v_det.get("contact_or_booking_url"),
                        "details_verified_at": v_det.get("details_verified_at"),
                        "details_source_claim_id": v_det.get("details_source_claim_id"),
                    })

        integrity = con.execute("PRAGMA integrity_check;").fetchone()[0]
        if integrity != "ok":
            raise RuntimeError(f"Database integrity check failed post-ingestion: {integrity}")

        print(f"Successfully ingested {len(sources)} sources and {len(places)} places into {db_path}.")
    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(description="YatraOS data ingestion pipeline.")
    parser.add_argument("--db", type=Path, default=Path("data/yatraos.sqlite"), help="Target SQLite database")
    parser.add_argument(
        "--sources", type=Path, default=Path("data/source_registry.csv"), help="Source registry CSV file"
    )
    parser.add_argument(
        "--places", type=Path, default=Path("data/processed/pilot_places.json"), help="Cleaned places JSON file"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate only without writing to database")
    args = parser.parse_args()

    sources = load_sources_from_csv(args.sources)
    places = load_places_from_json(args.places)
    ingest_data(args.db, sources, places, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
