"""Combined parse -> verdict -> index pipeline (CB2-450)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import bootlog_parse  # noqa: E402
import bootlog_verdict  # noqa: E402
import proof_index  # noqa: E402

GOOD = """\
META OS 0.1 (K6)
META OS KERNEL - alive (K1)
Programs: hello sleeper crasher (ring 3)
INT user page-fault addr 0x0 err 0x4: task killed
"""

BAD = GOOD + "META OS KERNEL - panic\n"


class BootlogPipeline(unittest.TestCase):
    def test_three_logs_parse_verdict_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a-good.txt").write_text(GOOD, encoding="utf-8")
            (directory / "b-bad.txt").write_text(BAD, encoding="utf-8")
            (directory / "c-good.txt").write_text(GOOD, encoding="utf-8")
            (directory / "notes.md").write_text("skip\n", encoding="utf-8")

            index = proof_index.scan_dir(directory)
            self.assertEqual(len(index["rows"]), 3)
            self.assertEqual(index["skipped"], 1)

            verdicts = {}
            for name in ("a-good.txt", "b-bad.txt", "c-good.txt"):
                parsed = bootlog_parse.parse_log((directory / name).read_text(encoding="utf-8"))
                verdicts[name] = bootlog_verdict.evaluate(parsed)

            self.assertTrue(verdicts["a-good.txt"]["all_green"])
            self.assertTrue(verdicts["c-good.txt"]["all_green"])
            self.assertFalse(verdicts["b-bad.txt"]["all_green"])
            self.assertEqual(
                bootlog_verdict.changed_checks(verdicts["a-good.txt"], verdicts["b-bad.txt"]),
                ["panic_zero"],
            )
            self.assertIn("3 log(s), 1 non-log file(s) skipped", proof_index.render(index))


if __name__ == "__main__":
    unittest.main()
