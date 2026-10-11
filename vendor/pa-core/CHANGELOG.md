# Changelog

## v0.1.0 (2026-10-11)
- First release, extracted with the PA Uí Mhaine migration.
- Schema version 1: TSV triples, backslash escaping (\t \n \r \| \\), \N null, per-column types,
  deterministic sorted serializer.
- Required A_prov (source, status, fetched_at, sha256, code_sha); reserved prov| meta| sys| claim|.
- visibility|public / restricted; default-deny export with allowlist and hard-deny fields.
- Core status vocabulary, extendable per site.
- CLI pa-d4m: ingest (json-claims), validate (+ round-trip), export, diff (relative drop guard, strict), inspect.
