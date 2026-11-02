"""Section 2a (tasks 11, 12, 13, 16): source schema, literature job,
brief assembler, contradiction check.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v
"""
import copy
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import ledger  # noqa: E402
import literature  # noqa: E402


def _src(sid, claim, stance="supports", locator="doi:10.0000/ex",
          h=None, cite=None):
    return {
        "id": sid,
        "citation": cite or ("Author A. (%s) Title of work. Venue." % sid),
        "retrieved_at": "2026-10-30",
        "access_note": "open-access, CC-BY",
        "supports_claim": claim,
        "locator": "%s:%s" % (locator, sid),
        "content_hash": h or ("ab" * 32),
        "stance": stance,
    }


CLAIM_X = "Compound X lowers blood pressure in adults"
SOURCES = [
    _src("SRC-1", CLAIM_X, "supports"),
    _src("SRC-2", CLAIM_X, "disputes"),
    _src("SRC-3", "Compound Y has no effect on sleep in mice"),
]


class TestSourceSchema(unittest.TestCase):
    def test_schema_file_loads_with_required_fields(self):
        p = os.path.join(_LAB, "schemas", "source.schema.json")
        d = json.load(open(p))
        self.assertEqual(d["type"], "object")
        for f in ("citation", "retrieved_at", "access_note",
                  "supports_claim", "locator", "content_hash"):
            self.assertIn(f, d["properties"], f)
            self.assertIn(f, d["required"], f)

    def test_valid_record_passes(self):
        self.assertEqual(literature.validate_source(SOURCES[0]), [])

    def test_missing_citation_rejected(self):
        bad = dict(SOURCES[0])
        del bad["citation"]
        self.assertTrue(any("citation" in e for e in literature.validate_source(bad)))
        with self.assertRaises(ValueError):
            literature.assert_valid_source(bad)

    def test_bad_hash_rejected(self):
        bad = dict(SOURCES[0], content_hash="not-a-hash")
        self.assertTrue(any("content_hash" in e for e in literature.validate_source(bad)))

    def test_bad_date_rejected(self):
        bad = dict(SOURCES[0], retrieved_at="sometime last fall")
        self.assertTrue(any("retrieved_at" in e for e in literature.validate_source(bad)))

    def test_bad_stance_rejected(self):
        bad = dict(SOURCES[0], stance="maybe")
        self.assertTrue(any("stance" in e for e in literature.validate_source(bad)))

    def test_non_dict_rejected(self):
        self.assertTrue(literature.validate_source(["not", "a", "record"]))


class TestLiteratureSearch(unittest.TestCase):
    def test_deterministic_same_inputs(self):
        b1 = literature.literature_search("Does compound X lower blood pressure?", SOURCES)
        b2 = literature.literature_search("Does compound X lower blood pressure?", list(SOURCES))
        self.assertEqual(b1, b2)

    def test_brief_shape_and_hashes(self):
        b = literature.literature_search("compound X blood pressure adults", SOURCES)
        self.assertIn("title", b)
        self.assertTrue(b["title"])
        ids = [s["id"] for s in b["sources"]]
        self.assertIn("SRC-1", ids)
        for s in b["sources"]:
            self.assertTrue(s["locator"])
            self.assertRegex(s["content_hash"], r"^[0-9a-fA-F]{64}$")

    def test_reads_local_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "shelf.json")
            json.dump(SOURCES, open(p, "w"))
            b = literature.literature_search("X lowers blood pressure in adults", p)
            self.assertEqual({s["id"] for s in b["sources"]}, {"SRC-1", "SRC-2"})

    def test_reads_local_directory(self):
        with tempfile.TemporaryDirectory() as td:
            for s in SOURCES:
                json.dump(s, open(os.path.join(td, s["id"] + ".json"), "w"))
            b = literature.literature_search("Y sleep mice effect", td)
            self.assertEqual([s["id"] for s in b["sources"]], ["SRC-3"])

    def test_no_match_is_honest_empty(self):
        b = literature.literature_search("quantum tunneling in cheese", SOURCES)
        self.assertEqual(b["sources"], [])

    def test_invalid_records_reported_never_sourced(self):
        bad = dict(SOURCES[0], id="SRC-BAD")
        del bad["content_hash"]  # a result without a hash is a lead
        b = literature.literature_search("compound X blood pressure", SOURCES + [bad])
        self.assertNotIn("SRC-BAD", [s["id"] for s in b["sources"]])
        self.assertTrue(any(i["id"] == "SRC-BAD" for i in b["invalid_sources"]))

    def test_empty_question_refused(self):
        with self.assertRaises(ValueError):
            literature.literature_search("   ", SOURCES)

    def test_model_and_network_are_unimplemented(self):
        with self.assertRaises(NotImplementedError) as cm:
            literature.search_remote("anything")
        self.assertIn(literature.UNIMPLEMENTED, str(cm.exception))
        with self.assertRaises(NotImplementedError) as cm:
            literature.synthesize_with_model({"title": "t"})
        self.assertIn(literature.UNIMPLEMENTED, str(cm.exception))


