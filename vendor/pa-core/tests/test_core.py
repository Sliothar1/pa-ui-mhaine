"""pa-core tests: escaping/round-trip, types, determinism, validation, privacy negatives, diff guard, CLI."""
import io, json, os, random, shutil, subprocess, sys, tempfile, unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from pa_core import tsvio, __version__
from pa_core.schema import Schema, SchemaError, to_text, from_text, parse_row_key
from pa_core.validate import validate
from pa_core.export import plan_export, export, ExportError
from pa_core.diff import diff, load_side
from pa_core.inspect_row import inspect
from pa_core.adapters import json_claims, tabular
from pa_core.cli import main as cli

FX = os.path.join(HERE, "fixtures")
CL = os.path.join(FX, "claims")
SE = os.path.join(FX, "sensitive")
TB = os.path.join(FX, "table")


def jl(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


class Escaping(unittest.TestCase):
    def test_specials_roundtrip(self):
        for s in ["", "a\tb", "a\nb", "a|b", "a\\b", "\\t", "\\N", "\\", "|||", "x\r\ny", "\t\n|\\"]:
            e = tsvio.escape(s)
            self.assertNotIn("\t", e); self.assertNotIn("\n", e); self.assertNotIn("\r", e)
            self.assertEqual(tsvio.unescape(e), s)
            self.assertEqual(tsvio.decode_val(tsvio.encode_val(s)), s)

    def test_null_distinct_from_literal(self):
        self.assertEqual(tsvio.encode_val(None), "\\N")
        self.assertEqual(tsvio.encode_val("\\N"), "\\\\N")
        self.assertIsNone(tsvio.decode_val("\\N"))
        self.assertEqual(tsvio.decode_val("\\\\N"), "\\N")
        self.assertEqual(tsvio.decode_val(""), "")

    def test_random_roundtrip(self):
        rnd = random.Random(42)
        alphabet = "ab|\\\t\nN \u00e1\u00fa\r"
        for _ in range(2000):
            s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 12)))
            self.assertEqual(tsvio.unescape(tsvio.escape(s)), s)

    def test_invalid_escapes_rejected(self):
        for bad in ["a\\x", "trailing\\", "\\q"]:
            with self.assertRaises(tsvio.TSVError):
                tsvio.unescape(bad)

    def test_keys_split_on_unescaped_pipe_only(self):
        self.assertEqual(tsvio.split_key("field|qual"), ["field", "qual"])
        self.assertEqual(tsvio.split_key("a\\|b|c"), ["a|b", "c"])
        self.assertEqual(tsvio.join_key(["a|b", "c"]), "a\\|b|c")

    def test_file_roundtrip_and_wrong_field_count(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "A_x.tsv")
        trip = [("t:1", "f", "x\ty\nz|\\"), ("t:1", "g", None), ("t:2", "f", "")]
        tsvio.write_triples(p, trip)
        self.assertEqual(sorted(tsvio.read_triples(p)), sorted(trip))
        with open(p, "a", encoding="utf-8") as fh:
            fh.write("t:3\tonly-two\n")
        with self.assertRaises(tsvio.TSVError):
            tsvio.read_triples(p)


class Determinism(unittest.TestCase):
    def test_sorted_and_order_independent(self):
        trip = [("b:2", "z", "1"), ("a:1", "y", "2"), ("a:1", "b", "3"), ("a:10", "a", None), ("a:1|q", "a", "x")]
        outs = set()
        for seed in range(10):
            t = trip[:]; random.Random(seed).shuffle(t)
            outs.add(tsvio.serialize(t))
        self.assertEqual(len(outs), 1)
        out = outs.pop()
        self.assertTrue(out.endswith("\n"))
        self.assertEqual([l.split("\t")[:2] for l in out.splitlines()][0], ["a:1", "b"])


