"""pa-d4m: ingest | validate | export | diff | inspect | parity.  Exit 0 = ok, 1 = check failed, 2 = usage."""
import argparse, json, sys

from . import __version__
from .schema import Schema


def _load_json(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pa-d4m", description="PA core data contract CLI (pa-core %s)" % __version__)
    ap.add_argument("--version", action="version", version="pa-core " + __version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest", help="run an adapter, write A_*.tsv")
    i.add_argument("adapter", choices=["json-claims", "tabular"])
    i.add_argument("--config", required=True); i.add_argument("--schema", required=True)
    i.add_argument("--out", default="data/d4m"); i.add_argument("--root", default=".")
    i.add_argument("--dry-run", action="store_true", help="report counts, write nothing")
    v = sub.add_parser("validate", help="validate a dataset directory")
    v.add_argument("data", nargs="?", default="data/d4m"); v.add_argument("--schema", required=True)
    v.add_argument("--roundtrip", metavar="ADAPTER_CONFIG", help="also check the TSVs reproduce the JSON sources")
    v.add_argument("--root", default=".")
    v.add_argument("--edges", action="store_true", help="also check the edge-row convention (docs/EDGES.md)")
    e = sub.add_parser("export", help="default-deny export to static JSON")
    e.add_argument("data", nargs="?", default="data/d4m"); e.add_argument("--schema", required=True)
    e.add_argument("--allow", required=True); e.add_argument("--to", required=True)
    d = sub.add_parser("diff", help="row/col deltas; fails on a per-type drop above --max-drop %%")
    d.add_argument("base", help="directory or git:<ref>"); d.add_argument("head", help="directory or git:<ref>")
    d.add_argument("--path", default="data/d4m", help="dataset path inside the repo for git:<ref>")
    d.add_argument("--max-drop", type=float, default=10.0); d.add_argument("--strict", action="store_true")
    n = sub.add_parser("inspect", help="show one row: columns, provenance, status, linked rows")
    n.add_argument("row"); n.add_argument("data", nargs="?", default="data/d4m"); n.add_argument("--schema", required=True)
    p = sub.add_parser("parity", help="byte equality + schema diff + semantic hash + negative control")
    p.add_argument("base"); p.add_argument("head"); p.add_argument("--schema")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.add_argument("--no-negative-control", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "ingest":
        from .adapters import json_claims, tabular
        schema = Schema.load(a.schema)
        mod = {"json-claims": json_claims, "tabular": tabular}[a.adapter]
        ds, written = mod.ingest(_load_json(a.config), schema, a.out, a.root, a.dry_run)
        for t, c in sorted(ds.counts_by_type().items()):
            print("%-10s %d rows" % (t, c))
        print("dry run: nothing written" if a.dry_run else "wrote %s to %s" % (", ".join(sorted(written)), a.out))
        return 0
    if a.cmd == "validate":
        from .validate import validate
        schema = Schema.load(a.schema)
        errs = validate(a.data, schema)
        if a.roundtrip and not errs:
            from .adapters import json_claims, tabular
            cfg = _load_json(a.roundtrip)
            mod = tabular if cfg.get("adapter") == "tabular" else json_claims
            errs += mod.roundtrip_errors(cfg, schema, a.data, a.root)
        if a.edges and not errs:
            from .edges import edge_errors
            errs += edge_errors(a.data, schema)
        for x in errs:
            print("ERROR " + x)
        print("valid" if not errs else "%d error(s)" % len(errs))
        return 1 if errs else 0
    if a.cmd == "export":
        from .export import export, ExportError
        try:
            files = export(a.data, Schema.load(a.schema), _load_json(a.allow), a.to)
        except ExportError as ex:
            print(ex); return 1
        print("exported %s to %s" % (", ".join(files), a.to)); return 0
    if a.cmd == "diff":
        from .diff import load_side, diff
        lines, fails = diff(load_side(a.base, a.path), load_side(a.head, a.path), a.max_drop, a.strict)
        print("\n".join(lines))
        for f in fails:
            print("FAIL " + f)
        print("diff guard: " + ("FAIL" if fails else "ok"))
        return 1 if fails else 0
    if a.cmd == "inspect":
        from .inspect_row import inspect
        r = inspect(a.data, Schema.load(a.schema), a.row)
        if r is None:
            print("no such row: " + a.row); return 1
        print(json.dumps(r, ensure_ascii=False, indent=1)); return 0
    if a.cmd == "parity":
        from .parity import compare, negative_control
        sch = Schema.load(a.schema) if a.schema else None
        rep = compare(a.base, a.head, sch)
        if not a.no_negative_control:
            ok, what = negative_control(a.base, a.head, sch)
            rep["negative_control"] = {"ok": ok, "detail": what}
        good = rep["pass"] and rep.get("negative_control", {"ok": True})["ok"]
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1, sort_keys=True))
        else:
            b = rep["bytes"]
            print("bytes: %s (%d files; differ %d, only-base %d, only-head %d)" % (
                "identical" if b["equal"] else "DIFFER", b["files"], len(b["differ"]), len(b["only_base"]), len(b["only_head"])))
            for f in (b["differ"] + b["only_base"] + b["only_head"])[:20]:
                print("  " + f)
            if "schema_diff" in rep:
                print("schema diff: " + ("none" if not rep["schema_diff"] else "%d change(s)" % len(rep["schema_diff"])))
                for l in rep["schema_diff"][:20]:
                    print("  " + l)
                h = rep["semantic_hash"]
                print("semantic hash: base %s head %s %s" % (h["base"][:16], h["head"][:16], "equal" if h["base"] == h["head"] else "DIFFER"))
            if "negative_control" in rep:
                print("negative control: " + rep["negative_control"]["detail"])
            print("parity gate: " + ("PASS" if good else "FAIL"))
        return 0 if good else 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
