"""DEM-014: the provisional narration final mix exists and runs ~68.5 s.

The mix combines the provisional picked takes (take 1 of the WDG-031
opening framing and take 1 of the WDG-030 watchdog segment, both Helio)
with a 0.5 s silence gap. Dale's rehearsal pick is still open and the
DEM-003 fallback video is not landed, so the tests pin the mix file the
edit will consume, not a final synced cut.
"""

import shutil
import subprocess
import unittest

MIX = "demo-assets/audio/dem014-final-mix.mp3"


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


class FinalMixTest(unittest.TestCase):
    def test_mix_exists_and_is_mp3(self):
        with open(MIX, "rb") as handle:
            head = handle.read(3)
        self.assertEqual(head, b"ID3")

    def test_mix_duration_is_opening_plus_gap_plus_watchdog(self):
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe not available")
        duration = probe_duration(MIX)
        # 19.92 s opening + 0.5 s gap + 48.07 s watchdog = 68.49 s.
        self.assertAlmostEqual(duration, 68.49, delta=2.0)

    def test_mix_decodes_clean(self):
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", MIX, "-f", "null", "-"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr[:300])


if __name__ == "__main__":
    unittest.main()
