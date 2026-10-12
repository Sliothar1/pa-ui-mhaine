"""Edge-row convention (docs/EDGES.md), golden fixtures, and the parity gate (docs/PARITY-GATE.md)."""
import io, os, shutil, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pa_core.schema import Schema
from pa_core.validate import validate
from pa_core.edges import edge_errors
from pa_core.export import export
from pa_core import parity, tsvio
from pa_core.cli import main as cli

ED = os.path.join(HERE, "fixtures", "edges")
SCH = Schema.load(os.path.join(ED, "schema.json"))


def copy_ds():
    d = tempfile.mkdtemp()
    for n in os.listdir(ED):
        if n.startswith("A_"):
            shutil.copy(os.path.join(ED, n), d)
    return d


def edit(d, assoc, fn):
    p = os.path.join(d, assoc + ".tsv")
    t = tsvio.read_triples(p)
    tsvio.write_triples(p, fn(t))


class Edges(unittest.TestCase):
    def test_golden_fixture_valid(self):
        self.assertEqual(validate(ED, SCH), [])
        self.assertEqual(edge_errors(ED, SCH), [])

    def test_golden_export_bytes(self):
        out = tempfile.mkdtemp()
        export(ED, SCH, {"types": {"player": ["name"], "club": "*", "match": "*", "role": "*", "edge": "*", "claim": "*"},
                         "include_prov": True}, out)
        rep = parity.byte_report(os.path.join(ED, "golden"), out)
        self.assertTrue(rep["equal"], rep)

    def test_player_private_field_not_exported(self):
        import json
        with open(os.path.join(ED, "golden", "player.json"), encoding="utf-8") as fh:
            self.assertNotIn("deceased", json.load(fh)["player:P-0001"])

    def _bad(self, assoc, fn, needle):
        d = copy_ds(); edit(d, assoc, fn)
        errs = validate(d, SCH) + edge_errors(d, SCH)
        self.assertTrue(any(needle in e for e in errs), errs)

    def test_dangling_endpoint(self):
        self._bad("A_edge", lambda t: [(r, c, "club:C-9999" if (r, c) == ("edge:E-0001", "to") else v) for r, c, v in t], "no such row")

    def test_unknown_role(self):
        self._bad("A_edge", lambda t: [(r, c, "goalie" if c == "role" and r == "edge:E-0001" else v) for r, c, v in t], "no role:goalie")

    def test_end_before_start(self):
        self._bad("A_edge", lambda t: [(r, c, "1940" if (r, c) == ("edge:E-0001", "end") else v) for r, c, v in t], "before start")

    def test_bad_date(self):
        self._bad("A_edge", lambda t: [(r, c, "c.1950" if (r, c) == ("edge:E-0001", "start") else v) for r, c, v in t], "must be YYYY")

    def test_edge_needs_claim(self):
        self._bad("A_edge", lambda t: [x for x in t if x[1] != "claim|CL-0001"], "needs at least one claim")

    def test_claim_must_exist(self):
        self._bad("A_edge", lambda t: [(r, "claim|CL-0404" if c == "claim|CL-0001" else c, v) for r, c, v in t], "has no claim:CL-0404")

    def test_public_edge_to_restricted_entity(self):
        self._bad("A_ent", lambda t: [(r, "visibility|restricted" if (r, c) == ("club:C-0001", "visibility|public") else c, v) for r, c, v in t],
                  "non-public club:C-0001")

    def test_cli_validate_edges(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli(["validate", ED, "--schema", os.path.join(ED, "schema.json"), "--edges"]), 0)


class Parity(unittest.TestCase):
    def test_identical_passes_and_negative_control_fails(self):
        d = copy_ds()
        rep = parity.compare(ED, d, SCH)
        self.assertFalse(rep["bytes"]["equal"])  # golden/ + generator live only in base
        rep = parity.compare(copy_ds(), d, SCH)
        self.assertTrue(rep["pass"], rep)
        ok, what = parity.negative_control(copy_ds(), d, SCH)
        self.assertTrue(ok, what)

    def test_value_change_detected_everywhere(self):
        a, b = copy_ds(), copy_ds()
        edit(b, "A_ent", lambda t: [(r, c, "Sample Club CLG" if v == "Sample Club GAA" else v) for r, c, v in t])
        rep = parity.compare(a, b, SCH)
        self.assertFalse(rep["pass"])
        self.assertEqual(rep["bytes"]["differ"], ["A_ent.tsv"])
        self.assertNotEqual(rep["semantic_hash"]["base"], rep["semantic_hash"]["head"])
        self.assertEqual(rep["schema_diff"], [])  # same shape, different value

    def test_visibility_and_type_changes_in_schema_diff(self):
        a, b = copy_ds(), copy_ds()
        edit(b, "A_ent", lambda t: [(r, "visibility|restricted" if (r, c) == ("role:member", "visibility|public") else c, v) for r, c, v in t])
        self.assertTrue(any("vis role:member" in l for l in parity.schema_diff(a, b, SCH)))
        self.assertTrue(any("visibility|restricted" in l for l in parity.schema_diff(a, b)))

    def test_semantic_hash_ignores_line_order(self):
        a, b = copy_ds(), copy_ds()
        p = os.path.join(b, "A_ent.tsv")
        with open(p, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(reversed(lines)) + "\n")
        self.assertEqual(parity.semantic_hash(a), parity.semantic_hash(b))
        self.assertFalse(parity.byte_report(a, b)["equal"])

    def test_cli_parity_exit_codes(self):
        a, b = copy_ds(), copy_ds()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli(["parity", a, b, "--schema", os.path.join(ED, "schema.json")]), 0)
        self.assertIn("parity gate: PASS", out.getvalue())
        edit(b, "A_claim", lambda t: t[:-1])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(cli(["parity", a, b]), 1)

    def test_output_dirs_without_tsv(self):
        a = os.path.join(ED, "golden"); b = tempfile.mkdtemp()
        shutil.rmtree(b); shutil.copytree(a, b)
        rep = parity.compare(a, b)
        self.assertTrue(rep["pass"]); self.assertNotIn("semantic_hash", rep)
        self.assertTrue(parity.negative_control(a, b)[0])


if __name__ == "__main__":
    unittest.main()
