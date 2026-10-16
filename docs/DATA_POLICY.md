# Data Collection and Provenance Policy

## Before importing a source

Record:
- source name and publisher;
- source URL or dataset identifier;
- access method (download, documented API, permitted page collection, manual entry);
- terms of use and licence;
- whether commercial use and redistribution are allowed;
- attribution wording required;
- access/rate limits;
- date checked and refresh interval;
- status: proposed, approved, blocked, or needs legal review.

## Collection rules

- Prefer official open datasets and explicitly reusable publications.
- Use documented APIs or bulk downloads where provided.
- Respect terms, rate limits, robots rules where applicable, copyright, privacy, and database rights.
- Do not bulk-copy Google Maps content, Google reviews, directions, or map tiles.
- Do not assume that publicly viewable means reusable or trainable.
- Keep a record of the origin and licence of every image.
- Never remove attribution from OpenStreetMap-derived data; follow ODbL requirements.
- Avoid collecting personal data about individual visitors.
- Do not invent missing facts.

## Fact quality

Each fact should have a source, last-verified date, and confidence:
- `verified`: checked against a reliable source;
- `provisional`: sourced but not independently checked;
- `conflicting`: sources disagree;
- `unknown`: not available.

Unknown hours, entry fees, accessibility details, or historical claims should stay unknown until verified.

## Refresh strategy

Use a staged import:
1. download to a temporary location;
2. validate file integrity and licence metadata;
3. normalise and deduplicate;
4. run quality checks;
5. create a versioned snapshot;
6. replace the active dataset only after validation passes.

Keep old snapshots until the new one is confirmed usable.
