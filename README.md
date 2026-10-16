# YatraOS

A local-first AI travel planner focused on heritage and cultural tourism across North India.

## First milestone

- Establish the project structure and data governance.
- Build a source-aware SQLite database.
- Start with Punjab, Chandigarh, and Himachal Pradesh.
- Expand to other North Indian regions using the same schema.
- Add local AI, routing, and maps only after the data foundation is validated.

## Principles

1. Local-first: no hosted AI API is required for core planning.
2. Source-aware: every important fact should be traceable to a source.
3. Licence-aware: record source terms and media licences before importing or redistributing data.
4. Honest uncertainty: unknown hours, fees, or historical details remain unknown.
5. Offline-ready: the database and trip package must work without internet after preparation.
6. Human-confirmed: the user approves the final itinerary.

## Proposed stack

- Desktop UI: React + TypeScript (later milestone)
- Local API and ingestion: Python + FastAPI (later milestone)
- Database: SQLite + FTS5
- Local model runtime: Ollama, after hardware/model benchmark
- Maps: MapLibre with appropriately licensed local map assets
- Routing: local routing engine after a small-area proof of concept

## Project layout

- `docs/` architecture and decisions
- `data/source_registry.csv` source inventory template
- `data/imports/` temporary incoming data (do not commit large datasets)
- `data/processed/` cleaned data snapshots (do not commit large datasets)
- `database/` schema and migrations
- `scripts/` future ingestion and validation scripts
- `tests/` data and itinerary quality tests
- `app/` future desktop application
- `trip_packages/` generated trip exports (keep private; do not commit by default)

## First steps

1. Read `docs/DATA_POLICY.md`.
2. Fill in `data/source_registry.csv` with the exact sources you intend to use.
3. Review `database/schema.sql`.
4. Create the local database and ingestion scripts only after the source/field design is reviewed.
5. Start with a small manually verified pilot dataset before bulk collection.

## Important

Do not scrape sites indiscriminately. Respect each source's terms, rate limits, robots rules where applicable, copyright, and database licences. Keep attribution and provenance. OpenStreetMap data has ODbL requirements; map tile services have separate usage policies.
