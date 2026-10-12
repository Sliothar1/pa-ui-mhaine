"""Regenerate the edge golden fixture TSVs (synthetic data). Run from this directory."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from pa_core.tsvio import write_triples

S = "0" * 64
ent = [("player:P-0001", "name", "Sample Player"), ("player:P-0001", "deceased", "true"),
       ("club:C-0001", "name", "Sample Club GAA"), ("club:C-0002", "name", "Other Club GAA"),
       ("match:M-1959-0001", "date", "1959-09-06"), ("match:M-1959-0001", "competition", "Sample County SHC final"),
       ("match:M-1959-0001", "home", "club:C-0001"), ("match:M-1959-0001", "away", "club:C-0002"),
       ("role:member", "label", "club member (playing)"), ("role:right-corner-forward", "label", "right corner-forward")]
ent += [(r, "visibility|public", "1") for r in sorted({t[0] for t in ent})]
edge = [("edge:E-0001", "from", "player:P-0001"), ("edge:E-0001", "to", "club:C-0001"), ("edge:E-0001", "role", "member"),
        ("edge:E-0001", "start", "1950"), ("edge:E-0001", "end", "1962"), ("edge:E-0001", "claim|CL-0001", "1"),
        ("edge:E-0002", "from", "player:P-0001"), ("edge:E-0002", "to", "match:M-1959-0001"),
        ("edge:E-0002", "role", "right-corner-forward"), ("edge:E-0002", "start", "1959-09-06"),
        ("edge:E-0002", "end", "1959-09-06"), ("edge:E-0002", "claim|CL-0002", "1"), ("edge:E-0002", "claim|CL-0003", "1")]
edge += [(e, "visibility|public", "1") for e in ("edge:E-0001", "edge:E-0002")]
src = {"CL-0001": "Sample club history (1984), p. 41", "CL-0002": "Sample newspaper, 12 Sep 1959, p. 14",
       "CL-0003": "Sample newspaper, 5 Sep 1959, p. 9"}
text = {"CL-0001": "Club history lists P-0001 on senior panels 1950-1962",
        "CL-0002": "Match report names P-0001 at right corner-forward",
        "CL-0003": "Team list printed before the match names P-0001 at right corner-forward"}
claim = []
for k in sorted(src):
    claim += [("claim:" + k, "text", text[k]), ("claim:" + k, "cites", src[k]), ("claim:" + k, "visibility|public", "1")]
prov = []
for r in sorted({t[0] for t in ent + edge + claim}):
    s = src.get(r.split(":", 1)[1], "fixture: tests/fixtures/edges (synthetic)")
    st = "pinned" if r.startswith("claim:") else ("interpretation" if r.startswith("edge:") else "needs source")
    prov += [(r, "prov|source", s), (r, "prov|status", st), (r, "prov|fetched_at", "2026-10-11T00:00:00Z"),
             (r, "prov|sha256", S), (r, "prov|code_sha", "fixture")]
for n, t in (("A_ent", ent), ("A_edge", edge), ("A_claim", claim), ("A_prov", prov)):
    write_triples(n + ".tsv", t)
