# pa-core data contract, schema version 1 (pa-core v0.2.0)

The shared interchange format for PA sites. Each site keeps its own editable source (JSON, CSV,
fetch scripts); the associations below are what the core validates, diffs and exports.
Stdlib Python only; no D4M runtime in the browser.

## 1. Files
- One file per association: `data/d4m/A_<concern>.tsv` (`A_` + lowercase name).
- UTF-8, LF line ends, no BOM, no header. One triple per line: `row \t col \t val`.
- `A_prov.tsv` is required in every dataset.
- The serializer is deterministic: triples sorted by (row key parts, col key parts) in Unicode
  code-point order, trailing newline. Same data in, same bytes out.

## 2. Escaping
Applied to row, col and val. Backslash is the only escape character:

| Character | Written as |
|---|---|
| backslash `\` | `\\` |
| tab | `\t` |
| newline | `\n` |
| carriage return | `\r` (extra to the review spec, so no raw CR can ever appear) |
| pipe `\|` | `\|` |

Any other `\x` sequence, or a trailing lone backslash, is an error. Null is the token `\N`;
an escaped string can never produce it (a literal backslash-N is written `\\N`). The empty string
is an empty field. Null and absent are different: absent means the column is not set for that row.
Round-trip tests: `tests/test_core.py` (`Escaping`).

## 3. Keys
- **Row key**: `type:id[|qualifier]`. `type` is lowercase `[a-z][a-z0-9_]*`. `id` matches
  `[A-Za-z0-9][A-Za-z0-9._:+-]*` (case kept: Uí Mhaine ids are `UM-C01`; Réalt rows become
  `mon:SMR123`). The optional qualifier is typically an ISO UTC time (`2026-10-11T00:00:00Z`).
- **Col key**: `field[|qualifier]`, field `[A-Za-z_][A-Za-z0-9_]*` (v0.2.0 allows capitals, e.g. Réalt `WS_rise|3200BC`; prefer lowercase for new fields). An unescaped `|` is the separator.
- Set membership / exploded values: `field|value` with value `1` (type `flag`), e.g. `tag|harbour`.
  Flags are their own columns and are never confused with a numeric value of 1.
- A row may appear in several associations (e.g. `A_mon`, `A_prop`, `A_sky`), but its visibility flag
  is set exactly once across them, and it has one `A_prov` row. A `(row, col)` pair appears at most once
  per association. (v0.1.0 required one home per row; relaxed in v0.2.0.)

## 4. Types (per column, from the site schema file)
`str`, `int`, `float`, `bool` (`true`/`false`), `json` (compact, sorted keys), `json_ordered` (compact,
key order kept; v0.2.0, for published metadata whose key order is part of the output bytes), `flag` (must be `1`).
A trailing `?` makes the column nullable. Values must be in canonical form (no `007` in an `int`
column: ids such as `007` are declared `str` and stay strings). Every column used must be declared:
undeclared columns fail validation.

Site schema file (`data/d4m/schema.json`):
```json
{"schema_version": 1,
 "status_vocabulary_extra": ["annal identified, entry not pinned"],
 "prov_exempt_types": ["status", "ledger"],
 "assocs": {"A_claim": {"columns": {"zoom": "int", "pinned": "str?"},
                        "required": {"claim": ["id", "date", "status"]}}}}
