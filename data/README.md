# data/

- claims.json: canonical claims ledger (time-map stops, court places UM-P01..P05, top-level curley_area_km2).
- eras.json: sketched era polygons.
- places.json: Map places for the time map. Coordinates must be unique (checked by tools/build.py). kind: label | landmark | assembly | court | lake. private: true -> drawn as an approximate dashed area, no precise pin. learned_land = learned-family townland, not private.
- true-boundary.geojson: empty until Garry Lohan's survey; the map shows "Boundary survey coming soon" while empty.
- d4m/: pa-core associations (A_claim, A_place, A_era, A_prov TSVs), written by tools/build.py from the three JSON files above via the vendored pa-core json-claims adapter (vendor/pa-core, pinned v0.3.0). Do not edit the TSVs by hand: edit the JSON and run python3 tools/build.py. schema.json declares column types; adapter.json maps the JSON to rows. Inspect a row: python3 vendor/pa-core/pa_d4m.py inspect claim:UM-C08 data/d4m --schema data/d4m/schema.json
