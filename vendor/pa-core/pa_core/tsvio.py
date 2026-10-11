"""TSV triple I/O: `row \t col \t val`, UTF-8, LF, one triple per line.

Escaping (applied to row, col and val): backslash -> \\\\, tab -> \\t, newline -> \\n,
carriage return -> \\r, pipe -> \\| . The null value is the token \\N (a bare backslash-N,
which an escaped string can never produce). In row and col keys an *unescaped* `|` is the
qualifier separator; a literal pipe inside a key part is written `\\|`.

The serializer is deterministic: triples sorted by (row, col) on the unescaped keys
(Unicode code point order), no header, trailing newline, no BOM.
"""
NULL = "\\N"
_ESC = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r", "|": "\\|"}
_UNESC = {"\\": "\\", "t": "\t", "n": "\n", "r": "\r", "|": "|"}


class TSVError(ValueError):
    pass


def escape(s):
    return "".join(_ESC.get(ch, ch) for ch in s)


def unescape(s, keep_pipe_escapes=False):
    """Undo escape(). With keep_pipe_escapes the `\\|` sequence is kept (used for keys,
    where an unescaped `|` is structural)."""
    out, i, n = [], 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "\\":
            if i + 1 >= n:
                raise TSVError("dangling backslash in %r" % s)
            nx = s[i + 1]
            if nx not in _UNESC:
                raise TSVError("invalid escape \\%s in %r" % (nx, s))
            out.append("\\|" if (nx == "|" and keep_pipe_escapes) else _UNESC[nx])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def split_key(raw):
    """Split an escaped key on unescaped `|` and unescape each part."""
    parts, cur, i = [], [], 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            cur.append(raw[i:i + 2]); i += 2; continue
        if raw[i] == "|":
            parts.append(unescape("".join(cur))); cur = []; i += 1; continue
        cur.append(raw[i]); i += 1
    parts.append(unescape("".join(cur)))
    return parts


def join_key(parts):
    return "|".join(escape(p) for p in parts)


def encode_val(v):
    """v is the already-typed string form, or None for null."""
    return NULL if v is None else escape(v)


def decode_val(raw):
    return None if raw == NULL else unescape(raw)


def parse_lines(text, name="<tsv>"):
    """Yield (lineno, row_key_raw, col_key_raw, val_raw). Keys stay in escaped form."""
    if text.startswith("\ufeff"):
        raise TSVError("%s: BOM not allowed" % name)
    if "\r" in text:
        raise TSVError("%s: CR characters not allowed (use LF; escape CR as \\r)" % name)
    for ln, line in enumerate(text.split("\n"), 1):
        if line == "":
            continue
        f = line.split("\t")
        if len(f) != 3:
            raise TSVError("%s:%d: expected 3 tab-separated fields, got %d" % (name, ln, len(f)))
        yield ln, f[0], f[1], f[2]


def read_triples(path):
    """Return list of (row, col, val) with keys in escaped form and val unescaped (None = null)."""
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    out = []
    for ln, r, c, v in parse_lines(text, path):
        try:
            out.append((r, c, decode_val(v)))
        except TSVError as e:
            raise TSVError("%s:%d: %s" % (path, ln, e))
    return out


def serialize(triples):
    """triples: iterable of (row_key_escaped, col_key_escaped, val_str_or_None). Deterministic."""
    def k(t):
        return (split_key(t[0]), split_key(t[1]))
    lines = ["%s\t%s\t%s" % (r, c, encode_val(v)) for r, c, v in sorted(triples, key=k)]
    return "".join(l + "\n" for l in lines)


def write_triples(path, triples):
    data = serialize(triples)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(data)
    return data
