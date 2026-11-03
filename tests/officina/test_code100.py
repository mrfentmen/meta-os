"""CB-081..084, CB-088, CB-090 — Officina pure-code checks."""

import json
import os
import sys
import tempfile
import unittest

RUNTIME = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "os", "worlds", "officina", "runtime"))
sys.path.insert(0, RUNTIME)

from heatsink import FIN_HEIGHT_MM, HeatsinkParams, simulate  # noqa: E402
from pack_export import PackExportError, export_pack  # noqa: E402
from memory import AppendOnlyError, WorkshopMemory  # noqa: E402
from prior_art import PriorArtError, validate_note  # noqa: E402
from faber import FaberError, run_order  # noqa: E402


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
    def test_missing_bounds_is_refused_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pack.json")
            with self.assertRaises(PackExportError) as ctx:
                export_pack({"artefact_class": "heatsink-fin-geometry"}, path)
            self.assertIn("bounds", str(ctx.exception))
            self.assertFalse(os.path.exists(path))

    def test_valid_pack_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pack.json")
            export_pack({"artefact_class": "heatsink-fin-geometry",
                         "bounds": {"fin_height_mm_max": 80.0}}, path)
            with open(path) as fh:
                self.assertEqual(json.load(fh)["bounds"]["fin_height_mm_max"], 80.0)


class TestMemory(unittest.TestCase):
    def test_append_is_append_only_and_tamper_names_the_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            mem = WorkshopMemory(os.path.join(tmp, "memory.jsonl"))
            mem.append({"note": "one"})
            mem.append({"note": "two"})
            self.assertTrue(mem.verify()["ok"])
            with self.assertRaises(AppendOnlyError):
                mem.rewrite(1, {"note": "changed"})
            with open(mem.path) as fh:
                lines = fh.read().splitlines()
            first = json.loads(lines[0])
            first["entry"]["note"] = "tampered"
            lines[0] = json.dumps(first, sort_keys=True)
            with open(mem.path, "w") as fh:
                fh.write("\n".join(lines) + "\n")
            broken = WorkshopMemory(mem.path).verify()
            self.assertFalse(broken["ok"])
            self.assertEqual(broken["broken_at"], 1)


class TestPriorArt(unittest.TestCase):
    def test_note_without_sources_is_refused(self):
        with self.assertRaises(PriorArtError) as ctx:
            validate_note({"title": "someone did this before"})
        self.assertIn("sources", str(ctx.exception))

    def test_note_with_sources_passes(self):
        self.assertTrue(validate_note({"title": "paper", "sources": ["doi:10.1/x"]}))


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
