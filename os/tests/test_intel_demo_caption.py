"""DEM-015: the watchdog-moment caption voiceover clip exists and runs ~15s.

The clip narrates what the viewer is seeing at the DEM-011 silent-failure
moment (a worker claimed a job, posted once, then went silent; the
watchdog fired one red stall alert) for the fallback video. It is
synthesized in Helio, the same voice as the WDG-030/WDG-031 take-1 clips
and the WDG-033 fallback track, so it cuts against them without a voice
change. Placement into the DEM-003 fallback video edit itself is a later
step owned by that edit; this test pins the clip the edit consumes.
"""

import shutil
import subprocess
import unittest


CLIP = "demo-assets/audio/dem015-caption-watchdog-moment.mp3"


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


class CaptionVoiceoverTest(unittest.TestCase):
    def test_clip_exists_and_is_mp3(self):
        with open(CLIP, "rb") as handle:
            head = handle.read(3)
        self.assertEqual(head, b"ID3")

    def test_clip_duration_near_15_seconds(self):
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe not available")
        duration = probe_duration(CLIP)
        self.assertGreaterEqual(duration, 12.0, duration)
        self.assertLessEqual(duration, 18.0, duration)
