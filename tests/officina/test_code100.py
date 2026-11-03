"""CB-081..084, CB-088, CB-090 — Officina pure-code checks, ported to main.

Pax removed the first version of this file because it imported classes that
never landed on main (WorkshopMemory, AppendOnlyError, PackExportError,
PriorArtError). This one is written against what main actually ships:

  memory.py       module functions; append-only with no rewrite API at all
  pack_export.py  export_pack(record) -> dict, write_pack / read_pack
  prior_art.py    validate_note raises ValueError, not a custom class
  heatsink.py     the same simulator and the same live ranges
  faber.py        FaberError + run_order

No model, no network, no build step.
"""

import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNTIME = os.path.join(REPO, "os", "worlds", "officina", "runtime")
sys.path.insert(0, RUNTIME)

import memory as workshop_memory  # noqa: E402
from heatsink import FIN_HEIGHT_MM, HeatsinkParams, simulate  # noqa: E402
from pack_export import BOUNDS, export_pack, read_pack, write_pack  # noqa: E402
from prior_art import validate_note  # noqa: E402
from faber import FaberError, run_order  # noqa: E402


def a_record(**over):
    rec = {
        "rough_input": "keep a small amplifier cool",
        "brief": {"artefact_class": "heatsink-fin-geometry"},
        "final_params": {
            "fin_height_mm": 40.0,
            "fin_thickness_mm": 1.5,
            "fin_count": 12,
            "base_thickness_mm": 6.0,
        },
        "final_grade": {"r_th_c_per_w": 0.42},
        "verification": {"proven": True},
        "proven": True,
        "status": "proven",
        "rounds_used": 3,
    }
    rec.update(over)
    return rec


class TestBounds(unittest.TestCase):
    def test_exact_max_height_passes_and_one_mm_over_fails(self):
        top = HeatsinkParams(FIN_HEIGHT_MM[1], 0.5, 4, 2.0)
        self.assertTrue(simulate(top).feasible, simulate(top).violations)
        over = HeatsinkParams(FIN_HEIGHT_MM[1] + 1.0, 0.5, 4, 2.0)
        result = simulate(over)
        self.assertFalse(result.feasible)
        self.assertTrue(any("fin_height_mm" in v for v in result.violations))

    def test_zero_and_negative_dimensions_are_named(self):
        cases = {
            "fin_height_mm": HeatsinkParams(0.0, 1.0, 10, 3.0),
            "fin_thickness_mm": HeatsinkParams(20.0, 0.0, 10, 3.0),
            "fin_count": HeatsinkParams(20.0, 1.0, 0, 3.0),
            "base_thickness_mm": HeatsinkParams(20.0, 1.0, 10, 0.0),
            "negative_height": HeatsinkParams(-5.0, 1.0, 10, 3.0),
        }
        for name, params in cases.items():
            result = simulate(params)
            self.assertFalse(result.feasible, name)
            field = name.replace("negative_", "")
            self.assertTrue(any(field in v for v in result.violations), (name, result.violations))


class TestPackExport(unittest.TestCase):
    def test_export_carries_live_bounds_not_copies(self):
        pack = export_pack(a_record())
        self.assertEqual(pack["stage"], "2c-blueprint-pack")
        self.assertEqual(pack["dimensions"]["fin_count"], 12)
        # the bounds in a pack ARE the simulator's ranges, so they cannot drift
        self.assertEqual(pack["bounds"]["fin_height_mm"], list(FIN_HEIGHT_MM))
        self.assertEqual(pack["bounds"]["fin_height_mm"], list(BOUNDS["fin_height_mm"]))

    def test_pack_round_trips_through_disk(self):
        pack = export_pack(a_record())
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pack.json")
            write_pack(pack, path)
            again = read_pack(path)
        self.assertEqual(again["dimensions"], pack["dimensions"])
        self.assertEqual(again["steps"], pack["steps"])

    def test_a_record_without_final_params_is_refused(self):
        rec = a_record()
        del rec["final_params"]
        with self.assertRaises(ValueError) as ctx:
            export_pack(rec)
        self.assertIn("final_params", str(ctx.exception))


class TestMemory(unittest.TestCase):
    def test_append_is_append_only_and_there_is_no_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            workshop_memory.append_entry(store, {"note": "one"})
            workshop_memory.append_entry(store, {"note": "two"})
            entries = workshop_memory.read_all(store)
            self.assertEqual([e["seq"] for e in entries], [1, 2])
            self.assertEqual(entries[0]["entry"]["note"], "one")
            # the point of append-only: the API to rewrite history does not exist
            self.assertFalse(hasattr(workshop_memory, "rewrite"))
            self.assertFalse(hasattr(workshop_memory, "WorkshopMemory"))

    def test_a_corrupt_line_is_reported_with_its_number(self):
        # main has no hash chain, so this is corruption reporting, not tamper
        # detection: a broken line names itself instead of vanishing.
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            workshop_memory.append_entry(store, {"note": "one"})
            with open(store, "a", encoding="utf-8") as fh:
                fh.write("{not json}\n")
            with self.assertRaises(ValueError) as ctx:
                workshop_memory.read_all(store)
            self.assertIn("line 2", str(ctx.exception))

    def test_recall_reports_the_tail_and_the_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            for i in range(3):
                workshop_memory.append_entry(store, {"n": i})
            recall = workshop_memory.recall_for_brief(store, limit=2)
        self.assertEqual(recall["total_entries"], 3)
        self.assertEqual(recall["oldest_seq"], 1)
        self.assertEqual(len(recall["window"]), 2)


class TestPriorArt(unittest.TestCase):
    def test_note_without_sources_is_refused_by_name(self):
        with self.assertRaises(ValueError) as ctx:
            validate_note({"title": "someone did this before"})
        self.assertIn("sources", str(ctx.exception))

    def test_note_with_sources_passes(self):
        self.assertTrue(validate_note({"title": "paper", "sources": ["doi:10.1/x"]}))

    def test_a_claim_without_sources_is_refused_by_index(self):
        note = {"sources": ["doi:10.1/x"], "claims": [{"text": "a"}, {"text": "b", "sources": ["x"]}]}
        with self.assertRaises(ValueError) as ctx:
            validate_note(note)
        self.assertIn("claim 0", str(ctx.exception))


class TestFaber(unittest.TestCase):
    def test_unknown_material_is_refused_before_any_stage(self):
        ran = []
        with self.assertRaises(FaberError):
            run_order({"material": "unobtainium"}, [lambda order: ran.append(order)])
        self.assertEqual(ran, [])

    def test_known_material_runs_stages(self):
        ran = []
        out = run_order({"material": "aluminium"}, [lambda order: ran.append(order) or "ok"])
        self.assertEqual(out, ["ok"])
        self.assertEqual(len(ran), 1)


if __name__ == "__main__":
    unittest.main()
