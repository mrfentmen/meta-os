"""Live camera pick tests (CB2-078..079). Offline; pure."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import livecams  # noqa: E402

CAMS = [
    {"id": "b", "name": "B", "area": "Brooklyn", "isOnline": "true"},
    {"id": "a", "name": "A", "area": "Brooklyn", "isOnline": "true"},
    {"id": "c", "name": "C", "area": "Queens", "isOnline": "true"},
    {"id": "d", "name": "D", "area": "Brooklyn", "isOnline": "false"},
]


class PickTests(unittest.TestCase):
    def test_same_list_and_area_pick_same_camera(self):
        first = livecams.pick(CAMS, area="Brooklyn")
        second = livecams.pick(CAMS, area="Brooklyn")
        self.assertEqual(first, second)
        self.assertEqual(first[0]["id"], "a")

    def test_offline_cameras_are_dropped(self):
        picked = livecams.pick(CAMS, area="Brooklyn", count=10)
        self.assertNotIn("d", [c["id"] for c in picked])

    def test_area_with_no_online_camera_returns_empty(self):
        self.assertEqual(livecams.pick(CAMS, area="Bronx"), [])


if __name__ == "__main__":
    unittest.main()
