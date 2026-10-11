import hashlib, json, os, time

from . import __version__

_PKG = os.path.dirname(os.path.abspath(__file__))


def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_obj(obj):
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def code_sha():
    """Content hash of the pa_core package sources: stable per release, identical when vendored."""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(_PKG):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(files):
            if f.endswith(".py"):
                p = os.path.join(root, f)
                h.update(os.path.relpath(p, _PKG).replace(os.sep, "/").encode() + b"\0")
                with open(p, "rb") as fh:
                    h.update(fh.read().replace(b"\r\n", b"\n") + b"\0")
    return "pa-core-%s+%s" % (__version__, h.hexdigest()[:12])


def now_z():
    t = os.environ.get("SOURCE_DATE_EPOCH")
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t) if t else None))
