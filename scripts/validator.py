"""
YatraOS Data Validation Engine.
Strictly enforces data governance, provenance, licensing, and geographic constraints.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Any, Optional

ALLOWED_SOURCE_STATUSES = {"proposed", "approved", "blocked", "needs_review"}
ALLOWED_PERMISSIONS = {"yes", "no", "conditional", "unknown"}
ALLOWED_CONFIDENCES = {"verified", "provisional", "conflicting", "unknown"}

# Cultural and heritage category taxonomy
ALLOWED_CATEGORIES = {
    "Fort",
    "Gurudwara",
    "Temple",
    "Palace",
    "Heritage Site",
    "Museum",
    "Architectural Complex",
    "Archaeological Site",
    "Garden",
    "Monastery",
    "Monument",
    "Memorial",
}

# Regional coordinate bounding boxes for sanity checks
REGIONAL_BOUNDS = {
    "Punjab": {"lat_min": 29.5, "lat_max": 32.5, "lon_min": 73.8, "lon_max": 77.0},
    "Chandigarh": {"lat_min": 30.6, "lat_max": 30.85, "lon_min": 76.65, "lon_max": 76.85},
    "Himachal Pradesh": {"lat_min": 30.3, "lat_max": 33.3, "lon_min": 75.5, "lon_max": 79.1},
    "North India": {"lat_min": 25.0, "lat_max": 37.0, "lon_min": 71.0, "lon_max": 82.0},
}


@dataclass
class ValidationError:
    entity_type: str
    entity_id: str
    field_name: str
    message: str


@dataclass
class ValidationReport:
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_source(source: dict[str, Any], for_production: bool = True) -> list[ValidationError]:
    """Validates a source record according to data policy."""
    errors = []
    source_id = str(source.get("source_id", "")).strip()

    if not source_id:
        errors.append(ValidationError("source", "UNKNOWN", "source_id", "source_id is required."))
        return errors

    name = str(source.get("name") or source.get("source_name") or "").strip()
    if not name:
        errors.append(ValidationError("source", source_id, "name", "Source name is required."))

    status = str(source.get("status", "")).strip().lower()
    if status not in ALLOWED_SOURCE_STATUSES:
        errors.append(
            ValidationError(
                "source",
                source_id,
                "status",
                f"Invalid status '{status}'. Must be one of {sorted(ALLOWED_SOURCE_STATUSES)}.",
            )
        )
    elif for_production and status != "approved":
        errors.append(
            ValidationError(
                "source",
                source_id,
                "status",
                f"Production source must have status 'approved', but has '{status}'.",
            )
        )

    redist_allowed = str(source.get("redistribution_allowed", "")).strip().lower()
    if redist_allowed not in ALLOWED_PERMISSIONS:
        errors.append(
            ValidationError(
                "source",
                source_id,
                "redistribution_allowed",
                f"Invalid redistribution_allowed '{redist_allowed}'. Must be one of {sorted(ALLOWED_PERMISSIONS)}.",
            )
        )
    elif for_production and redist_allowed == "no":
        errors.append(
            ValidationError(
                "source",
                source_id,
                "redistribution_allowed",
                "Source redistribution is forbidden ('no'); cannot ingest into offline distribution dataset.",
            )
        )
    elif for_production and redist_allowed == "unknown":
        errors.append(
            ValidationError(
                "source",
                source_id,
                "redistribution_allowed",
                "Source redistribution permission is 'unknown'; legal review required before production ingestion.",
            )
        )

    commercial_allowed = str(source.get("commercial_use_allowed", "unknown")).strip().lower()
    if commercial_allowed not in ALLOWED_PERMISSIONS:
        errors.append(
            ValidationError(
                "source",
                source_id,
                "commercial_use_allowed",
                f"Invalid commercial_use_allowed '{commercial_allowed}'. Must be one of {sorted(ALLOWED_PERMISSIONS)}.",
            )
        )

    attr_req = str(source.get("attribution_required", "unknown")).strip().lower()
    if attr_req not in ALLOWED_PERMISSIONS:
        errors.append(
            ValidationError(
                "source",
                source_id,
                "attribution_required",
                f"Invalid attribution_required '{attr_req}'. Must be one of {sorted(ALLOWED_PERMISSIONS)}.",
            )
        )

    attr_text = str(source.get("attribution_text", "")).strip()
    if attr_req == "yes" and not attr_text:
        errors.append(
            ValidationError(
                "source",
                source_id,
                "attribution_text",
                "attribution_text must be provided when attribution_required is 'yes'.",
            )
        )

    checked_at = str(source.get("checked_at") or source.get("checked_on") or "").strip()
    if checked_at and not re.match(r"^\d{4}-\d{2}-\d{2}$", checked_at):
        errors.append(
            ValidationError(
                "source",
                source_id,
                "checked_at",
                f"checked_at '{checked_at}' must be in YYYY-MM-DD format.",
            )
        )

    return errors


def validate_place(
    place: dict[str, Any],
    approved_source_ids: set[str],
    for_production: bool = True,
) -> tuple[list[ValidationError], list[str]]:
    """Validates a place record, its coordinates, category, and source claims."""
    errors = []
    warnings = []
    place_id = str(place.get("place_id", "")).strip()

    if not place_id:
        errors.append(ValidationError("place", "UNKNOWN", "place_id", "place_id is required."))
        return errors, warnings

    # Required fields
    canonical_name = str(place.get("canonical_name", "")).strip()
    if not canonical_name:
        errors.append(ValidationError("place", place_id, "canonical_name", "canonical_name is required."))

    region = str(place.get("region", "")).strip()
    if not region:
        errors.append(ValidationError("place", place_id, "region", "region is required."))

    primary_category = str(place.get("primary_category", "")).strip()
    if not primary_category:
        errors.append(ValidationError("place", place_id, "primary_category", "primary_category is required."))
    elif primary_category not in ALLOWED_CATEGORIES:
        warnings.append(
            f"Place {place_id} category '{primary_category}' is not in standard taxonomy {sorted(ALLOWED_CATEGORIES)}."
        )

    confidence = str(place.get("data_confidence", "provisional")).strip().lower()
    if confidence not in ALLOWED_CONFIDENCES:
        errors.append(
            ValidationError(
                "place",
                place_id,
                "data_confidence",
                f"Invalid data_confidence '{confidence}'. Must be one of {sorted(ALLOWED_CONFIDENCES)}.",
            )
        )

    # Coordinates
    lat = place.get("latitude")
    lon = place.get("longitude")

    if lat is not None:
        try:
            lat_f = float(lat)
            if lat_f < -90.0 or lat_f > 90.0:
                errors.append(
                    ValidationError("place", place_id, "latitude", f"Latitude {lat_f} out of range [-90, 90].")
                )
        except (ValueError, TypeError):
            errors.append(ValidationError("place", place_id, "latitude", f"Invalid latitude format: {lat}"))

    if lon is not None:
        try:
            lon_f = float(lon)
            if lon_f < -180.0 or lon_f > 180.0:
                errors.append(
                    ValidationError("place", place_id, "longitude", f"Longitude {lon_f} out of range [-180, 180].")
                )
        except (ValueError, TypeError):
            errors.append(ValidationError("place", place_id, "longitude", f"Invalid longitude format: {lon}"))

    # Regional bounding box check
    if lat is not None and lon is not None and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        bounds = REGIONAL_BOUNDS.get(region) or REGIONAL_BOUNDS.get("North India")
        if bounds:
            if not (bounds["lat_min"] <= lat <= bounds["lat_max"] and bounds["lon_min"] <= lon <= bounds["lon_max"]):
                warnings.append(
                    f"Place {place_id} ({lat}, {lon}) falls outside typical geographic bounds for region '{region}'."
                )

    # Estimated visit duration
    est_visit = place.get("estimated_visit_min")
    if est_visit is not None:
        if not isinstance(est_visit, int) or est_visit < 0:
            errors.append(
                ValidationError(
                    "place", place_id, "estimated_visit_min", "estimated_visit_min must be a non-negative integer."
                )
            )

    # Provenance claims check
    claims = place.get("claims", [])
    if for_production and not claims:
        errors.append(
            ValidationError(
                "place",
                place_id,
                "claims",
                "Place must have at least one source claim verifying factual claims.",
            )
        )

    for i, claim in enumerate(claims):
        claim_id = claim.get("claim_id") or f"{place_id}_claim_{i+1}"
        source_id = claim.get("source_id", "")
        if not source_id:
            errors.append(ValidationError("claim", claim_id, "source_id", "Claim source_id is required."))
        elif source_id not in approved_source_ids:
            errors.append(
                ValidationError(
                    "claim",
                    claim_id,
                    "source_id",
                    f"Claim references source '{source_id}' which is not in the approved sources registry.",
                )
            )

        field_name = claim.get("field_name", "")
        if not field_name:
            errors.append(ValidationError("claim", claim_id, "field_name", "Claim field_name is required."))

        claim_text = claim.get("claim_text", "")
        if not claim_text:
            errors.append(ValidationError("claim", claim_id, "claim_text", "Claim claim_text is required."))

        claim_conf = str(claim.get("confidence", "provisional")).strip().lower()
        if claim_conf not in ALLOWED_CONFIDENCES:
            errors.append(
                ValidationError(
                    "claim",
                    claim_id,
                    "confidence",
                    f"Invalid claim confidence '{claim_conf}'. Must be one of {sorted(ALLOWED_CONFIDENCES)}.",
                )
            )

    # Visitor details check
    vis_details = place.get("visitor_details")
    if vis_details:
        opening_hours = vis_details.get("opening_hours_json")
        if opening_hours is not None and isinstance(opening_hours, str):
            try:
                json.loads(opening_hours)
            except json.JSONDecodeError:
                errors.append(
                    ValidationError(
                        "visitor_details", place_id, "opening_hours_json", "opening_hours_json must be valid JSON."
                    )
                )

        fee = vis_details.get("entry_fee_amount")
        if fee is not None:
            if not isinstance(fee, (int, float)) or fee < 0:
                errors.append(
                    ValidationError(
                        "visitor_details", place_id, "entry_fee_amount", "entry_fee_amount must be non-negative."
                    )
                )

    return errors, warnings


def validate_dataset(
    sources: list[dict[str, Any]],
    places: list[dict[str, Any]],
    for_production: bool = True,
) -> ValidationReport:
    """Validates an entire dataset of sources and places."""
    report = ValidationReport()

    # Validate sources
    approved_source_ids = set()
    for src in sources:
        src_errors = validate_source(src, for_production=for_production)
        report.errors.extend(src_errors)
        if not src_errors and src.get("status") == "approved":
            approved_source_ids.add(src["source_id"])

    # Validate places
    for pl in places:
        pl_errors, pl_warnings = validate_place(pl, approved_source_ids, for_production=for_production)
        report.errors.extend(pl_errors)
        report.warnings.extend(pl_warnings)

    return report
