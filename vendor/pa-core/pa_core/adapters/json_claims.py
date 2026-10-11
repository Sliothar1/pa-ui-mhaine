"""json-claims adapter: hand-edited JSON ledgers -> assocs (+ A_prov), and back.

The JSON stays the editable source. `ingest` writes A_*.tsv; `reconstruct` rebuilds the JSON
objects from the TSVs (lossless: list order via meta|order, null vs absent, typed values), so a
site build can read only the TSVs. Config (JSON):
{
 "adapter": "json-claims",
 "sources": [
  {"file": "data/claims.json", "assoc": "A_claim",
   "lists": [{"key": "claims", "type": "claim", "id_key": "id", "source_key": "reference",
              "status_key": "status", "pinned_key": "pinned"}],
   "vocabulary": {"key": "status_values", "type": "status"},
   "scalars": {"type": "ledger", "id": "claims"}},
  {"file": "data/eras.json", "assoc": "A_era",
   "mapping": {"type": "era", "value_col": "ring", "source": "data/eras.json", "status": "interpretation"}}
 ],
 "prov_status_overrides": {"court:UM-P04": "partly pinned"}
}
A list entry takes either source_key/status_key (per record) or fixed source/status.
A record status that is not in the vocabulary maps to the longest vocabulary term it starts
with (e.g. "pinned · private land" -> pinned); otherwise an override is required.
"""
import json, os, re

from ..dataset import Dataset, typed_load, write_dataset
from ..provenance import sha256_obj, code_sha, now_z
from ..schema import SchemaError


class AdapterError(ValueError):
    pass


def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "x"


def _status(text, vocab, row, overrides):
    if row in overrides:
        return overrides[row]
    if text in vocab:
        return text
    hits = [v for v in vocab if text and text.startswith(v) and (len(text) == len(v) or not text[len(v)].isalnum())]
    if hits:
        return max(hits, key=len)
    raise AdapterError("%s: status %r is not in the vocabulary and has no prov_status_overrides entry" % (row, text))


def _get(obj, key):
    return obj if key in ("", None) else obj[key]


def build(config, schema, root=".", previous=None):
    """Return a Dataset built from the JSON sources. `previous` (Dataset) keeps fetched_at stable
    for records whose sha256 is unchanged."""
    vocab = schema.status_vocab
    overrides = config.get("prov_status_overrides", {})
    csha = code_sha()
    prevprov = (previous.assocs.get("A_prov", {}) if previous else {})
    ds = Dataset({"A_prov": {}})
    prov = ds.assocs["A_prov"]

    def put(assoc, row, cols, record, source, status):
        rows = ds.assocs.setdefault(assoc, {})
        if any(row in r for r in ds.assocs.values() if r is not prov):
            raise AdapterError("duplicate row %s (duplicate id)" % row)
        rows[row] = dict(cols, **{"visibility|public": 1})
        sha = sha256_obj(record)
        old = prevprov.get(row, {})
        p = {"prov|source": source, "prov|sha256": sha, "prov|code_sha": csha,
             "prov|fetched_at": old["prov|fetched_at"] if old.get("prov|sha256") == sha and old.get("prov|fetched_at") else now_z()}
        if status is not None:
            p["prov|status"] = status
        prov[row] = p

    for src in config["sources"]:
        path = os.path.join(root, src["file"])
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        used = set()
        for spec in src.get("lists", []):
            used.add(spec["key"])
            for i, rec in enumerate(_get(doc, spec["key"])):
                row = "%s:%s" % (spec["type"], rec[spec["id_key"]])
                cols = dict(rec); cols["meta|order"] = i
                srcv = rec.get(spec["source_key"]) if spec.get("source_key") else spec.get("source")
                if not srcv:
                    raise AdapterError("%s: no source (reference) to put in prov|source" % row)
                st = _status(rec.get(spec["status_key"]) if spec.get("status_key") else spec.get("status"), vocab, row, overrides)
                put(src["assoc"], row, cols, rec, srcv, st)
                if spec.get("pinned_key") and rec.get(spec["pinned_key"]):
                    prov[row]["prov|pinned"] = rec[spec["pinned_key"]]
        if "vocabulary" in src:
            v = src["vocabulary"]; used.add(v["key"])
            for i, (name, desc) in enumerate(_get(doc, v["key"]).items()):
                put(src["assoc"], "%s:%s" % (v["type"], _slug(name)), {"name": name, "description": desc, "meta|order": i},
                    {name: desc}, src["file"], None)
        if "mapping" in src:
            m = src["mapping"]
            for i, (k, val) in enumerate(_get(doc, m.get("key", "")).items()):
                put(src["assoc"], "%s:%s" % (m["type"], k), {m["value_col"]: val, "meta|order": i}, {k: val},
                    m["source"], _status(m["status"], vocab, "%s:%s" % (m["type"], k), overrides))
        if "scalars" in src:
            s = src["scalars"]
            rest = {k: v for k, v in doc.items() if k not in used}
            put(src["assoc"], "%s:%s" % (s["type"], s["id"]), dict(rest, **{"meta|order": 0}), rest, src["file"], None)
    return ds


def ingest(config, schema, out, root=".", dry_run=False):
    previous = typed_load(out, schema) if os.path.isdir(out) else None
    ds = build(config, schema, root, previous)
    if dry_run:
        return ds, None
    return ds, write_dataset(ds, out, schema)


def _strip(cols):
    return {k: v for k, v in cols.items() if not k.startswith(("meta|", "visibility|", "sys|"))}


def reconstruct(config, schema, directory):
    """Rebuild {file: json_object} from the TSVs in `directory`."""
    ds = typed_load(directory, schema)
    out = {}
    for src in config["sources"]:
        rows = ds.assocs.get(src["assoc"], {})

        def of_type(t):
            sel = [(cols.get("meta|order", 0), r, cols) for r, cols in rows.items() if r.split(":", 1)[0] == t]
            return [(r, cols) for _, r, cols in sorted(sel)]
        doc = {}
        if "scalars" in src:
            s = src["scalars"]
            doc.update(_strip(rows.get("%s:%s" % (s["type"], s["id"]), {})))
        if "vocabulary" in src:
            v = src["vocabulary"]
            doc[v["key"]] = {c["name"]: c["description"] for _, c in of_type(v["type"])}
        for spec in src.get("lists", []):
            doc[spec["key"]] = [_strip(c) for _, c in of_type(spec["type"])]
        if "mapping" in src:
            m = src["mapping"]
            mp = {r.split(":", 1)[1]: c[m["value_col"]] for r, c in of_type(m["type"])}
            if m.get("key"):
                doc[m["key"]] = mp
            else:
                doc.update(mp)
        out[src["file"]] = doc
    return out


def roundtrip_errors(config, schema, directory, root="."):
    """Canonical-JSON comparison of reconstruct() against the source files."""
    from ..provenance import canonical_json
    errs = []
    rec = reconstruct(config, schema, directory)
    for f, obj in rec.items():
        with open(os.path.join(root, f), encoding="utf-8") as fh:
            src = json.load(fh)
        if canonical_json(src) != canonical_json(obj):
            errs.append("%s: TSVs do not reproduce the source (re-run ingest)" % f)
    return errs
