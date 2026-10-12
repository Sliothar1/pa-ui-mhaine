# Edge rows, roles and per-assertion provenance (v0.3.0, schema_version 1)

A convention on top of the contract (no format change), written for HurlingWiki-style data:
time-qualified, many-to-many relations (player ↔ club spells, player ↔ match appearances) where
each fact needs its own source. Check it with `pa-d4m validate <dir> --schema … --edges`.

## Entity rows
Ordinary rows: `player:<id>`, `club:<id>`, `match:<id>`, … A match is an entity, not an edge:
`match:M-1959-0001` with `date`, `competition`, `home`, `away` (home/away hold row keys).
Roles are entity rows too: `role:<slug>` with a `label` (e.g. `role:member`,
`role:right-corner-forward`), so the set of roles is data, versioned and exportable.

## Edge rows
One relation instance = one row `edge:<id>` (stable id, never reused):

| column | type | meaning |
|---|---|---|
| `from` | str | row key of the subject (e.g. `player:P-0001`) |
| `to` | str | row key of the object (`club:…`, `match:…`) |
| `role` | str | slug; a `role:<slug>` row must exist |
| `start` | str? | `YYYY`, `YYYY-MM` or `YYYY-MM-DD`; `\N` = unknown |
| `end` | str? | same; `\N` = open/unknown. A one-day appearance has start = end |
| `claim|<id>` | flag | one per supporting assertion (≥ 1 required) |

Many-to-many is just several edge rows. Two spells at the same club are two edges. Edges never
point at edges. Precision is kept as written (a year stays a year; no invented days); `end`
before `start` (compared at the shared precision) is an error.

## Per-assertion provenance (`claim|`)
`A_prov` gives one provenance record per row, which is too coarse when a club spell rests on a
club history and a match appearance on two newspaper items. So each fact is a `claim:<id>` row
(`text`, `cites`) with its own `A_prov` (`prov|source` = the citation, `prov|status` usually
`pinned`). The edge (or an entity row, for an entity-level fact) carries `claim|<id> = 1` for each
claim that supports it. The `claim|` namespace is core-reserved and typed `flag`.

Rules checked by `--edges`: from/to exist and are not edges; the role row exists; dates are well
formed and ordered; each edge has ≥ 1 claim; each cited claim exists and has `prov|source`; a
public edge cites only public claims and points only at public rows.

Privacy (reviews 2026-10-11): living people and possible minors are opt-in only. Store no inferred
birth years, no contact details; keep cuttings as citation + provenance with a correction path.
Such fields are restricted or HARD_DENY and never exported.

## Golden fixtures
`tests/fixtures/edges/` (synthetic): a sample player, two clubs, a club spell (`edge:E-0001`,
1950-1962, one claim), a match (`match:M-1959-0001`) and an appearance (`edge:E-0002`, two
claims). `golden/` holds the exact export bytes; `make_fixture.py` regenerates the TSVs.
Tests: `tests/test_edges_parity.py` (valid fixture, golden bytes, and one negative per rule).
HurlingWiki is TypeScript: this page plus the golden files are its contract; a TS reader should
reproduce `golden/` from the TSVs byte for byte.
