"""Schema: key rules, per-column value types, reserved namespaces, status vocabulary.

A schema file is JSON:
{
  "schema_version": 1,
  "status_vocabulary_extra": ["annal identified, entry not pinned"],
  "prov_exempt_types": ["status"],            # config rows: no prov|status needed, never exportable
  "assocs": {
    "A_claim": {
      "columns": {"zoom": "int", "pinned": "str?", "centre": "json", "tag|*": "flag"},
      "required": {"claim": ["id", "date", "status"]}
    }
  }
}
Types: str, int, float, bool (true|false), json (compact, sorted keys), flag (must be 1).
A trailing `?` makes the column nullable (null is written \\N). Every column used must be
declared (strict). Reserved namespaces (prov|, meta|, sys|, claim|) and visibility| are
declared by the core and must not be redeclared by a site.
"""
import json, re

from . import SCHEMA_VERSION
from .tsvio import split_key

CORE_STATUS = ("pinned", "partly pinned", "annal identified", "year only",
               "needs source", "tradition", "interpretation")
RESERVED = ("prov", "meta", "sys", "claim")
PROV_REQUIRED = ("prov|source", "prov|status", "prov|fetched_at", "prov|sha256", "prov|code_sha")
CORE_COLUMNS = {
    "prov|source": "str", "prov|status": "str", "prov|fetched_at": "str", "prov|sha256": "str",
    "prov|code_sha": "str", "prov|pinned": "str?", "prov|confidence": "str?",
    "meta|order": "int", "meta|note": "str?",
    "visibility|public": "flag", "visibility|restricted": "flag",
    "sys|*": "str?", "claim|*": "flag",
}
TYPES = ("str", "int", "float", "bool", "json", "flag")
TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+-]*$")
QUAL_RE = re.compile(r"^[^\t\n\r]+$")
FIELD_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")


class SchemaError(ValueError):
    pass


def parse_row_key(raw):
    """`type:id[|qualifier]` -> (type, id, qualifier-or-None). Raises SchemaError."""
    parts = split_key(raw)
    if len(parts) > 2:
        raise SchemaError("row key %r: at most one | qualifier" % raw)
    head = parts[0]
    if ":" not in head:
        raise SchemaError("row key %r: missing type: prefix" % raw)
    typ, ident = head.split(":", 1)
    if not TYPE_RE.match(typ):
        raise SchemaError("row key %r: type must be lowercase [a-z][a-z0-9_]*" % raw)
    if not ID_RE.match(ident):
        raise SchemaError("row key %r: id must match %s" % (raw, ID_RE.pattern))
    q = parts[1] if len(parts) == 2 else None
    if q is not None and not QUAL_RE.match(q):
        raise SchemaError("row key %r: bad qualifier" % raw)
    return typ, ident, q


def parse_col_key(raw):
    parts = split_key(raw)
    if not FIELD_RE.match(parts[0]):
        raise SchemaError("col key %r: field must match %s" % (raw, FIELD_RE.pattern))
    if len(parts) > 2:
        raise SchemaError("col key %r: at most one | qualifier" % raw)
    return parts[0], (parts[1] if len(parts) == 2 else None)


def to_text(typ, v):
    """Typed python value -> canonical string (None stays None)."""
    base = typ.rstrip("?")
    if v is None:
        if not typ.endswith("?"):
            raise SchemaError("null in non-nullable %s column" % base)
        return None
    if base == "str":
        if not isinstance(v, str): raise SchemaError("expected str, got %r" % (v,))
        return v
    if base == "int":
        if isinstance(v, bool) or not isinstance(v, int): raise SchemaError("expected int, got %r" % (v,))
        return str(v)
    if base == "float":
        if isinstance(v, bool) or not isinstance(v, (int, float)): raise SchemaError("expected float, got %r" % (v,))
        return repr(float(v))
    if base == "bool":
        if not isinstance(v, bool): raise SchemaError("expected bool, got %r" % (v,))
        return "true" if v else "false"
    if base == "json":
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if base == "flag":
        if v not in (1, "1") or isinstance(v, bool): raise SchemaError("flag value must be 1, got %r" % (v,))
        return "1"
    raise SchemaError("unknown type %s" % typ)


def from_text(typ, s):
    """Canonical string -> typed value. Strict: rejects non-canonical forms."""
    base = typ.rstrip("?")
    if s is None:
        if not typ.endswith("?"):
            raise SchemaError("null in non-nullable %s column" % base)
        return None
    if base == "str":
        return s
    if base == "int":
        if not INT_RE.match(s): raise SchemaError("not a canonical int: %r" % s)
        return int(s)
    if base == "float":
        try: f = float(s)
        except ValueError: raise SchemaError("not a float: %r" % s)
        if repr(f) != s: raise SchemaError("non-canonical float %r (expected %r)" % (s, repr(f)))
        return f
    if base == "bool":
        if s not in ("true", "false"): raise SchemaError("bool must be true|false: %r" % s)
        return s == "true"
    if base == "json":
        try: v = json.loads(s)
        except ValueError as e: raise SchemaError("bad json %r: %s" % (s[:40], e))
        if to_text(typ, v) != s: raise SchemaError("non-canonical json %r" % s[:60])
        return v
    if base == "flag":
        if s != "1": raise SchemaError("flag value must be 1: %r" % s)
        return 1
    raise SchemaError("unknown type %s" % typ)


class Schema:
    def __init__(self, obj):
        if obj.get("schema_version") != SCHEMA_VERSION:
            raise SchemaError("schema_version must be %d" % SCHEMA_VERSION)
        self.raw = obj
        self.status_vocab = list(CORE_STATUS) + [s for s in obj.get("status_vocabulary_extra", []) if s not in CORE_STATUS]
        self.prov_exempt_types = set(obj.get("prov_exempt_types", []))
        self.assocs = {}
        for name, spec in obj.get("assocs", {}).items():
            if not re.match(r"^A_[a-z][a-z0-9_]*$", name):
                raise SchemaError("assoc name %r must be A_<lowercase>" % name)
            cols = dict(spec.get("columns", {}))
            for c, t in cols.items():
                f = c.split("|", 1)[0]
                if "|" in c and (f in RESERVED or f == "visibility"):
                    raise SchemaError("%s: column %r uses a reserved namespace (%s|)" % (name, c, f))
                if t.rstrip("?") not in TYPES or t.count("?") > 1:
                    raise SchemaError("%s: column %r has unknown type %r" % (name, c, t))
            self.assocs[name] = {"columns": cols, "required": spec.get("required", {})}
        if "A_prov" not in self.assocs:
            self.assocs["A_prov"] = {"columns": {}, "required": {}}

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls(json.load(fh))

    def col_type(self, assoc, col):
        """Declared type for a col key (escaped form) or None if undeclared."""
        for table in (CORE_COLUMNS, self.assocs.get(assoc, {}).get("columns", {})):
            if col in table:
                return table[col]
            field = col.split("|", 1)[0]
            if "|" in col and field + "|*" in table:
                return table[field + "|*"]
        return None
