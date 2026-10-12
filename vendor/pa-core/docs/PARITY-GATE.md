# Parity gate: `pa-d4m parity BASE HEAD [--schema schema.json] [--json]`

Used whenever a site moves to a new pa-core or refactors a pipeline: BASE is the reference
(published outputs or dataset at the old pin), HEAD is the rebuild. Exit 0 only if every check
passes **and** the negative control fails as it should.

| check | what it compares |
|---|---|
| byte equality | every file under both trees (recursive): differ / only-base / only-head |
| schema diff | per assoc: row count, column set and type (from `--schema`, else inferred), visibility flag per row |
| semantic hash | sha256 of canonical JSON of the sorted, unescaped `(assoc, row parts, col parts, value)` tuples; ignores line order and escaping choices |
| negative control | copies HEAD, mutates one value (first TSV line, else appends a byte), reruns the gate and requires FAIL |

Schema diff and semantic hash apply when a side contains `A_*.tsv`; for pure output dirs
(site JSON/HTML) byte equality + negative control is the gate. Canonical semantic equality is the
fallback evidence only when serialisation intentionally changes (bytes differ, hash equal); that
case FAILS the gate and needs a written justification in the parity record.

Parity record (commit in the site, e.g. `docs/PARITY.md`): BASE/HEAD refs and code SHAs, pa-core
tag before/after, the full `--json` report, input hashes of the sources, Python version, and for
science pipelines the intermediate artefact hashes (panel, feature matrix) the pipeline already
produces. Reproducibility is not validity: parity proves the refactor changed nothing, not that
the analysis is right.

Example:
```
git worktree add /tmp/base <old-ref>
python3 vendor/pa-core/pa_d4m.py parity /tmp/base/site/data site/data --json > parity.json
```
