# PA Core stable interchange contract (schema_version 1, pa-core v0.3.0)

This page is the short, normative contract that consuming sites (PA Uí Mhaine, PA Réalt, later
HurlingWiki) may rely on. `docs/SCHEMA.md` has the long-form detail and examples; where they
disagree, this page wins and the disagreement is a bug. Anything not listed here is internal and
may change in a minor release.

## 1. Stability promise
- Everything in sections 2-8 is frozen for `schema_version: 1`. Changing any of it bumps
  `schema_version`, needs an RFC (issue labelled `schema-rfc`), a migration note in CHANGELOG.md and
  Garry's sign-off.
- Additive, opt-in checks (like `validate --edges`) and new CLI commands are minor releases.
- Sites pin a tag (`vendor/pa-core` = `git archive <tag>`), never `main`. A new pa-core tag never
  moves a site: each site upgrades in its own PR with a parity record (docs/PARITY-GATE.md).

## 2. Files and types
- A dataset is a directory of `A_<concern>.tsv` files; `A_prov.tsv` is required.
- UTF-8, LF, no BOM, no header; one `row \t col \t val` triple per line.
- Value types, declared per column in the site schema: `str`, `int`, `float` (Python `repr`),
  `bool` (`true|false`), `json` (compact, sorted keys), `json_ordered` (compact, key order kept),
  `flag` (exactly `1`). `?` suffix = nullable. Values must be canonical; undeclared columns fail.

## 3. Escaping
Backslash is the only escape, applied to row, col and val: `\\` `\t` `\n` `\r` `\|`. Any other
`\x` or a trailing lone backslash is an error. Null is `\N`; a literal backslash-N is `\\N`; the
empty string is an empty field; absent ≠ null. Raw CR anywhere is an error.

## 4. Keys
- Row: `type:id[|qualifier]`, type `[a-z][a-z0-9_]*`, id `[A-Za-z0-9][A-Za-z0-9._:+-]*`.
- Col: `field[|qualifier]`, field `[A-Za-z_][A-Za-z0-9_]*`. Unescaped `|` is structural.
- Reserved namespaces owned by the core: `prov|`, `meta|`, `sys|`, `claim|`, `visibility|`.
- Edges, roles and per-assertion provenance follow docs/EDGES.md.

## 5. Provenance
Every data row has one `A_prov` row with `prov|source`, `prov|status` (core vocabulary + site
extras), `prov|fetched_at` (UTC `YYYY-MM-DDTHH:MM:SSZ`), `prov|sha256` (64 lowercase hex),
`prov|code_sha`. Optional: `prov|pinned`, `prov|confidence`. `batch:<id>` rows hold batch
provenance. `fetched_at` is kept when the sha256 is unchanged (re-ingest is byte-identical).
Row-level provenance says where the *row* came from; per-assertion provenance (which source
supports which fact) uses `claim|<id>` (docs/EDGES.md).

## 6. Visibility
Each row has exactly one of `visibility|public` / `visibility|restricted` across all its assocs.
Restricted personal data (consent, age band, raw submissions, review material) belongs in a
separate restricted store; if it must sit in a dataset, it is restricted and HARD_DENY applies.
A public edge may not point at, or cite, a non-public row (`--edges`).

## 7. Ordering and determinism
Serializer output is sorted by (row key parts, col key parts) in Unicode code-point order with a
trailing newline. Same data in, same bytes out. Export JSON is UTF-8, `indent=1`, sorted keys
(values of `json_ordered` columns keep their order). `index.json` records the pa-core version.

## 8. schema_version
The site schema file must say `"schema_version": 1`. A row may carry `meta|schema_version`;
validation fails if it differs from what the installed pa-core reads.

## 9. Export permissions (default deny)
A row is exported only if it is `visibility|public`, its type is in the allowlist and it is not
a prov-exempt config type. Only allow-listed columns go out (`"*"` = all declared non-core
columns). Never emitted, even if allow-listed: `visibility|*`, `sys|*`, and HARD_DENY fields
(`consent`, `age_band`, `age`, `dob`, `birth_date`, `email`, `phone`, `address`, `minor`,
`guardian`, `private_text`, `ocr_private`). Export refuses an invalid dataset. Public builds
consume only allow-listed exports.

## 10. Release gates (a pa-core tag is cut only when all hold)
1. CI green on the tagged commit (unit tests on Python 3.9 and 3.12, CLI smoke).
2. Golden fixtures unchanged, or changed in the same PR with a CHANGELOG entry saying why
   (`tests/fixtures/edges/golden`, round-trip and mutation suites).
3. Privacy negatives pass (HARD_DENY, restricted rows, invalid dataset refused).
4. No contract change without a `schema_version` bump + migration note + RFC + Garry sign-off.
5. CHANGELOG entry, `__version__` and `pyproject.toml` version agree with the tag.
6. docs/COMPATIBILITY.md updated (which site pins what); sites are NOT bumped by the release.
7. For each site that later upgrades: `pa-d4m parity` passes on its published outputs, negative
   control fails as required, and the record is committed in that site (docs/PARITY-GATE.md).
8. Tags are annotated (signed once tag protection/signing is set up; see the governance draft)
   and never moved or deleted.
