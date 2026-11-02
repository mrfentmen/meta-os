"""Tests for Officina stage 2c blueprint packs (OC2B-353–357).

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Offline and $0: the bounds come live from heatsink.py (the test
pins them against the imported ranges), and every check is
recomputed from the parameters — no stored score is trusted.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "officina", "runtime",
    ),
)

from brief import run_rough_words  # noqa: E402
from heatsink import BASE_THICKNESS_MM, FIN_HEIGHT_MM  # noqa: E402
from pack_export import (  # noqa: E402
    BOUNDS,
    check_pack,
    export_pack,
    read_pack,
    write_pack,
)

WORDS = (
    "a heatsink for a toasty little board, about 50mm square, "
    "no fan, keep it compact, under 2 degrees per watt"
)


class TestEmitter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = run_rough_words(WORDS)
        cls.pack = export_pack(cls.record)

    def test_pack_carries_dimensions_materials_steps(self):
        dims = self.pack["dimensions"]
        for key in ("fin_height_mm", "fin_thickness_mm", "fin_count",
                    "base_thickness_mm", "footprint_mm"):
            self.assertIn(key, dims)
        self.assertTrue(self.pack["materials"])
        self.assertGreaterEqual(len(self.pack["steps"]), 4)
        self.assertEqual(
            [s["n"] for s in self.pack["steps"]],
            sorted(s["n"] for s in self.pack["steps"]),
        )

    def test_bounds_are_the_live_ranges(self):
        self.assertEqual(tuple(self.pack["bounds"]["fin_height_mm"]),
                         tuple(FIN_HEIGHT_MM))
        self.assertEqual(tuple(self.pack["bounds"]["base_thickness_mm"]),
                         tuple(BASE_THICKNESS_MM))
        self.assertIs(BOUNDS["fin_height_mm"], FIN_HEIGHT_MM)
        self.assertIs(BOUNDS["base_thickness_mm"], BASE_THICKNESS_MM)

    def test_unproven_record_exports_unproven(self):
        bad_record = run_rough_words(
            "heatsink to cool a chip under 0.1 degrees per watt, "
            "no fan")
        self.assertFalse(bad_record["proven"])
        pack = export_pack(bad_record)
        self.assertFalse(pack["provenance"]["proven"])

    def test_round_trip_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "pack.json")
            write_pack(self.pack, path)
            reread = read_pack(path)
            self.assertEqual(reread["dimensions"],
                             self.pack["dimensions"])
            self.assertTrue(check_pack(reread)["ok"])


class TestChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = export_pack(run_rough_words(WORDS))

    def test_pack_at_exactly_the_bounds_passes(self):
        at_bounds = json.loads(json.dumps(self.pack))
        at_bounds["dimensions"]["fin_height_mm"] = FIN_HEIGHT_MM[1]
        at_bounds["dimensions"]["base_thickness_mm"] = \
            BASE_THICKNESS_MM[0]
        check = check_pack(at_bounds)
        self.assertTrue(check["ok"], check["violations"])

    def test_pack_1mm_over_fin_height_fails_naming_field(self):
        bad = json.loads(json.dumps(self.pack))
        bad["dimensions"]["fin_height_mm"] = FIN_HEIGHT_MM[1] + 1.0
        check = check_pack(bad)
        self.assertFalse(check["ok"])
        self.assertTrue(any("fin_height_mm" in v
                            for v in check["violations"]),
                        check["violations"])

    def test_base_thickness_below_lower_bound_2mm_fails(self):
        # Direction documented: BASE_THICKNESS_MM is a CLOSED range
        # (2.0, 12.0), so a pack BELOW the 2.0 mm lower bound fails
        # (thin side), while a pack above 12.0 mm fails (thick side).
        thin = json.loads(json.dumps(self.pack))
        thin["dimensions"]["base_thickness_mm"] = \
            BASE_THICKNESS_MM[0] - 0.5
        check = check_pack(thin)
        self.assertFalse(check["ok"])
        self.assertTrue(any("base_thickness_mm" in v
                            for v in check["violations"]),
                        check["violations"])

    def test_checker_rejects_gap_violation(self):
        gap_bad = json.loads(json.dumps(self.pack))
        gap_bad["dimensions"].update(
            {"fin_count": 30, "fin_thickness_mm": 3.0})
        check = check_pack(gap_bad)
        self.assertFalse(check["ok"])
        self.assertTrue(any("gap" in v for v in check["violations"]))


if __name__ == "__main__":
    unittest.main()
