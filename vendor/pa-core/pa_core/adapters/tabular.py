"""tabular adapter: one CSV or TSV table (header row, one record per line) -> one assoc (+ A_prov), and back.

Config (JSON):
{
 "adapter": "tabular",
 "file": "data/monuments.csv", "delimiter": ",",
 "assoc": "A_mon", "type": "mon", "id_col": "smrs",
 "source": "NMS SMR open data, record {id}",          # prov|source template; {id} = id cell
 "source_by_prefix": {"NI:": "NI SMR, record {id}"},   # optional, longest matching id prefix wins
 "status": "pinned",
 "meta_json": {"file": "data/monuments_meta.json", "row": "dataset:smr", "col": "meta",
               "source": "...", "status": "pinned"}  # optional: a whole JSON document as one json_ordered cell
}
Cells are typed by the site schema (str, int, float, bool; canonical text). An empty cell is the
empty string for str columns and null for nullable non-str columns. Row order is kept in meta|order.
The table is read and written with Python's csv module (`write_table` is deterministic: LF line
ends, minimal quoting), so `roundtrip_errors` can demand byte equality with the source file.
"""
import csv, io, json, os

from ..dataset import Dataset, typed_load, write_dataset
from ..provenance import sha256_obj, code_sha, now_z
from ..schema import from_text, to_text, SchemaError
from .json_claims import AdapterError, _status


def read_table(path, delimiter=","):
    with open(path, encoding="utf-8", newline="") as fh:
        rd = csv.reader(fh, delimiter=delimiter)
        rows = list(rd)
    if not rows:
        raise AdapterError("%s: empty table" % path)
    return rows[0], rows[1:]


def table_text(header, records, delimiter=","):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(header)
    for r in records:
        w.writerow(r)
    return buf.getvalue()


def write_table(path, header, records, delimiter=","):
    text = table_text(header, records, delimiter)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return text


def _source(cfg, ident):
    best = None
    for pre, tpl in cfg.get("source_by_prefix", {}).items():
        if ident.startswith(pre) and (best is None or len(pre) > len(best[0])):
            best = (pre, tpl)
    return (best[1] if best else cfg["source"]).replace("{id}", ident)


def _cell(schema, assoc, col, text):
    t = schema.col_type(assoc, col)
    if t is None:
        raise AdapterError("%s: column %r is not declared in the schema" % (assoc, col))
    if text == "" and t.rstrip("?") != "str":
        return from_text(t, None)
    try:
        return from_text(t, text)
    except SchemaError as e:
        raise AdapterError("%s %s: %s" % (assoc, col, e))


def build(cfg, schema, root=".", previous=None):
    vocab = schema.status_vocab
    overrides = cfg.get("prov_status_overrides", {})
    csha = code_sha()
    prevprov = previous.assocs.get("A_prov", {}) if previous else {}
    ds = Dataset({"A_prov": {}, cfg["assoc"]: {}})
    prov, rows = ds.assocs["A_prov"], ds.assocs[cfg["assoc"]]

    def stamp(row, record, source, status):
        sha = sha256_obj(record)
        old = prevprov.get(row, {})
        prov[row] = {"prov|source": source, "prov|status": _status(status, vocab, row, overrides),
                     "prov|sha256": sha, "prov|code_sha": csha,
                     "prov|fetched_at": old["prov|fetched_at"] if old.get("prov|sha256") == sha and old.get("prov|fetched_at") else now_z()}

    header, recs = read_table(os.path.join(root, cfg["file"]), cfg.get("delimiter", ","))
    if cfg["id_col"] not in header:
        raise AdapterError("%s: id column %r missing" % (cfg["file"], cfg["id_col"]))
    if len(set(header)) != len(header):
        raise AdapterError("%s: duplicate header names" % cfg["file"])
    ix = header.index(cfg["id_col"])
    for i, rec in enumerate(recs):
        if len(rec) != len(header):
            raise AdapterError("%s line %d: %d cells, header has %d" % (cfg["file"], i + 2, len(rec), len(header)))
        ident = rec[ix]
        row = "%s:%s" % (cfg["type"], ident)
        if row in rows:
            raise AdapterError("duplicate row %s (duplicate id)" % row)
        cols = {h: _cell(schema, cfg["assoc"], h, v) for h, v in zip(header, rec) if h != cfg["id_col"]}
        cols["meta|order"] = i
        cols["visibility|public"] = 1
        rows[row] = cols
        stamp(row, dict(zip(header, rec)), _source(cfg, ident), cfg["status"])
    mj = cfg.get("meta_json")
    if mj:
        with open(os.path.join(root, mj["file"]), encoding="utf-8") as fh:
            doc = json.load(fh)
        rows[mj["row"]] = {mj["col"]: doc, "visibility|public": 1}
        stamp(mj["row"], doc, mj["source"], mj["status"])
    return ds, header


def ingest(cfg, schema, out, root=".", dry_run=False):
    previous = typed_load(out, schema, errors=[]) if os.path.isdir(out) else None  # lenient: only A_prov fetched_at is reused
    ds, _ = build(cfg, schema, root, previous)
    if dry_run:
        return ds, None
    return ds, write_dataset(ds, out, schema)


def reconstruct(cfg, schema, directory, header=None):
    """-> (header, records as lists of text cells in source order, meta_json_doc_or_None)."""
    ds = typed_load(directory, schema)
    rows = ds.assocs.get(cfg["assoc"], {})
    sel = sorted((c["meta|order"], r, c) for r, c in rows.items() if r.split(":", 1)[0] == cfg["type"])
    if header is None:
        header, _ = read_table(cfg["file"], cfg.get("delimiter", ","))
    recs = []
    for _, r, c in sel:
        rec = []
        for h in header:
            if h == cfg["id_col"]:
                rec.append(r.split(":", 1)[1]); continue
            v = c.get(h)
            t = schema.col_type(cfg["assoc"], h)
            rec.append("" if v is None else to_text(t, v))
        recs.append(rec)
    mj = cfg.get("meta_json")
    meta = rows.get(mj["row"], {}).get(mj["col"]) if mj else None
    return header, recs, meta


def roundtrip_errors(cfg, schema, directory, root="."):
    errs = []
    path = os.path.join(root, cfg["file"])
    header, _ = read_table(path, cfg.get("delimiter", ","))
    h, recs, meta = reconstruct(cfg, schema, directory, header)
    with open(path, encoding="utf-8", newline="") as fh:
        if fh.read() != table_text(h, recs, cfg.get("delimiter", ",")):
            errs.append("%s: TSVs do not reproduce the table byte for byte (re-run ingest)" % cfg["file"])
    mj = cfg.get("meta_json")
    if mj:
        with open(os.path.join(root, mj["file"]), encoding="utf-8") as fh:
            if json.load(fh) != meta:
                errs.append("%s: TSVs do not reproduce the JSON (re-run ingest)" % mj["file"])
    return errs
