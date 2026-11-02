"""CB2-180: failure drill marks a mismatched success claim as not real."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import verify  # noqa: E402


class TestFailureDrill(unittest.TestCase):
    def test_claimed_success_with_mismatched_numbers_is_false(self):
        result = verify.failure_drill(
            {"success": True, "numbers": [0.818, 1.25]},
            {"numbers": [1.902, 1.25]},
        )
        self.assertTrue(result["claimed_success"])
        self.assertFalse(result["numbers_match"])
        self.assertFalse(result["fake_success"])
        self.assertFalse(result["accepted"])
        self.assertEqual(result["verdict"], "mismatch")

    def test_matching_numbers_stand(self):
        result = verify.failure_drill(
            {"success": True, "numbers": [0.818, 1.25]},
            {"numbers": [0.818, 1.25]},
        )
        self.assertTrue(result["numbers_match"])
        self.assertTrue(result["fake_success"])
        self.assertTrue(result["accepted"])

    def test_missing_numbers_refused(self):
        with self.assertRaises(ValueError):
            verify.failure_drill({"success": True}, {"numbers": [1.0]})


if __name__ == "__main__":
    unittest.main()
