"""
Tests for YatraOS Data Validation Engine.
Verifies source status rejection, redistribution gates, required fields, coordinate ranges, and provenance.
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to sys.path
sys.path.insert(0, str(Path("scripts").resolve()))

from validator import (
    validate_source,
    validate_place,
    validate_dataset,
    ALLOWED_CATEGORIES,
)


@pytest.fixture
def valid_source():
    return {
        "source_id": "asi_national_monuments",
        "name": "Archaeological Survey of India",
        "publisher": "Ministry of Culture, Govt of India",
        "source_url": "https://asi.nic.in/monuments-of-national-importance/",
        "region": "North India",
        "source_type": "government_registry",
        "access_method": "public_portal",
        "licence_or_terms": "Government Open Data Policy",
        "commercial_use_allowed": "conditional",
        "redistribution_allowed": "yes",
        "attribution_required": "yes",
        "attribution_text": "Source: ASI, Government of India",
        "checked_at": "2026-10-17",
        "status": "approved",
    }


@pytest.fixture
def valid_place():
    return {
        "place_id": "hp_kangra_fort",
        "canonical_name": "Kangra Fort",
        "alternate_names_json": ["Nagarkot", "Kot Kangra"],
        "region": "Himachal Pradesh",
        "state_or_territory": "Himachal Pradesh",
        "district": "Kangra",
        "locality": "Old Kangra",
        "latitude": 32.0911,
        "longitude": 76.2558,
        "primary_category": "Fort",
        "short_description": "Ancient hilltop fort overlooking the Banganga and Manjhi rivers.",
        "historical_background": "Associated with the Katoch dynasty, mentioned in Mahabharata references.",
        "cultural_significance": "One of the oldest recorded forts in the Indian subcontinent.",
        "estimated_visit_min": 120,
        "data_confidence": "verified",
        "last_verified_at": "2026-10-17",
        "claims": [
            {
                "claim_id": "c_kangra_asi",
                "source_id": "asi_national_monuments",
                "field_name": "historical_background",
                "claim_text": "Protected Monument of National Importance under Archaeological Survey of India (N-HP-20).",
                "confidence": "verified",
                "retrieved_at": "2026-10-17",
            }
        ],
    }


def test_unapproved_source_rejected(valid_source):
    """Sources with status other than 'approved' must be rejected for production."""
    for bad_status in ["proposed", "blocked", "needs_review", "invalid_status"]:
        src = dict(valid_source, status=bad_status)
        errors = validate_source(src, for_production=True)
        assert any(e.field_name == "status" for e in errors), f"Status {bad_status} should fail validation"


def test_redistribution_not_allowed_rejected(valid_source):
    """Sources where redistribution is 'no' or 'unknown' must be rejected for production."""
    for bad_redist in ["no", "unknown"]:
        src = dict(valid_source, redistribution_allowed=bad_redist)
        errors = validate_source(src, for_production=True)
        assert any(e.field_name == "redistribution_allowed" for e in errors)


def test_missing_attribution_text_rejected(valid_source):
    """When attribution_required is 'yes', attribution_text cannot be blank."""
    src = dict(valid_source, attribution_required="yes", attribution_text="")
    errors = validate_source(src, for_production=True)
    assert any(e.field_name == "attribution_text" for e in errors)


def test_place_missing_required_fields(valid_place):
    """Missing canonical_name or region must trigger validation errors."""
    pl_no_name = dict(valid_place, canonical_name="")
    errs, _ = validate_place(pl_no_name, {"asi_national_monuments"})
    assert any(e.field_name == "canonical_name" for e in errs)

    pl_no_region = dict(valid_place, region="")
    errs, _ = validate_place(pl_no_region, {"asi_national_monuments"})
    assert any(e.field_name == "region" for e in errs)


def test_place_invalid_confidence(valid_place):
    """Invalid data_confidence strings must be rejected."""
    pl_bad_conf = dict(valid_place, data_confidence="definitely_true")
    errs, _ = validate_place(pl_bad_conf, {"asi_national_monuments"})
    assert any(e.field_name == "data_confidence" for e in errs)


def test_place_invalid_coordinate_ranges(valid_place):
    """Latitude > 90 or Longitude > 180 must trigger validation errors."""
    pl_bad_lat = dict(valid_place, latitude=95.0)
    errs, _ = validate_place(pl_bad_lat, {"asi_national_monuments"})
    assert any(e.field_name == "latitude" for e in errs)

    pl_bad_lon = dict(valid_place, longitude=195.0)
    errs, _ = validate_place(pl_bad_lon, {"asi_national_monuments"})
    assert any(e.field_name == "longitude" for e in errs)


def test_place_provenance_rejected_if_source_unapproved(valid_place):
    """Claims citing an unapproved or unregistered source must be rejected."""
    approved_sources = {"some_other_approved_source"}
    errs, _ = validate_place(valid_place, approved_sources)
    assert any(e.field_name == "source_id" for e in errs)


def test_place_provenance_mandatory(valid_place):
    """Places with 0 claims must be rejected in production mode."""
    pl_no_claims = dict(valid_place, claims=[])
    errs, _ = validate_place(pl_no_claims, {"asi_national_monuments"}, for_production=True)
    assert any(e.field_name == "claims" for e in errs)


def test_valid_dataset_passes(valid_source, valid_place):
    """A consistent source and place pair must pass dataset validation with 0 errors."""
    report = validate_dataset([valid_source], [valid_place], for_production=True)
    assert report.is_valid
    assert len(report.errors) == 0