class Types(unittest.TestCase):
    def test_ids_stay_strings(self):
        self.assertEqual(from_text("str", "007"), "007")
        self.assertEqual(to_text("str", "007"), "007")
        with self.assertRaises(SchemaError):
            from_text("int", "007")

    def test_canonical_forms(self):
        self.assertEqual(to_text("int", 9), "9")
        self.assertEqual(to_text("float", 53.52), "53.52")
        self.assertEqual(to_text("bool", True), "true")
        self.assertEqual(to_text("json", {"b": 1, "a": [1.5, None]}), '{"a":[1.5,null],"b":1}')
        with self.assertRaises(SchemaError): from_text("json", '{"b":1, "a":2}')
        with self.assertRaises(SchemaError): from_text("bool", "True")
        with self.assertRaises(SchemaError): to_text("int", True)
        with self.assertRaises(SchemaError): from_text("flag", "2")
        with self.assertRaises(SchemaError): to_text("str", None)
        self.assertIsNone(to_text("str?", None))

    def test_row_keys(self):
        self.assertEqual(parse_row_key("claim:UM-C01"), ("claim", "UM-C01", None))
        self.assertEqual(parse_row_key("obs:B1|2026-10-11T00:00:00Z"), ("obs", "B1", "2026-10-11T00:00:00Z"))
        for bad in ["SMR123", "Mon:SMR123", "mon:", "mon:a b"]:
            with self.assertRaises(SchemaError):
                parse_row_key(bad)

    def test_reserved_namespaces_cannot_be_declared(self):
        for ns in ("prov|x", "meta|x", "sys|x", "claim|x", "visibility|public"):
            with self.assertRaises(SchemaError):
                Schema({"schema_version": 1, "assocs": {"A_x": {"columns": {ns: "str"}}}})
        # a bare field named like a namespace (Uí Mhaine's claim text column) is fine
        s = Schema({"schema_version": 1, "assocs": {"A_x": {"columns": {"claim": "str"}}}})
        self.assertEqual(s.col_type("A_x", "claim"), "str")
        self.assertEqual(s.col_type("A_x", "claim|claim:UM-C01"), "flag")


