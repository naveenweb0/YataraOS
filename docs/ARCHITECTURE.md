# YatraOS Architecture (Initial)

## Product goal

Plan feasible multi-day trips across North India, prioritising heritage and culture. Users choose categories and places one at a time, then review a day-by-day itinerary on a map.

## Runtime boundaries

- **Local AI** interprets user preferences and explains sourced information.
- **Database/retrieval** is the source of truth for places and facts.
- **Planner** applies hard constraints such as visit duration, opening hours, travel time, and day boundaries.
- **Routing engine** calculates routes from geographic data; the language model must not invent travel times.
- **Map UI** renders places, categories, routes, and itinerary order.
- **Trip exporter** packages only selected places, itinerary, and required map data for later Android use.

## Data flow

1. Source registry records the source, owner, access method, terms/licence, refresh approach, and review status.
2. Importer obtains permitted material.
3. Normaliser resolves names, coordinates, categories, and duplicates.
4. Validator checks required fields, source links, licences, and confidence.
5. SQLite stores places, source records, factual claims, categories, and itineraries.
6. Retrieval returns relevant facts with provenance.
7. AI produces a structured candidate plan.
8. Deterministic planner checks feasibility.
9. User reviews and approves the final itinerary.

## Offline-first contract

After preparation, the following must work without internet:
- search local place records;
- retrieve stored descriptions and source metadata;
- run the selected local model;
- display downloaded map assets;
- calculate routes if local routing data is installed;
- open and edit saved itineraries.

Live opening hours, road closures, weather, and event information cannot be assumed current offline. Show the last-verified timestamp and an uncertainty indicator.

## Initial regional scope

Pilot: Punjab, Chandigarh, and Himachal Pradesh.
Designed to expand to Haryana, Delhi NCR, Uttarakhand, Jammu region, Rajasthan, Uttar Pradesh, and other destinations as data sources are verified.

## Non-goals for the first milestone

- Training a foundation model from scratch.
- Scraping every site without checking terms.
- Android app or group messaging.
- Forcibly locking other people's phones.
- Guaranteeing route times under changing mountain-road conditions.
