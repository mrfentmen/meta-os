"""DEM-018 (partial): the local audio pre-check covers every asset.

The demo-machine listening check itself is still open (no demo machine
is named, and this VM has no speakers/headphones to listen on), so
these tests pin the pre-check, not a DEM-018 closure: the check script
covers exactly the audio files on disk, runs green, and the eval note
says plainly that DEM-018 remains open.
"""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "intel"))

from dem018_local_check import ASSETS  # noqa: E402

EVAL = "intel/evals/dem018_local.md"


class Dem018LocalTest(unittest.TestCase):
    def test_check_covers_every_audio_asset_on_disk(self):
        on_disk = set()
        for directory in ("demo-assets/audio", "submission-assets/audio"):
            for name in os.listdir(directory):
                if name.endswith(".mp3"):
                    on_disk.add(os.path.join(directory, name))
        self.assertEqual(set(ASSETS), on_disk)

    def test_check_script_runs_green(self):
        result = subprocess.run(
            [sys.executable, "intel/dem018_local_check.py"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:])
        self.assertIn("all local checks PASS", result.stdout)

    def test_eval_note_states_dem018_still_open(self):
        with open(EVAL) as handle:
            text = " ".join(handle.read().split())
        self.assertIn("still OPEN", text)
        self.assertIn("does not close DEM-018", text)


if __name__ == "__main__":
    unittest.main()