```

## 5. Reserved namespaces
`prov|`, `meta|`, `sys|`, `claim|` and `visibility|` belong to the core; a site schema may not declare
them (a namespace is the prefix *with* its pipe: a bare field called `claim`, such as the Uí Mhaine
claim text, is an ordinary column). Core columns:

| Column | Type | Where | Meaning |
|---|---|---|---|
| `prov|source` | str | A_prov | URL or citation (required) |
| `prov|status` | str | A_prov | status vocabulary term (required, except prov-exempt config types) |
| `prov|fetched_at` | str | A_prov | UTC `YYYY-MM-DDTHH:MM:SSZ` when this content was ingested (required) |
| `prov|sha256` | str | A_prov | sha256 of the canonical JSON of the source record (required) |
| `prov|code_sha` | str | A_prov | code that produced it, e.g. `pa-core-0.1.0+<12 hex>` (required) |
| `prov|pinned` | str? | A_prov | page / annal / entry when pinned |
| `prov|confidence` | str? | A_prov | free-text confidence |
| `meta|order` | int | data | position in the editable source (lists keep their order) |
| `meta|note` | str? | data | maintainer note |
| `visibility|public` / `visibility|restricted` | flag | data | exactly one per row |
| `sys|*` | str? | data | tool bookkeeping, never exported |
| `claim|<row>` | flag | data | link to a claim row (used by `inspect`) |

`prov|*` columns live only in `A_prov`; `A_prov` holds only `prov|*`. Every data row needs an
`A_prov` row with the five required fields. Batch provenance rows use `batch:<id>`.
`fetched_at` is kept when a record's sha256 is unchanged, so re-ingesting unchanged data is
byte-identical. Consent, age band and similar personal data never go in `A_prov`; they live in a
separate restricted table (e.g. `A_consent`) and are hard-denied at export.

## 6. Status vocabulary
Core terms: `pinned`, `partly pinned`, `annal identified`, `year only`, `needs source`, `tradition`,
`interpretation`. A site adds terms with `status_vocabulary_extra`. Adapters map a free-text record
status to the longest vocabulary term it starts with (`pinned · private land` -> `pinned`);
anything else needs an explicit `prov_status_overrides` entry in the adapter config.

## 6b. Adapters
- `json-claims` (v0.1.0): hand-edited JSON ledgers (lists of records, a status vocabulary, top-level
  scalars, id-keyed mappings). Round-trip check: canonical-JSON equality with the source.
- `tabular` (v0.2.0): one CSV or TSV table with a header, one record per line, cells typed by the
  schema; `prov|source` from a template (`{id}`, optional per-id-prefix templates); an optional whole
  JSON document stored as one `json_ordered` cell (dataset metadata). Round-trip check: the table is
  reproduced byte for byte by `tabular.table_text` (Python csv, LF, minimal quoting).

## 7. Export (default deny)
`pa-d4m export --allow export.allow.json --to site/data/` writes `<type>.json` (`{row: {col: val}}`)
plus `index.json`. A row's columns from all its associations are merged. A row is exported only if it is `visibility|public`, its type is in the allowlist,
and it is not a prov-exempt config type; only allow-listed columns go out (`"*"` = all declared
non-core columns). `visibility|*`, `sys|*` and HARD_DENY fields (`consent`, `age_band`, `age`,
`dob`, `birth_date`, `email`, `phone`, `address`, `minor`, `guardian`, `private_text`, `ocr_private`)
are never emitted, even when allow-listed. Export refuses an invalid dataset.

## 8. Commands
```
pa-d4m ingest json-claims|tabular --config data/d4m/adapter.json --schema data/d4m/schema.json --out data/d4m [--dry-run]
pa-d4m validate data/d4m --schema data/d4m/schema.json [--roundtrip data/d4m/adapter.json]
pa-d4m export data/d4m --schema ... --allow ... --to site/data
pa-d4m diff git:origin/main data/d4m [--max-drop 10] [--strict]
pa-d4m inspect claim:UM-C08 data/d4m --schema data/d4m/schema.json
```
`diff` reports rows added/removed per type and triples added/removed/changed per assoc. It fails
when any row type drops by more than `--max-drop` percent (relative seed guard); `--strict` fails on
any triple change (use it for pure refactors). A side is a directory or `git:<ref>`.

## 9. Versioning
Sites vendor pa-core at `vendor/pa-core`, pinned to a tag (`v0.2.0`), never `main`.
Any change to this document's rules bumps `schema_version` and needs a migration note in CHANGELOG.md.
