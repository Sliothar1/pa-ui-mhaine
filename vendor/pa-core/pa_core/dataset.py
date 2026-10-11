"""A dataset is a directory of A_<concern>.tsv files; in memory {assoc: {row: {col: value}}}."""
import glob, os

from .schema import from_text, to_text, SchemaError
from .tsvio import read_triples, serialize, TSVError


class Dataset:
    def __init__(self, assocs=None):
        self.assocs = assocs or {}

    def rows(self):
        out = {}
        for a, rows in self.assocs.items():
            for r, cols in rows.items():
                out.setdefault(r, {}).setdefault(a, cols)
        return out

    def counts_by_type(self):
        """Distinct data rows per row type (A_prov excluded)."""
        c = {}
        for a, rows in self.assocs.items():
            if a == "A_prov":
                continue
            for r in rows:
                t = r.split(":", 1)[0]
                c.setdefault(t, set()).add(r)
        return {t: len(s) for t, s in c.items()}


def raw_load(directory):
    """{assoc: [(row, col, val_str_or_None)]} without typing. Missing directory -> empty."""
    out = {}
    if not directory or not os.path.isdir(directory):
        return out
    for p in sorted(glob.glob(os.path.join(directory, "A_*.tsv"))):
        out[os.path.basename(p)[:-4]] = read_triples(p)
    return out


def typed_load(directory, schema, errors=None):
    """Load and type every value. Errors are appended to `errors` (list) when given, else raised."""
    ds = Dataset()
    for a, triples in raw_load(directory).items():
        rows = ds.assocs.setdefault(a, {})
        for r, c, v in triples:
            t = schema.col_type(a, c)
            try:
                if t is None:
                    raise SchemaError("undeclared column %r" % c)
                val = from_text(t, v)
            except SchemaError as e:
                if errors is None:
                    raise
                errors.append("%s: %s %s: %s" % (a, r, c, e)); continue
            if c in rows.setdefault(r, {}):
                msg = "%s: duplicate triple %s %s" % (a, r, c)
                if errors is None: raise SchemaError(msg)
                errors.append(msg)
            rows[r][c] = val
    return ds


def to_triples(rows, schema, assoc):
    out = []
    for r, cols in rows.items():
        for c, v in cols.items():
            t = schema.col_type(assoc, c)
            if t is None:
                raise SchemaError("%s: undeclared column %r (declare it in the schema)" % (assoc, c))
            out.append((r, c, to_text(t, v)))
    return out


def write_dataset(ds, directory, schema):
    """Write each assoc deterministically; returns {filename: text}."""
    os.makedirs(directory, exist_ok=True)
    written = {}
    for a in sorted(ds.assocs):
        text = serialize(to_triples(ds.assocs[a], schema, a))
        path = os.path.join(directory, a + ".tsv")
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        written[a + ".tsv"] = text
    return written
