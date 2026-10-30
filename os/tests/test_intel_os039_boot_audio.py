"""OS-039: the boot sting + voice line exist, are short, and mix without clipping.

The sting must sit under narration, not compete with it, so its peak is
pinned below the voice line's peak. Placement into the DEM-003 fallback cut
is a later step (that cut is Pax's task, not landed); these tests pin the
assets the cut will consume, as with DEM-015/DEM-017.
"""

import re
import shutil
import subprocess
import unittest

STING = "submission-assets/audio/os039-boot-sting.mp3"
VOICE = "submission-assets/audio/os039-boot-voice-line.mp3"


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


def max_volume_db(path):
    result = subprocess.run(
        ["ffmpeg", "-i", path, "-af", "volumedetect", "-vn", "-sn", "-dn",
         "-f", "null", "/dev/null"],
        capture_output=True, text=True, timeout=120)
    match = re.search(r"max_volume:\s*(-?[\d.]+) dB", result.stderr)
    if not match:
        raise RuntimeError("no max_volume in volumedetect output")
    return float(match.group(1))


class BootAudioTest(unittest.TestCase):
    def test_files_exist_and_are_mp3(self):
        for path in (STING, VOICE):
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(3), b"ID3", path)

    def test_sting_is_short(self):
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe not available")
        duration = probe_duration(STING)
        self.assertGreaterEqual(duration, 1.5, duration)
        self.assertLessEqual(duration, 2.5, duration)

    def test_voice_line_is_one_short_line(self):
        if shutil.which("ffprobe") is None:
            self.skipTest("ffprobe not available")
        duration = probe_duration(VOICE)
        self.assertLess(duration, 10.0, duration)

    def test_sting_peak_below_voice_peak(self):
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")
        self.assertLess(max_volume_db(STING), max_volume_db(VOICE))

    def test_neither_file_clips(self):
        if shutil.which("ffmpeg") is None:
            self.skipTest("ffmpeg not available")
        for path in (STING, VOICE):
            self.assertLess(max_volume_db(path), 0.0, path)


if __name__ == "__main__":
    unittest.main()
