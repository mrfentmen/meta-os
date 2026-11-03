"""CB2-210/211: verifier names violations and passes a valid child."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import model, verifier  # noqa: E402


class TestVerifier(unittest.TestCase):
    def test_invalid_child_flags_named_constraint(self):
        result = verifier.verify_child({"genome": (40.0, 60.0, 4.0, 8.0)})
        self.assertFalse(result["passed"])
        self.assertIn("min_spacing_m", result["violation_names"])
        for violation in result["violations"]:
            self.assertIn("constraint", violation)
            self.assertIn("actual", violation)
            self.assertIn("limit", violation)

    def test_valid_child_passes(self):
        result = verifier.verify_child(model.REFERENCE_GENOME)
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["violation_names"], [])


if __name__ == "__main__":
    unittest.main()
