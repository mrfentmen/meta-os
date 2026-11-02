"""Section 2 Task 19b: budget guard, status record, shelves, target, worked example."""
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

import literature  # noqa: E402


class TestBudgetGuard(unittest.TestCase):
    def test_caps_stop_with_receipt(self):
        ok, reason = literature.check_source_budget(
            "C-BUDGET", sources_read=1000, calls=1000)
        self.assertFalse(ok)
        self.assertIn("cap", reason.lower() + "budget")

    def test_within_cap_allowed(self):
        ok, _ = literature.check_source_budget("C-OK", 2, 2)
        self.assertTrue(ok)


class TestStatusAndShelves(unittest.TestCase):
    def test_shelves_exist(self):
        for name in ("biology", "chemistry", "physics_math", "materials"):
            p = os.path.join(_LAB, "shelves", name + ".json")
            d = json.load(open(p))
            self.assertTrue(len(d) >= 3)

    def test_status_record_counts(self):
        r = literature.status_record("C1", ["s1", "s2"], ["c1"], ["c2"], ["x"])
        self.assertEqual(r["counts"]["sources_read"], 2)
        self.assertEqual(r["counts"]["claims_dropped"], 1)

    def test_target_qualifies(self):
        t = literature.find_prior_result()
        self.assertIn("qualifies", t)
        self.assertEqual(t["target_id"], "delaney-2004-esol")
        self.assertEqual(t["target_numbers"]["reported_fit_statistics"],
                         "TO_BE_READ_AT_RUN")

    def test_worked_example_honest(self):
        p = os.path.join(_LAB, "records", "examples",
                         "research_intelligence_example.json")
        d = json.load(open(p))
        self.assertEqual(d["answer"]["reported_rmse"], "TO_BE_READ_AT_RUN")
        self.assertTrue(len(d["claims_pinned"]) >= 2)
        self.assertTrue(len(d["claims_dropped"]) >= 1)


if __name__ == "__main__":
    unittest.main()
