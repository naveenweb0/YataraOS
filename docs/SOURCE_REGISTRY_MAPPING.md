# Source Registry & Database Schema Reconciliation

This document specifies the exact mapping between [`data/source_registry.csv`](file:///Users/naveenmaan/Projects/yatraos/data/source_registry.csv) and the SQLite [`sources`](file:///Users/naveenmaan/Projects/yatraos/database/schema.sql) table in YatraOS.

## Field Mapping

| CSV Column | SQLite Column (`sources`) | Type | Nullable | Permitted Values / Format | Description & Policy Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `source_id` | `source_id` | `TEXT` | `NO` (PK) | Lowercase slug, e.g. `asi_national_monuments` | Unique identifier for provenance tracking across all claims. |
| `name` *(or `source_name`)* | `name` | `TEXT` | `NO` | Descriptive string | Full official title of the publication, portal, or dataset. |
| `publisher` | `publisher` | `TEXT` | `YES` | Organisation or authority | Publishing entity (e.g. "Archaeological Survey of India"). |
| `source_url` | `source_url` | `TEXT` | `YES` | Valid URL | Canonical web location or dataset DOI. |
| `region` | `region` | `TEXT` | `YES` | Region name | Geographic coverage (e.g. `Punjab`, `Chandigarh`, `Himachal Pradesh`, `Pan-India`). |
| `source_type` | `source_type` | `TEXT` | `NO` | `government_registry`, `official_tourism_board`, `academic`, `open_data`, `unknown` | Classification of the source origin. |
| `access_method` | `access_method` | `TEXT` | `NO` | `public_portal`, `bulk_download`, `documented_api`, `manual_entry`, `unknown` | Ingestion vector. Scraping without terms review is blocked. |
| `licence_or_terms` | `licence_or_terms` | `TEXT` | `YES` | License identifier or summary | Explicit licence (e.g. `ODbL`, `NDSAP/Open Govt Data`, `CC-BY-4.0`, `Website Terms of Use`). |
| `commercial_use_allowed` | `commercial_use_allowed` | `TEXT` | `NO` | `'yes'`, `'no'`, `'conditional'`, `'unknown'` | Derived from source licence review. |
| `redistribution_allowed` | `redistribution_allowed` | `TEXT` | `NO` | `'yes'`, `'no'`, `'conditional'`, `'unknown'` | Mandatory check: Must be `'yes'` (or vetted `'conditional'`) for offline package distribution. |
| `attribution_required` | `attribution_required` | `TEXT` | `NO` | `'yes'`, `'no'`, `'conditional'`, `'unknown'` | Indicates whether attribution is legally or contractually mandated. |
| `attribution_text` | `attribution_text` | `TEXT` | `YES` | Prescribed wording | Exact attribution notice to be shown to users and included in exports. |
| `rate_limits` | `rate_limits` | `TEXT` | `YES` | Notes on rate limits | Any automated collection restrictions. |
| `refresh_method` | `refresh_method` | `TEXT` | `YES` | Refresh frequency | E.g. `manual_annual`, `quarterly_api_pull`. |
| `checked_at` *(or `checked_on`)* | `checked_at` | `TEXT` | `YES` | `YYYY-MM-DD` | Timestamp when terms and availability were last independently reviewed. |
| `status` | `status` | `TEXT` | `NO` | `'proposed'`, `'approved'`, `'blocked'`, `'needs_review'` | **Gatekeeper field**: Only `'approved'` sources may be used in production datasets. |
| `notes` | `notes` | `TEXT` | `YES` | Freeform text | Legal review notes, caveats, or contact information. |

## Interoperability Rules

1. **Backwards-Compatibility in Ingestion:**
   The ingestion tool accepts either `name` or `source_name`, and either `checked_at` or `checked_on`.
2. **Attribution Handling:**
   `attribution_required` records whether attribution is needed; `attribution_text` records the exact wording required by the source publisher.
3. **Region Scope:**
   The `region` column in `sources` allows filtering sources relevant to specific North Indian jurisdictions (e.g. Himachal Pradesh vs. Punjab).
