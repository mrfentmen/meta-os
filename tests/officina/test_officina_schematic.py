"""CB2-458 — the schematic dict one real design produces.

The values come from the design's own parameters, so this file asserts the
sections and the arithmetic, not a picture nobody can check.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "os", "worlds", "officina", "runtime"))

from heatsink import HeatsinkParams  # noqa: E402
from schematic import SCHEMATIC_VERSION, schematic, validate_schematic  # noqa: E402

DESIGN = HeatsinkParams(
    fin_height_mm=32.0, fin_thickness_mm=1.5, fin_count=18,
    base_thickness_mm=5.0)


class SchematicTest(unittest.TestCase):
    def test_a_real_design_produces_the_documented_sections(self):
        draw = schematic(DESIGN)

        self.assertEqual(draw["v"], SCHEMATIC_VERSION)
        self.assertEqual(draw["units"], "mm")
        self.assertEqual(sorted(draw), ["base", "fin_count", "fin_root_mm", "fins", "overall", "units", "v"])

        self.assertEqual(draw["overall"]["fin_height_mm"], 32.0)
        self.assertEqual(draw["overall"]["base_mm"], 5.0)
        self.assertEqual(draw["overall"]["height_mm"], 37.0, "base plus fin height")
        self.assertEqual(draw["base"]["fin_count"], 18)
        self.assertEqual(draw["base"]["thickness_mm"], 5.0)

        self.assertEqual(len(draw["fins"]), 18)
        self.assertEqual([f["index"] for f in draw["fins"]], list(range(18)))
        for fin in draw["fins"]:
            self.assertEqual(fin["height_mm"], 32.0)
            self.assertEqual(fin["thickness_mm"], 1.5)
        self.assertEqual(draw["fin_root_mm"], 27.0, "18 fins at 1.5 mm")

        self.assertEqual(validate_schematic(draw), [])

    def test_a_dict_design_gives_the_same_schematic(self):
        self.assertEqual(schematic(DESIGN.as_dict()), schematic(DESIGN))
        self.assertEqual(
            json.loads(json.dumps(schematic(DESIGN))), schematic(DESIGN),
            "the record is JSON-ready")

    def test_bad_designs_and_broken_sections_are_refused(self):
        with self.assertRaises(ValueError):
            schematic(HeatsinkParams(fin_height_mm=30.0, fin_thickness_mm=1.5, fin_count=0, base_thickness_mm=5.0))
        with self.assertRaises(ValueError):
            schematic(HeatsinkParams(fin_height_mm=0.0, fin_thickness_mm=1.5, fin_count=5, base_thickness_mm=5.0))

        draw = schematic(DESIGN)
        self.assertEqual(validate_schematic(None), ["schematic: must be an object"])
        self.assertEqual(
            validate_schematic({"v": 1}),
            ["overall: section missing", "base: section missing", "fins: section missing"])

        broken = json.loads(json.dumps(draw))
        broken["fin_count"] = 3
        self.assertIn("fin_count: does not match the fin list", validate_schematic(broken))

        out_of_order = json.loads(json.dumps(draw))
        out_of_order["fins"][1]["index"] = 0
        self.assertIn("fins[1]: index is out of order", validate_schematic(out_of_order))


if __name__ == "__main__":
    unittest.main()
