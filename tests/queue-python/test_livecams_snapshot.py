"""Live camera snapshot tests (CB2-080). Offline; fetch stub."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import livecams  # noqa: E402

CAM = {"id": "a", "name": "A", "imageUrl": "https://x/a.jpg"}


class SnapshotTests(unittest.TestCase):
    def test_jpeg_and_png_are_accepted(self):
        for data in (b"\xff\xd8\xffrest", b"\x89PNG\r\n\x1a\nrest"):
            self.assertEqual(
                livecams.fetch_snapshot(CAM, fetch=lambda url: data), data)

    def test_non_image_is_refused(self):
        with self.assertRaises(livecams.LiveCamError):
            livecams.fetch_snapshot(
                CAM, fetch=lambda url: b"<html>error page</html>")


if __name__ == "__main__":
    unittest.main()