class Claims(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "d4m")
        self.schema = Schema.load(os.path.join(CL, "schema.json"))
        self.cfg = jl(os.path.join(CL, "adapter.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def ingest(self):
        return json_claims.ingest(self.cfg, self.schema, self.out, root=CL)

    def test_ingest_validate_reconstruct(self):
        self.ingest()
        self.assertEqual(validate(self.out, self.schema), [])
        self.assertEqual(json_claims.roundtrip_errors(self.cfg, self.schema, self.out, CL), [])
        rec = json_claims.reconstruct(self.cfg, self.schema, self.out)
        src = jl(os.path.join(CL, "claims.json"))
        self.assertEqual([c["id"] for c in rec["claims.json"]["claims"]], ["FX-C02", "FX-C01"])
        self.assertEqual(rec["claims.json"], src)
        self.assertIsNone(rec["claims.json"]["claims"][1]["pinned"])
        self.assertEqual(rec["claims.json"]["claims"][0]["code"], "007")
        self.assertEqual(rec["eras.json"], jl(os.path.join(CL, "eras.json")))

    def test_prov_status_derivation(self):
        ds, _ = self.ingest()
        prov = ds.assocs["A_prov"]
        self.assertEqual(prov["court:FX-P01"]["prov|status"], "pinned")
        self.assertEqual(prov["claim:FX-C01"]["prov|status"], "annal identified, entry not pinned")
        self.assertEqual(prov["era:MID"]["prov|status"], "interpretation")

    def test_reingest_is_byte_identical(self):
        _, w1 = self.ingest()
        os.environ["SOURCE_DATE_EPOCH"] = "2000000000"
        try:
            _, w2 = self.ingest()
        finally:
            del os.environ["SOURCE_DATE_EPOCH"]
        self.assertEqual(w1, w2)  # fetched_at kept because sha256 unchanged

    def test_dry_run_writes_nothing(self):
        json_claims.ingest(self.cfg, self.schema, self.out, root=CL, dry_run=True)
        self.assertFalse(os.path.exists(self.out))

    def test_unknown_status_needs_override(self):
        src = os.path.join(self.tmp, "src"); shutil.copytree(CL, src)
        d = jl(os.path.join(src, "claims.json")); d["places"][0]["status"] = "identified roughly"
        json.dump(d, open(os.path.join(src, "claims.json"), "w"))
        with self.assertRaises(json_claims.AdapterError):
            json_claims.ingest(self.cfg, self.schema, self.out, root=src)
        cfg = dict(self.cfg, prov_status_overrides={"court:FX-P01": "partly pinned"})
        ds, _ = json_claims.ingest(cfg, self.schema, self.out, root=src)
        self.assertEqual(ds.assocs["A_prov"]["court:FX-P01"]["prov|status"], "partly pinned")

    def test_duplicate_ids_rejected(self):
        src = os.path.join(self.tmp, "src"); shutil.copytree(CL, src)
        d = jl(os.path.join(src, "claims.json")); d["claims"][1]["id"] = "FX-C02"
        json.dump(d, open(os.path.join(src, "claims.json"), "w"))
        with self.assertRaises(json_claims.AdapterError):
            json_claims.ingest(self.cfg, self.schema, self.out, root=src)

    def _mutate(self, fname, fn):
        p = os.path.join(self.out, fname)
        lines = open(p, encoding="utf-8").read().splitlines()
        open(p, "w", encoding="utf-8").write("".join(l + "\n" for l in fn(lines)))

    def test_validation_negatives(self):
        cases = {
            "missing prov": ("A_prov.tsv", lambda L: [l for l in L if not l.startswith("claim:FX-C01\t")], "missing provenance"),
            "bad status": ("A_prov.tsv", lambda L: [l.replace("prov|status\tpinned", "prov|status\tsorta") for l in L], "not in vocabulary"),
            "no fetched_at": ("A_prov.tsv", lambda L: [l for l in L if not (l.startswith("era:MID\t") and "fetched_at" in l)], "fetched_at missing"),
            "no visibility": ("A_era.tsv", lambda L: [l for l in L if not (l.startswith("era:MID\t") and "visibility" in l)], "visibility"),
            "undeclared col": ("A_era.tsv", lambda L: L + ["era:MID\tcolour\tred"], "undeclared column"),
            "duplicate triple": ("A_era.tsv", lambda L: L + [L[0]], "duplicate triple"),
            "bad type": ("A_claim.tsv", lambda L: [l.replace("\tzoom\t9", "\tzoom\tnine") for l in L], "canonical int"),
            "missing required": ("A_claim.tsv", lambda L: [l for l in L if not l.startswith("claim:FX-C01\tdate\t")], "missing required column date"),
            "prov outside A_prov": ("A_era.tsv", lambda L: L + ["era:MID\tprov|source\tx"], "A_prov only"),
            "bad row key": ("A_era.tsv", lambda L: L + ["SMR123\tring\t[]"], "missing type"),
        }
        for name, (f, fn, needle) in cases.items():
            with self.subTest(name):
                shutil.rmtree(self.out, ignore_errors=True); self.ingest(); self._mutate(f, fn)
                errs = validate(self.out, self.schema)
                self.assertTrue(any(needle in e for e in errs), (name, errs))

    def test_export_allowlist_and_prov(self):
        self.ingest()
        plan = plan_export(self.out, self.schema, jl(os.path.join(CL, "allow.json")))
        self.assertEqual(sorted(plan), ["claim", "court", "era"])  # status/ledger are config: never exported
        c = plan["claim"]["claim:FX-C02"]
        self.assertNotIn("centre", c)  # not allow-listed
        for k in ("prov|source", "prov|status", "prov|fetched_at", "prov|sha256", "prov|code_sha"):
            self.assertIn(k, c)

    def test_inspect_links(self):
        self.ingest()
        r = inspect(self.out, self.schema, "era:MID")
        self.assertIn("claim:FX-C02", r["linked"])
        self.assertEqual(r["status"], "interpretation")
        self.assertIsNone(inspect(self.out, self.schema, "era:NOPE"))


class Privacy(unittest.TestCase):
    """Negative tests on a sensitive fixture: restricted rows and consent/age_band/email never leave."""
    def setUp(self):
        self.schema = Schema.load(os.path.join(SE, "schema.json"))
        self.allow = jl(os.path.join(SE, "allow.json"))

    def test_fixture_valid(self):
        self.assertEqual(validate(SE, self.schema), [])

    def test_export_never_emits_sensitive(self):
        to = tempfile.mkdtemp()
        try:
            export(SE, self.schema, self.allow, to)
            blob = "".join(open(os.path.join(to, f), encoding="utf-8").read() for f in sorted(os.listdir(to)))
            for needle in ("consent", "age_band", "u16", "parent", "SECRET-RESTRICTED-NOTE", "find:F2", "someone@example.com", "visibility"):
                self.assertNotIn(needle, blob)
            self.assertIn("shell found", blob)
        finally:
            shutil.rmtree(to)

    def test_default_deny(self):
        self.assertEqual(plan_export(SE, self.schema, {"types": {}}), {})
        self.assertEqual(plan_export(SE, self.schema, {"types": {"find": ["note"]}, "include_prov": False}),
                         {"find": {"find:F1": {"note": "shell found"}}})

    def test_export_refuses_invalid(self):
        d = tempfile.mkdtemp()
        try:
            shutil.copy(os.path.join(SE, "A_obs.tsv"), d)
            with self.assertRaises(ExportError):
                plan_export(d, self.schema, self.allow)  # no A_prov
        finally:
            shutil.rmtree(d)


class DiffGuard(unittest.TestCase):
    def side(self, n, typ="claim"):
        return {"A_claim": {("%s:%d" % (typ, i), "id"): str(i) for i in range(n)}}

    def test_drop_over_threshold_fails(self):
        _, fails = diff(self.side(100), self.side(85), max_drop_pct=10)
        self.assertTrue(fails)

    def test_drop_under_threshold_passes(self):
        _, fails = diff(self.side(100), self.side(95), max_drop_pct=10)
        self.assertEqual(fails, [])

    def test_growth_and_new_base_pass(self):
        self.assertEqual(diff(self.side(5), self.side(50))[1], [])
        self.assertEqual(diff({}, self.side(5))[1], [])

    def test_strict(self):
        b = self.side(3); h = {"A_claim": dict(b["A_claim"])}; h["A_claim"][("claim:0", "id")] = "x"
        self.assertEqual(diff(b, h)[1], [])
        self.assertTrue(diff(b, h, strict=True)[1])

    def test_git_side(self):
        d = tempfile.mkdtemp()
        try:
            g = lambda *a: subprocess.run(["git", "-C", d] + list(a), check=True, capture_output=True)
            g("init", "-q"); os.makedirs(os.path.join(d, "data/d4m"))
            tsvio.write_triples(os.path.join(d, "data/d4m/A_claim.tsv"), [("claim:%d" % i, "id", str(i)) for i in range(10)])
            g("add", "."); g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x")
            cwd = os.getcwd(); os.chdir(d)
            try:
                base = load_side("git:HEAD")
            finally:
                os.chdir(cwd)
            self.assertEqual(len(base["A_claim"]), 10)
        finally:
            shutil.rmtree(d)


class Tabular(unittest.TestCase):
    """v0.2.0: CSV/TSV adapter (first used by PA Réalt), json_ordered, rows in several assocs."""
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); self.out = os.path.join(self.tmp, "d4m")
        self.schema = Schema.load(os.path.join(TB, "schema.json")); self.cfg = jl(os.path.join(TB, "adapter.json"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_ingest_validate_roundtrip_bytes(self):
        ds, _ = tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        self.assertEqual(validate(self.out, self.schema), [])
        self.assertEqual(tabular.roundtrip_errors(self.cfg, self.schema, self.out, TB), [])
        m = ds.assocs["A_mon"]
        self.assertEqual(m["mon:007"]["county_idx"], 1)          # typed int
        self.assertEqual(m["mon:CL004-016042-"]["townland_ga"], " ")  # whitespace kept
        self.assertEqual(m["mon:CL004-016042-"]["lat"], 53.09698)
        self.assertIn("mon:NI:ANT001:001", m)
        self.assertEqual(ds.assocs["A_prov"]["mon:NI:ANT001:001"]["prov|source"], "Fixture NI SMR, record NI:ANT001:001")
        self.assertEqual(ds.assocs["A_prov"]["mon:007"]["prov|source"], "Fixture SMR, record 007")

    def test_json_ordered_keeps_key_order(self):
        tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        _, recs, meta = tabular.reconstruct(self.cfg, self.schema, self.out, None if False else tabular.read_table(os.path.join(TB, "mon.csv"))[0])
        self.assertEqual(list(meta["groups"]), ["wt", "pt"])
        self.assertEqual(json.dumps(meta), json.dumps(jl(os.path.join(TB, "meta.json"))))
        self.assertEqual([r[0] for r in recs], ["CL002-077----", "CL004-016042-", "NI:ANT001:001", "007"])
        with self.assertRaises(SchemaError):
            from_text("json_ordered", '{"a": 1}')

    def test_reingest_identical_and_edit_detected(self):
        _, w1 = tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        _, w2 = tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        self.assertEqual(w1, w2)
        src = os.path.join(self.tmp, "src"); shutil.copytree(TB, src)
        with open(os.path.join(src, "mon.csv"), "a", encoding="utf-8") as fh:
            fh.write("X1,pt,53.0,-7.0,,,1,0,0\n")
        self.assertTrue(tabular.roundtrip_errors(self.cfg, self.schema, self.out, src))

    def test_bad_cells_and_duplicates_rejected(self):
        for line in ("X1,pt,abc,-7.0,,,1,0,0\n", "007,pt,53.0,-7.0,,,1,0,0\n", "X2,pt,53.0\n"):
            with self.subTest(line):
                src = os.path.join(self.tmp, "s"); shutil.rmtree(src, ignore_errors=True); shutil.copytree(TB, src)
                with open(os.path.join(src, "mon.csv"), "a", encoding="utf-8") as fh:
                    fh.write(line)
                with self.assertRaises(json_claims.AdapterError):
                    tabular.ingest(self.cfg, self.schema, self.out, root=src)

    def test_row_in_several_assocs(self):
        tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        tsvio.write_triples(os.path.join(self.out, "A_prop.tsv"), [("mon:007", "class|pt", "1")])
        self.assertEqual(validate(self.out, self.schema), [])
        r = inspect(self.out, self.schema, "mon:007")
        self.assertEqual(sorted(r["assocs"]), ["A_mon", "A_prop"])
        # visibility twice across assocs is an error
        tsvio.write_triples(os.path.join(self.out, "A_prop.tsv"), [("mon:007", "class|pt", "1"), ("mon:007", "visibility|restricted", "1")])
        self.assertTrue(any("visibility" in e for e in validate(self.out, self.schema)))

    def test_export_allowlist(self):
        tabular.ingest(self.cfg, self.schema, self.out, root=TB)
        plan = plan_export(self.out, self.schema, jl(os.path.join(TB, "allow.json")))
        self.assertEqual(sorted(plan["mon"]["mon:007"]), ["group", "lat", "lon", "meta|order"])
        self.assertEqual(list(plan["dataset"]["dataset:smr"]["meta"]["groups"]), ["wt", "pt"])
        to = os.path.join(self.tmp, "exp"); export(self.out, self.schema, jl(os.path.join(TB, "allow.json")), to)
        self.assertEqual(list(jl(os.path.join(to, "dataset.json"))["dataset:smr"]["meta"]["groups"]), ["wt", "pt"])


class CLI(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli(list(args))
        return rc, buf.getvalue()

    def test_end_to_end(self):
        tmp = tempfile.mkdtemp(); out = os.path.join(tmp, "d4m")
        try:
            sch, cfg = os.path.join(CL, "schema.json"), os.path.join(CL, "adapter.json")
            self.assertEqual(self.run_cli("ingest", "json-claims", "--config", cfg, "--schema", sch, "--out", out, "--root", CL)[0], 0)
            self.assertEqual(self.run_cli("validate", out, "--schema", sch, "--roundtrip", cfg, "--root", CL)[0], 0)
            rc, txt = self.run_cli("inspect", "claim:FX-C02", out, "--schema", sch)
            self.assertEqual(rc, 0); self.assertIn("prov|sha256", txt)
            self.assertEqual(self.run_cli("export", out, "--schema", sch, "--allow", os.path.join(CL, "allow.json"), "--to", os.path.join(tmp, "site"))[0], 0)
            self.assertEqual(self.run_cli("diff", out, out, "--strict")[0], 0)
            self.assertEqual(self.run_cli("diff", out, os.path.join(tmp, "empty"))[0], 1)
        finally:
            shutil.rmtree(tmp)

    def test_version(self):
        self.assertEqual(__version__, "0.2.0")


if __name__ == "__main__":
    unittest.main()
