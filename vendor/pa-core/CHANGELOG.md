# Changelog

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
