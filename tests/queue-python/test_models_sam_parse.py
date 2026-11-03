"""SAM parsing tests (CB2-051..053). Offline; no transport."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402

SAM_TEXT = ("<|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|>"
            "<|mask;x=0;y=0;data=355,592,FAKEENCODED|>")


class SamParseTests(unittest.TestCase):
    def test_one_box_maps_to_contract_scale(self):
        rec = models.parse_sam_text(SAM_TEXT)
        self.assertEqual(rec["box_px"],
                         {"x1": 8, "y1": 0, "x2": 599, "y2": 354})
        self.assertEqual(rec["region"],
                         {"x": 13, "y": 0, "w": 985, "h": 753})
        self.assertEqual(rec["mask"]["data"], "355,592,FAKEENCODED")

    def test_box_only_returns_no_mask(self):
        rec = models.parse_sam_text(SAM_TEXT.split("<|mask")[0])
        self.assertIsNone(rec["mask"])

    def test_mask_only_raises(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("<|mask;x=0;y=0;data=abc|>")

    def test_no_box_raises_never_invents(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("no segments here")


if __name__ == "__main__":
    unittest.main()
