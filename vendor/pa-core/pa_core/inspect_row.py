"""`pa-d4m inspect <row>`: every column across assocs, provenance, status, and linked rows."""
import json

from .dataset import typed_load


def inspect(directory, schema, row):
    ds = typed_load(directory, schema)
    found = {a: rows[row] for a, rows in ds.assocs.items() if row in rows}
    if not found:
        return None
    typ, ident = row.split("|", 1)[0].split(":", 1)
    linked = set()
    for a, rows in ds.assocs.items():
        for r, cols in rows.items():
            if r == row:
                continue
            for c, v in cols.items():
                if c == "claim|" + row or c.startswith("claim|") and c.split("|", 1)[1] == row:
                    linked.add(r)
                elif c not in ("id",) and not c.startswith("prov|"):
                    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else None
                    if s and (row in s or '"%s"' % ident in s):
                        linked.add(r)
    for c in found.get(next(iter(found)), {}):
        if c.startswith("claim|"):
            linked.add(c.split("|", 1)[1])
    prov = found.get("A_prov", {})
    return {"row": row, "assocs": {a: dict(sorted(v.items())) for a, v in sorted(found.items()) if a != "A_prov"},
            "provenance": dict(sorted(prov.items())), "status": prov.get("prov|status"),
            "linked": sorted(linked)}
