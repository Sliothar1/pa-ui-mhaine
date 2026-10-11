# Parity definition for the pa-core migration (written before any comparison was run)

Date: 11 Oct 2026. Scope: branch `pa-core` (pa-core v0.1.0 vendored at `vendor/pa-core`) versus `main`
at the commit the branch was cut from (`7a2ef65`). This is a pure data-representation refactor:
no claim, place, era, reference, status or wording changes.

## What "parity" means
Run `tools/build.py` on a clean checkout of each side, in both publishing modes
(draft: `PA_LIVE` unset; live: `PA_LIVE=1`). Then, for every file that the build writes or
rewrites, and for every file tracked on main:

1. **JSON outputs** (`generated/story-cards.json`, `generated/era-polygons.geojson`, and any other
   `*.json` / `*.geojson` tracked on main): equal after canonicalisation, i.e.
   `json.dumps(json.load(f), ensure_ascii=False, sort_keys=True, separators=(",", ":"))` is the
   same string on both sides. Key order and whitespace are not part of parity; values, types,
   list order and nulls are.
2. **HTML** (`*.html`, `scenes/*.html`): byte-identical.
3. **Everything else tracked on main** (`generated/verification-table.md`, data, JS, CSS, sitemap,
   robots): byte-identical.
4. Files that exist only on the branch (`data/d4m/*`, `vendor/pa-core/**`, `docs/PARITY.md`,
   `tools/parity_check.py`, CI changes) are listed but are not part of parity.

`tests/results.json` is excluded: it is a test-run log, rewritten by every test run.

Parity holds only if 1–3 hold in both modes with zero differences. Any difference blocks the merge.
In practice the comparison is stricter than required: JSON outputs are also compared byte for byte
and the result says which level they matched at.

## Correction to the scope (11 Oct 2026, after the first run, before any output was judged)
The first run of the check applied rule 3 literally to *every* tracked file, so it flagged the
five files this migration changes on purpose: `tools/build.py`, `.github/workflows/ci.yml`,
`.gitignore`, `data/README.md`, and the worktree `.git` pointer. Those are build code and docs,
not generated outputs, so rule 3 is narrowed to the **published site and its data**:
`*.html`, `scenes/*.html`, `generated/**`, `data/*.json`, `data/*.geojson`, `*.js`, `*.css`,
`vendor/leaflet/**`, `sitemap.xml`, `robots.txt`. Build code, CI, tests, docs and the new
`data/d4m`/`vendor/pa-core` are reported as "changed on purpose", not compared. No output file
differed in that first run; the rules for outputs (1 and 2) are unchanged.

## How to run
`python3 tools/parity_check.py main` (creates two temporary worktrees, builds both, compares,
exits 1 on any difference).

## Result
Recorded below by the check, after it was run.

### Run 11 Oct 2026, 17:30 IST: `python3 tools/parity_check.py main` on branch pa-core (6f919ee) vs main (7a2ef65)
- Draft mode: 35 published files compared, 35 byte-identical (including generated/story-cards.json and
  generated/era-polygons.geojson, so canonical-JSON equality holds trivially), 0 different.
- Live mode (PA_LIVE=1): same, 35/35 byte-identical, 0 different.
- **PARITY HOLDS.** Negative control: changing one claim title made the check fail on
  verification-table.md, sources.html and timeslider.html, as it should.
- CI (site-checks) green on the branch and after merge: pa-core 31 unit tests, rebuild-no-diff,
  pa-d4m validate, diff guard, html-validate, 19/19 site tests.
