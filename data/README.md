# data/

- claims.json: canonical claims ledger (time-map stops, court places UM-P01..P05, top-level curley_area_km2).
- eras.json: sketched era polygons.
- places.json: Map places for the time map. Coordinates must be unique (checked by tools/build.py). kind: label | landmark | assembly | court | lake. private: true -> drawn as an approximate dashed area, no precise pin. learned_land = learned-family townland, not private.
- true-boundary.geojson: empty until Garry Lohan's survey; the map shows "Boundary survey coming soon" while empty.
