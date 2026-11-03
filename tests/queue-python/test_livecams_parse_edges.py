"""Live camera parse edge tests (CB2-076..077). Offline."""
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import livecams  # noqa: E402


def payload():
    return json.dumps([
        {"id": "cam-a", "name": "A", "area": "Brooklyn",
         "latitude": 40.6, "longitude": -73.9,
         "isOnline": "true", "imageUrl": "https://x/a.jpg"},
        {"id": "cam-b", "name": "B", "area": "Brooklyn",
         "latitude": 40.6, "longitude": -73.9,
         "isOnline": "false", "imageUrl": "https://x/b.jpg"},
        {"id": "cam-c", "name": "C", "area": "Brooklyn",
         "latitude": None, "longitude": -73.9,
         "isOnline": "true", "imageUrl": "https://x/c.jpg"},
        {"id": "cam-d", "name": "D", "area": "Brooklyn",
         "latitude": 40.6, "longitude": -73.9,
         "isOnline": True, "imageUrl": "https://x/d.jpg"},
    ]).encode()


class LiveCamParseTests(unittest.TestCase):
    def test_string_false_is_excluded_and_true_is_included(self):
        cameras, skipped = livecams.parse_cameras_report(payload())
        ids = [c["id"] for c in cameras]
        self.assertEqual(ids, ["cam-a", "cam-d"])
        self.assertEqual(skipped["offline"], 1)

    def test_missing_coordinates_are_skipped_and_counted(self):
        cameras, skipped = livecams.parse_cameras_report(payload())
        self.assertNotIn("cam-c", [c["id"] for c in cameras])
        self.assertEqual(skipped["missing_coordinates"], 1)

    def test_parse_cameras_returns_only_valid_rows(self):
        cameras = livecams.parse_cameras(payload())
        self.assertEqual([c["id"] for c in cameras], ["cam-a", "cam-d"])


if __name__ == "__main__":
    unittest.main()
