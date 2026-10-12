"""Parity gate (docs/PARITY-GATE.md): byte equality, schema diff, canonical semantic hash,
and a negative control that must FAIL. Compares two dataset dirs or two output dirs."""
import hashlib, json, os, shutil, tempfile

from .dataset import raw_load
from .schema import from_text, SchemaError
from .tsvio import split_key


def _files(d):
    out = {}
    for root, _dirs, names in os.walk(d):
        for n in names:
            p = os.path.join(root, n)
            out[os.path.relpath(p, d).replace(os.sep, "/")] = p
    return out


def byte_report(a, b):
    fa, fb = _files(a), _files(b)
    only_a, only_b = sorted(set(fa) - set(fb)), sorted(set(fb) - set(fa))
    differ = []
    for k in sorted(set(fa) & set(fb)):
        with open(fa[k], "rb") as x, open(fb[k], "rb") as y:
            if x.read() != y.read():
                differ.append(k)
    return {"files": len(set(fa) | set(fb)), "only_base": only_a, "only_head": only_b,
            "differ": differ, "equal": not (only_a or only_b or differ)}


def _infer(v):
    if v is None:
        return "null"
    for t in ("int", "float", "json"):
        try:
            from_text(t, v); return t
        except SchemaError:
            pass
    return "flag" if v == "1" else "str"


def shape(d, schema=None):
    """{assoc: {"rows": n, "cols": {col_key: type}, "visibility": {row: flag}}}"""
    out = {}
    for a, trip in raw_load(d).items():
        cols, rows, vis = {}, set(), {}
        for r, c, v in trip:
            rows.add(r)
            t = schema.col_type(a, c) if schema else None
            cols[c] = t or _infer(v) if c not in cols or cols[c] == "null" else cols[c]
            if c.startswith("visibility|"):
                vis[r] = c
        out[a] = {"rows": len(rows), "cols": cols, "visibility": vis}
    return out


def schema_diff(a, b, schema=None):
    sa, sb = shape(a, schema), shape(b, schema)
    lines = []
    for x in sorted(set(sa) | set(sb)):
        if x not in sa or x not in sb:
            lines.append("assoc %s only in %s" % (x, "head" if x in sb else "base")); continue
        A, B = sa[x], sb[x]
        if A["rows"] != B["rows"]:
            lines.append("%s rows %d -> %d" % (x, A["rows"], B["rows"]))
        for c in sorted(set(A["cols"]) | set(B["cols"])):
            ta, tb = A["cols"].get(c), B["cols"].get(c)
            if ta != tb:
                lines.append("%s col %s type %s -> %s" % (x, c, ta, tb))
        for r in sorted(set(A["visibility"]) | set(B["visibility"])):
            if A["visibility"].get(r) != B["visibility"].get(r):
                lines.append("%s vis %s %s -> %s" % (x, r, A["visibility"].get(r), B["visibility"].get(r)))
    return lines


def semantic_hash(d):
    """sha256 over canonical JSON of sorted unescaped (assoc, row parts, col parts, value) tuples:
    insensitive to file order/whitespace/escaping choices, sensitive to any value or key change."""
    items = []
    for a, trip in raw_load(d).items():
        for r, c, v in trip:
            items.append([a, split_key(r), split_key(c), v])
    items.sort(key=lambda t: json.dumps(t, ensure_ascii=False, sort_keys=True))
    blob = json.dumps(items, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _is_dataset(d):
    return bool(raw_load(d))


def compare(a, b, schema=None):
    rep = {"bytes": byte_report(a, b)}
    if _is_dataset(a) or _is_dataset(b):
        rep["schema_diff"] = schema_diff(a, b, schema)
        rep["semantic_hash"] = {"base": semantic_hash(a), "head": semantic_hash(b)}
    rep["pass"] = rep["bytes"]["equal"] and not rep.get("schema_diff") and \
        ("semantic_hash" not in rep or rep["semantic_hash"]["base"] == rep["semantic_hash"]["head"])
    return rep


def negative_control(a, b, schema=None):
    """Copy head, flip one byte-level value, and check that compare() FAILS. Returns (ok, what)."""
    tmp = tempfile.mkdtemp(prefix="pa-parity-neg-")
    try:
        dst = os.path.join(tmp, "head")
        shutil.copytree(b, dst)
        files = sorted(_files(dst).items())
        if not files:
            return False, "head is empty: nothing to mutate"
        rel, p = next(((k, v) for k, v in files if k.endswith(".tsv") and os.path.getsize(v)), files[0])
        with open(p, "rb") as fh:
            data = fh.read()
        if rel.endswith(".tsv") and data:
            line = data.split(b"\n", 1)[0]
            mutated = line + b"\xc2\xb7neg"  # append to the first value
            data = mutated + data[len(line):]
        else:
            data = data + b"\n"
        with open(p, "wb") as fh:
            fh.write(data)
        rep = compare(a, dst, schema)
        return (not rep["pass"]), "mutated %s; gate %s" % (rel, "FAILED as required" if not rep["pass"] else "PASSED (control broken)")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
