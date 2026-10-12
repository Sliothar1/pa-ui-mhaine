"""Validation: keys, types, duplicates, reserved namespaces, visibility, provenance, status vocabulary."""
from .dataset import typed_load, raw_load
from .schema import (parse_row_key, parse_col_key, SchemaError, PROV_REQUIRED, ISO_Z, SHA256)
from .tsvio import TSVError
from . import SCHEMA_VERSION


def validate(directory, schema):
    """Return a list of error strings (empty = valid)."""
    errs = []
    try:
        raw = raw_load(directory)
    except TSVError as e:
        return [str(e)]
    if not raw:
        return ["%s: no A_*.tsv files" % directory]
    if "A_prov" not in raw:
        errs.append("A_prov.tsv is required")
    for a in raw:
        if a not in schema.assocs:
            errs.append("%s: assoc not declared in schema" % a)
    for a, triples in raw.items():
        for r, c, _ in triples:
            try:
                parse_row_key(r); f, _q = parse_col_key(c)
            except SchemaError as e:
                errs.append("%s: %s" % (a, e)); continue
            if a == "A_prov" and f != "prov":
                errs.append("A_prov: %s %s: only prov| columns allowed" % (r, c))
            if a != "A_prov" and f == "prov":
                errs.append("%s: %s %s: prov| columns live in A_prov only" % (a, r, c))
    ds = typed_load(directory, schema, errs)
    prov = ds.assocs.get("A_prov", {})
    data_rows, vis = {}, {}
    for a, rows in ds.assocs.items():
        if a == "A_prov":
            continue
        req = schema.assocs.get(a, {}).get("required", {})
        for r, cols in rows.items():
            typ = r.split(":", 1)[0]
            data_rows.setdefault(r, []).append(a)
            vis.setdefault(r, []).extend(c for c in cols if c.startswith("visibility|"))
            if "meta|schema_version" in cols and cols["meta|schema_version"] != SCHEMA_VERSION:
                errs.append("%s: %s: meta|schema_version %r, this pa-core reads %d" % (a, r, cols["meta|schema_version"], SCHEMA_VERSION))
            for k in req.get(typ, []):
                if k not in cols:
                    errs.append("%s: %s: missing required column %s" % (a, r, k))
    for r, assocs in sorted(data_rows.items()):
        # a row may appear in several assocs (D4M: A_mon, A_prop, A_sky); visibility is set once per row
        if len(vis[r]) != 1:
            errs.append("%s: %s: needs exactly one of visibility|public / visibility|restricted across its assocs (has %s)" % (",".join(assocs), r, vis[r] or "none"))
        typ = r.split(":", 1)[0]
        p = prov.get(r)
        if p is None:
            errs.append("A_prov: missing provenance for %s" % r); continue
        need = [c for c in PROV_REQUIRED if not (typ in schema.prov_exempt_types and c == "prov|status")]
        for c in need:
            if p.get(c) in (None, ""):
                errs.append("A_prov: %s: %s missing or empty" % (r, c))
        if p.get("prov|status") not in (None, "") and p["prov|status"] not in schema.status_vocab:
            errs.append("A_prov: %s: status %r not in vocabulary" % (r, p["prov|status"]))
        if p.get("prov|fetched_at") and not ISO_Z.match(p["prov|fetched_at"]):
            errs.append("A_prov: %s: prov|fetched_at must be UTC YYYY-MM-DDTHH:MM:SSZ" % r)
        if p.get("prov|sha256") and not SHA256.match(p["prov|sha256"]):
            errs.append("A_prov: %s: prov|sha256 must be 64 lowercase hex" % r)
    for r in prov:
        if r not in data_rows and not r.startswith("batch:"):
            errs.append("A_prov: %s has provenance but no data row (use batch:<id> for batch provenance)" % r)
    return errs