class TestAssembleBrief(unittest.TestCase):
    def test_pinned_claim_kept(self):
        b = literature.assemble_brief("q?", [CLAIM_X], SOURCES[:1])
        self.assertEqual(len(b["claims"]), 1)
        self.assertEqual(b["claims"][0]["pinned_sources"], ["SRC-1"])
        self.assertEqual(b["claims"][0]["status"], "pinned")
        self.assertEqual(b["dropped"], [])

    def test_unpinned_claim_dropped(self):
        b = literature.assemble_brief("q?", ["Moon cheese cures everything"], SOURCES)
        self.assertEqual(b["claims"], [])
        self.assertEqual(len(b["dropped"]), 1)
        self.assertIn("unpinned", b["dropped"][0]["reason"])

    def test_drop_logged_to_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "lab.jsonl")
            b = literature.assemble_brief("q?", [CLAIM_X, "Free energy from nothing"],
                                          SOURCES[:1], ledger_path=lp)
            self.assertEqual(len(b["claims"]), 1)
            self.assertEqual(len(b["dropped"]), 1)
            entries = ledger.read_all(lp)
            drops = [e for e in entries if e.get("kind") == "brief-claim-dropped"]
            self.assertEqual(len(drops), 1)
            self.assertIn("Free energy", drops[0]["claim"])
            ok, msg = ledger.verify_chain(lp)
            self.assertTrue(ok, msg)

    def test_explicit_citation_pins(self):
        claim = {"claim": "Something phrased differently", "source_ids": ["SRC-3"]}
        b = literature.assemble_brief("q?", [claim], SOURCES)
        self.assertEqual(len(b["claims"]), 1)
        self.assertEqual(b["claims"][0]["pinned_sources"], ["SRC-3"])

    def test_phantom_citation_warns_not_silent(self):
        claim = {"claim": CLAIM_X, "source_ids": ["SRC-1", "SRC-9"]}
        b = literature.assemble_brief("q?", [claim], SOURCES[:1])
        self.assertEqual(len(b["claims"]), 1)
        self.assertEqual(b["claims"][0]["pinned_sources"], ["SRC-1"])
        self.assertTrue(any("SRC-9" in w for w in b["claims"][0].get("warnings", [])))

    def test_invalid_source_record_refused(self):
        bad = dict(SOURCES[0])
        bad["content_hash"] = "zz"
        with self.assertRaises(ValueError):
            literature.assemble_brief("q?", [CLAIM_X], [bad])


class TestContested(unittest.TestCase):
    def test_opposing_stances_mark_contested(self):
        claims = [{"claim": CLAIM_X, "pinned_sources": ["SRC-1", "SRC-2"],
                   "status": "pinned"}]
        out = literature.mark_contested(claims, SOURCES)
        self.assertEqual(len(out), 1)  # kept, never dropped
        self.assertEqual(out[0]["status"], "contested")
        self.assertEqual(out[0]["contested_by"]["supports"], ["SRC-1"])
        self.assertEqual(out[0]["contested_by"]["disputes"], ["SRC-2"])
        self.assertIn("note", out[0])

    def test_unanimous_stays_pinned(self):
        claims = [{"claim": CLAIM_X, "pinned_sources": ["SRC-1"], "status": "pinned"}]
        out = literature.mark_contested(claims, SOURCES[:1])
        self.assertEqual(out[0]["status"], "pinned")
        self.assertNotIn("contested_by", out[0])

    def test_conflict_across_entries_merges_by_text(self):
        claims = [{"claim": CLAIM_X, "pinned_sources": ["SRC-1"]},
                  {"claim": CLAIM_X.lower(), "pinned_sources": ["SRC-2"]}]
        out = literature.mark_contested(claims, SOURCES)
        self.assertTrue(all(c["status"] == "contested" for c in out))
        self.assertEqual(len(out), 2)  # both kept, never silently resolved

    def test_inputs_not_mutated(self):
        claims = [{"claim": CLAIM_X, "pinned_sources": ["SRC-1", "SRC-2"],
                   "status": "pinned"}]
        snapshot = copy.deepcopy(claims)
        literature.mark_contested(claims, SOURCES)
        self.assertEqual(claims, snapshot)

    def test_end_to_end_assemble_then_contest(self):
        b = literature.assemble_brief("Does X lower blood pressure?",
                                      [CLAIM_X, "Unbacked assertion"], SOURCES)
        self.assertEqual(len(b["dropped"]), 1)  # unpinned dropped
        out = literature.mark_contested(b["claims"], SOURCES)
        self.assertEqual(out[0]["status"], "contested")  # conflict flagged


if __name__ == "__main__":
    unittest.main()
