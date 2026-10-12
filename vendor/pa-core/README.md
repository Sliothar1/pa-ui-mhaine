# PA Core

**A small, stdlib-only toolkit for trustworthy place-based data: D4M triples, provenance, validation, privacy-safe export.**

[![tests](https://github.com/Sliothar1/pa-core/actions/workflows/ci.yml/badge.svg)](https://github.com/Sliothar1/pa-core/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)

## What it is
PA Core is the shared data contract behind the PA family of heritage and science sites. Every
dataset is a set of D4M-style associative arrays, stored as plain, sorted TSV triples
(`row \t col \t val`), with:

- **Provenance on every record** – `A_prov` is required: source, status, fetched_at, sha256, code_sha.
- **Honest status** – a core vocabulary (*pinned, partly pinned, annal identified, year only,
  needs source, tradition, interpretation*) that each site can extend.
- **Strict validation** – typed columns (ids like `007` stay strings), escaping rules,
  duplicates, reserved namespaces (`prov|`, `meta|`, `sys|`, `claim|`).
- **Deterministic files** – same data in, same bytes out, so diffs and reviews mean something.
- **Count guards** – `pa-d4m diff` fails a change that drops too many rows of any type.
- **No dependencies** – Python standard library only; no D4M runtime in the browser.

## Why
Small research sites mix hand-edited claims, open data and derived numbers. PA Core keeps the
editable source per site, but makes the interchange format shared, checkable and reversible:
migrations are proven by byte-for-byte parity, not by eye.

## Quick start
```bash
git clone https://github.com/Sliothar1/pa-core && cd pa-core
python3 -m unittest discover -s tests          # 42 tests, stdlib only
pip install .                                  # installs the pa-d4m command (or run python3 pa_d4m.py)

pa-d4m ingest tabular --config data/d4m/tabular.json --schema data/d4m/schema.json --out data/d4m
pa-d4m validate data/d4m --schema data/d4m/schema.json --roundtrip data/d4m/tabular.json
pa-d4m export data/d4m --schema data/d4m/schema.json --allow data/d4m/export.allow.json --to site/data
pa-d4m diff git:origin/main data/d4m --max-drop 10
pa-d4m inspect mon:ME001-005---- data/d4m --schema data/d4m/schema.json
```
Adapters: `json-claims` (hand-edited JSON ledgers) and `tabular` (CSV/TSV tables).
The full specification is in [docs/SCHEMA.md](docs/SCHEMA.md); changes are in [CHANGELOG.md](CHANGELOG.md). Stable contract and release gates: [docs/CONTRACT.md](docs/CONTRACT.md); edges: [docs/EDGES.md](docs/EDGES.md); parity gate: [docs/PARITY-GATE.md](docs/PARITY-GATE.md).

## Sites using it
- **PA Uí Mhaine** – the medieval kingdom of Uí Mhaine: a claims ledger with pinned annal
  references (PA Core v0.2.0; was v0.1.0).
- **PA Réalt** – Ireland's Neolithic and Bronze Age monuments and the sky: 6,878 monuments, with
  preregistered tests reproduced byte for byte after migration (PA Core v0.2.0).

Sites vendor a tagged release at `vendor/pa-core`, never `main`. The site → pinned version
matrix and the checksums of the vendored files are in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Privacy by default
Export is **default-deny**: only rows marked `visibility|public`, of allow-listed types, with
allow-listed columns, ever leave. Fields such as consent, age band, date of birth, email and
phone are hard-blocked even if a site allow-lists them, and the test suite includes negative
tests on a sensitive fixture.

## Licence
[Apache License, Version 2.0](LICENSE). See [NOTICE](NOTICE). Copyright © 2026 Dr Garry Lohan.

---

**Created, designed and built by Dr Garry Lohan** ·
[Google Scholar](https://scholar.google.com/citations?user=9aBECzQAAAAJ&hl=en) ·
[LinkedIn](https://www.linkedin.com/in/garry-lohan-14923814)
