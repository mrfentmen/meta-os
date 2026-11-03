"""Live camera round-robin tests (CB2-081..082). Offline."""
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import livecams  # noqa: E402

PAYLOAD = json.dumps([
    {"id": f"cam-{name}", "name": name, "area": "Brooklyn",
     "latitude": 40.6, "longitude": -73.9, "isOnline": "true",
     "imageUrl": f"https://x/{name}.jpg"} for name in "ABC"
]).encode()
JPEG = b"\xff\xd8\xffframe"


class RoundRobinTests(unittest.TestCase):
    def _source(self, failing=()):
        def fetch(url):
            if url == livecams.API_URL:
                return PAYLOAD
            if any(name in url for name in failing):
                raise OSError("offline")
            return JPEG
        counter = iter(range(1000))
        return livecams.LiveCamSource(
            fetch=fetch, now=lambda: f"t{next(counter)}")

    def test_three_cameras_cycle_in_order_and_wrap(self):
        source = self._source()
        names = [source.frame()[0]["id"] for _ in range(4)]
        self.assertEqual(names, ["cam-A", "cam-B", "cam-C", "cam-A"])

    def test_camera_that_goes_offline_is_skipped(self):
        source = self._source(failing=("B",))
        first = source.frame()[0]["id"]
        second = source.frame()[0]["id"]
        self.assertEqual(first, "cam-A")
        self.assertEqual(second, "cam-C")


if __name__ == "__main__":
    unittest.main()
