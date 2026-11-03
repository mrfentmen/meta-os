"""Timestamp normalisation tests (CB2-017..018). Pure; no clock use."""
import os
import sys
import unittest
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402


class TimestampTests(unittest.TestCase):
    def test_z_suffix(self):
        expected = datetime(2026, 11, 2, 10, 0, 0,
                            tzinfo=timezone.utc).timestamp()
        self.assertAlmostEqual(
            crew_common.iso_to_epoch("2026-11-02T10:00:00Z"), expected)

    def test_numeric_offset_is_the_same_instant(self):
        z = crew_common.iso_to_epoch("2026-11-02T10:00:00Z")
        offset = crew_common.iso_to_epoch("2026-11-02T12:00:00+02:00")
        self.assertEqual(z, offset)

    def test_fractional_seconds_are_kept(self):
        whole = crew_common.iso_to_epoch("2026-11-02T10:00:00Z")
        half = crew_common.iso_to_epoch("2026-11-02T10:00:00.500Z")
        self.assertAlmostEqual(half - whole, 0.5)

    def test_naive_timestamp_is_refused(self):
        with self.assertRaises(ValueError):
            crew_common.iso_to_epoch("2026-11-02T10:00:00")

    def test_empty_and_garbage_are_refused(self):
        for value in ("", "   ", "not-a-time"):
            with self.assertRaises(ValueError):
                crew_common.iso_to_epoch(value)


if __name__ == "__main__":
    unittest.main()
