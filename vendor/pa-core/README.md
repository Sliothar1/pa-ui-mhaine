# pa-core

The shared data contract for the PA sites: D4M-style associative arrays stored as sorted TSV
triples, with required provenance, a status vocabulary, a default-deny export and a relative
count guard. Python standard library only.

- Spec: [docs/SCHEMA.md](docs/SCHEMA.md)
- CLI: `pa-d4m ingest | validate | export | diff | inspect` (`pip install .`, or run
  `python3 pa_d4m.py` from a vendored copy)
- Adapters: `json-claims` (v0.1.0, hand-edited JSON ledgers, PA Uí Mhaine) and `tabular`
  (v0.2.0, CSV/TSV tables, PA Réalt)
- Tests: `python3 -m unittest discover -s tests -v`

Consumers vendor a tagged release at `vendor/pa-core` (first consumer: Sliothar1/pa-ui-mhaine;
next: PA Réalt). The core was extracted only as far as the Uí Mhaine migration needed.
