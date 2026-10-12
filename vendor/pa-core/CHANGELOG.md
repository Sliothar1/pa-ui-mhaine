# Changelog

## Unreleased
- (nothing yet)

## v0.3.0 (2026-10-11)
- docs/CONTRACT.md: the stable interchange contract (types, escaping, keys, provenance, visibility,
  ordering, schema_version, export permissions) and release gates.
- docs/EDGES.md + `validate --edges`: edge-row convention (`edge:<id>` from/to/role/start/end,
  `role:<slug>` and `match:<id>` entity rows) and per-assertion provenance via `claim|<id>`.
  Golden fixtures in tests/fixtures/edges (sample player, club spell, match).
- `pa-d4m parity`: byte equality, schema diff (rows/cols/types/visibility), canonical semantic
  hash, negative control; docs/PARITY-GATE.md.
- Migration note: schema_version stays 1; no format change, new checks are opt-in. Sites stay
  pinned at v0.2.0 until they upgrade with a parity record.
- Core column `meta|schema_version` (int); validation fails if a row carries a value other than
  the schema version this pa-core reads.
- Tests: JSON → TSV → JSON round trip, and a mutation suite (id, number, provenance-only field;
  the provenance-only change must leave the outputs unchanged). 42 tests.
- Docs: docs/COMPATIBILITY.md (site → pinned version, vendored-file checksums).

## v0.2.1 (2026-10-11)
- Licence only: relicensed from AGPL-3.0 to Apache-2.0 by the sole copyright holder, Dr Garry Lohan.
  LICENSE is the unmodified Apache-2.0 text; NOTICE, README and pyproject updated. No code or data-contract change.

## v0.2.0 (2026-10-11)
- New `tabular` adapter (CSV/TSV with header; per-id-prefix source templates; optional JSON metadata
  document; byte-exact round-trip check). First consumer: PA Réalt.
- New column type `json_ordered` (key order kept). Export no longer re-sorts keys inside values.
- A row may now live in several assocs (D4M style); visibility is checked once per row across them,
  and export merges a row's columns.
- Col key fields may contain capitals (Réalt sky events `WS_rise|3200BC`).
- Migration note: schema_version stays 1. Every v0.1.0 dataset is still valid (the changes add a
  type and relax one rule). Sites pinned to v0.1.0 (PA Uí Mhaine) need no change.

## v0.1.0 (2026-10-11)
- First release, extracted with the PA Uí Mhaine migration.
- Schema version 1: TSV triples, backslash escaping (\t \n \r \| \\), \N null, per-column types,
  deterministic sorted serializer.
- Required A_prov (source, status, fetched_at, sha256, code_sha); reserved prov| meta| sys| claim|.
- visibility|public / restricted; default-deny export with allowlist and hard-deny fields.
- Core status vocabulary, extendable per site.
- CLI pa-d4m: ingest (json-claims), validate (+ round-trip), export, diff (relative drop guard, strict), inspect.
