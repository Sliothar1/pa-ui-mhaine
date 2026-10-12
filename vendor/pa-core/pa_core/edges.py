"""Edge-row convention checks (docs/EDGES.md). Opt-in: `pa-d4m validate --edges`.

edge:<id>  from=<row key> to=<row key> role=<slug> start=<date?> end=<date?> claim|<claim id>=1
role:<slug> entity rows name the roles; match:<id> rows are ordinary entities.
Every edge carries at least one claim|<id> pointing at a claim:<id> row (per-assertion provenance).
"""
import re

from .dataset import typed_load

DATE_RE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
EDGE_COLS = ("from", "to", "role")


def edge_errors(directory, schema):
    errs = []
    ds = typed_load(directory, schema, errs)
    if errs:
        return errs
    rows = {r: c for r, c in ds.rows().items()}
    merged = {}
    for a, rs in ds.assocs.items():
        if a == "A_prov":
            continue
        for r, cols in rs.items():
            merged.setdefault(r, {}).update(cols)
    prov = ds.assocs.get("A_prov", {})
    for r, cols in sorted(merged.items()):
        if not r.startswith("edge:"):
            continue
        for k in EDGE_COLS:
            if cols.get(k) in (None, ""):
                errs.append("%s: missing %s" % (r, k))
        for k in ("from", "to"):
            v = cols.get(k)
            if v and v not in merged:
                errs.append("%s: %s -> %s: no such row" % (r, k, v))
            elif v and v.startswith("edge:"):
                errs.append("%s: %s may not point at another edge" % (r, k))
        role = cols.get("role")
        if role and "role:" + role not in merged:
            errs.append("%s: role %r has no role:%s row" % (r, role, role))
        s, e = cols.get("start"), cols.get("end")
        for k, v in (("start", s), ("end", e)):
            if v is not None and not DATE_RE.match(v):
                errs.append("%s: %s %r must be YYYY, YYYY-MM or YYYY-MM-DD" % (r, k, v))
        if s and e and DATE_RE.match(s) and DATE_RE.match(e) and e[:len(s)] < s[:len(e)]:
            errs.append("%s: end %s before start %s" % (r, e, s))
        claims = [c.split("|", 1)[1] for c in cols if c.startswith("claim|")]
        if not claims:
            errs.append("%s: needs at least one claim|<id> (per-assertion provenance)" % r)
        for cid in claims:
            ck = "claim:" + cid
            if ck not in merged:
                errs.append("%s: claim|%s has no %s row" % (r, cid, ck))
            elif not (prov.get(ck) or {}).get("prov|source"):
                errs.append("%s: %s has no prov|source" % (r, ck))
            elif "visibility|public" in cols and "visibility|public" not in merged[ck]:
                errs.append("%s: public edge cites non-public %s" % (r, ck))
        if "visibility|public" in cols:
            for k in ("from", "to"):
                v = cols.get(k)
                if v in merged and "visibility|public" not in merged[v]:
                    errs.append("%s: public edge points at non-public %s" % (r, v))
    return errs
