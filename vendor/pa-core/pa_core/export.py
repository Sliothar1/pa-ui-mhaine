"""Default-deny export to static JSON.

Only rows that are (a) visibility|public, (b) of a row type named in the allowlist, and
(c) not a prov-exempt config type are emitted; only allow-listed columns are emitted; and
columns whose field is in HARD_DENY are never emitted, even if allow-listed.
Allowlist file (JSON): {"types": {"claim": ["id", "date"], "place": "*"}, "include_prov": true}
"""
import json, os

from . import __version__
from .dataset import typed_load
from .schema import PROV_REQUIRED
from .validate import validate

HARD_DENY = {"consent", "age_band", "age", "dob", "birth_date", "email", "phone", "address",
             "minor", "guardian", "private_text", "ocr_private"}


class ExportError(ValueError):
    pass


def _field(col):
    f = col.split("|", 1)
    return f[1] if f[0] in ("prov", "sys", "meta") and len(f) > 1 else f[0]


def plan_export(directory, schema, allow):
    errs = validate(directory, schema)
    if errs:
        raise ExportError("refusing to export an invalid dataset:\n  " + "\n  ".join(errs[:20]))
    ds = typed_load(directory, schema)
    prov = ds.assocs.get("A_prov", {})
    types = allow.get("types", {})
    out = {}
    for a, rows in ds.assocs.items():
        if a == "A_prov":
            continue
        for r, cols in rows.items():
            typ = r.split(":", 1)[0]
            if typ not in types or typ in schema.prov_exempt_types:
                continue
            if cols.get("visibility|public") != 1:
                continue
            spec = types[typ]
            rec = {}
            for c, v in cols.items():
                if c.startswith(("visibility|", "sys|")) or _field(c) in HARD_DENY:
                    continue
                if spec == "*" or c in spec:
                    rec[c] = v
            if allow.get("include_prov", True):
                for c in PROV_REQUIRED + ("prov|pinned", "prov|confidence"):
                    if c in prov.get(r, {}):
                        rec[c] = prov[r][c]
            out.setdefault(typ, {})[r] = dict(sorted(rec.items()))
    return {t: dict(sorted(v.items())) for t, v in sorted(out.items())}


def export(directory, schema, allow, to):
    plan = plan_export(directory, schema, allow)
    os.makedirs(to, exist_ok=True)
    files = {}
    for typ, rows in plan.items():
        files[typ + ".json"] = rows
    files["index.json"] = {"pa_core": __version__, "types": {t: len(r) for t, r in plan.items()}}
    for name, obj in files.items():
        with open(os.path.join(to, name), "w", encoding="utf-8", newline="") as fh:
            json.dump(obj, fh, ensure_ascii=False, sort_keys=True, indent=1)
            fh.write("\n")
    return sorted(files)
