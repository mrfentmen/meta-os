"""DEM-017: the ambient crew audio bed exists, runs ~60 s, and stays very low.

The bed sits under narration in the fallback video, so it must be
quiet by construction: a soft low pad, not a competing track. This test
pins the file the DEM-003 fallback edit consumes (placement into that
edit itself is a later step owned by the edit, as with DEM-015).
"""

import re
import shutil
import subprocess
import unittest

BED = "demo-assets/audio/dem017-ambient-bed.mp3"


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1", path],
        capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    for line in result.stdout.splitlines():
        if line.startswith("duration="):
            return float(line.split("=", 1)[1])
    raise RuntimeError("no duration in ffprobe output")


def mean_volume_db(path):
    result = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-sn", "-dn",
         "-f", "null", "/dev/null"],
        capture_output=True, text=True, timeout=120)
    match = re.search(r"mean_volume:\s*(-?[\d.]+) dB", result.stderr)
    if not match:
        raise RuntimeError("no mean_volume in volumedetect output")
    return float(match.group(1))


class AmbientBedTest(unittest.TestCase):
    def test_bed_exists_and_is_mp3(self):
        with open(BED, "rb") as handle:
            head = handle.read(3)
        self.assertEqual(head, b"ID3")

    def test_bed_duration_near_60_seconds(self):
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe not available")
        duration = probe_duration(BED)
        self.assertGreaterEqual(duration, 55.0, duration)
        self.assertLessEqual(duration, 65.0, duration)

    def test_bed_stays_very_low(self):
        # A bed under narration: mean volume must stay below -30 dB.
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")
        volume = mean_volume_db(BED)
        self.assertLess(volume, -30.0, volume)
