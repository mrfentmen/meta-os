"""SAM bounds tests (CB2-054..055). Offline; pure parser."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


def box(x1, y1, x2, y2, w=1000, h=1000):
    return (f"<|box;x1={x1};y1={y1};x2={x2};y2={y2};"
            f"w={w};h={h}|>")


class SamBoundsTests(unittest.TestCase):
    def test_exact_zero_and_full_scale_are_accepted(self):
        rec = models.parse_sam_text(box(0, 0, 1000, 1000))
        self.assertEqual(rec["region"],
                         {"x": 0, "y": 0, "w": 1000, "h": 1000})

    def test_1001_is_rejected(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text(box(0, 0, 1001, 1000))

    def test_inverted_box_is_rejected(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text(box(900, 900, 100, 100))


if __name__ == "__main__":
    unittest.main()
