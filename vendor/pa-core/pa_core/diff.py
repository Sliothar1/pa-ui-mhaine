"""Row/col deltas between two datasets, with a relative count guard per row type."""
import subprocess

from .tsvio import parse_lines, decode_val


def load_side(spec, path="data/d4m"):
    """spec: a directory, or git:<ref> (reads <path>/A_*.tsv at that ref). Returns {assoc: {(r,c): v}}."""
    out = {}
    if spec.startswith("git:"):
        ref = spec[4:]
        ls = subprocess.run(["git", "ls-tree", "--name-only", ref, path.rstrip("/") + "/"],
                            capture_output=True, text=True)
        if ls.returncode != 0:
            raise SystemExit("git ls-tree failed for %s: %s" % (ref, ls.stderr.strip()))
        names = [n for n in ls.stdout.split() if n.rsplit("/", 1)[-1].startswith("A_") and n.endswith(".tsv")]
        for n in names:
            text = subprocess.run(["git", "show", "%s:%s" % (ref, n)], capture_output=True, check=True).stdout.decode("utf-8")
            out[n.rsplit("/", 1)[-1][:-4]] = {(r, c): decode_val(v) for _, r, c, v in parse_lines(text, n)}
        return out
    from .dataset import raw_load
    for a, triples in raw_load(spec).items():
        out[a] = {(r, c): v for r, c, v in triples}
    return out


def _types(side):
    t = {}
    for a, trip in side.items():
        if a == "A_prov":
            continue
        for (r, _c) in trip:
            t.setdefault(r.split(":", 1)[0], set()).add(r)
    return t


def diff(base, head, max_drop_pct=10.0, strict=False):
    """Return (report_lines, failures)."""
    lines, fails = [], []
    tb, th = _types(base), _types(head)
    for typ in sorted(set(tb) | set(th)):
        b, h = tb.get(typ, set()), th.get(typ, set())
        added, removed = sorted(h - b), sorted(b - h)
        lines.append("type %-12s rows %d -> %d (+%d -%d)" % (typ, len(b), len(h), len(added), len(removed)))
        for r in removed[:20]:
            lines.append("  - %s" % r)
        for r in added[:20]:
            lines.append("  + %s" % r)
        if b and (len(b) - len(h)) * 100.0 / len(b) > max_drop_pct:
            fails.append("type %s dropped %d -> %d (%.1f%% > %.1f%%)" % (typ, len(b), len(h), (len(b) - len(h)) * 100.0 / len(b), max_drop_pct))
    changed = 0
    for a in sorted(set(base) | set(head)):
        B, H = base.get(a, {}), head.get(a, {})
        ch = [k for k in set(B) & set(H) if B[k] != H[k]]
        add, rem = set(H) - set(B), set(B) - set(H)
        changed += len(ch) + len(add) + len(rem)
        lines.append("assoc %-10s triples %d -> %d (+%d -%d ~%d)" % (a, len(B), len(H), len(add), len(rem), len(ch)))
        for k in sorted(ch)[:20]:
            lines.append("  ~ %s %s" % k)
        for k in sorted(rem)[:20]:
            lines.append("  - %s %s" % k)
        for k in sorted(add)[:20]:
            lines.append("  + %s %s" % k)
    if strict and changed:
        fails.append("strict: %d triple(s) differ" % changed)
    return lines, fails
