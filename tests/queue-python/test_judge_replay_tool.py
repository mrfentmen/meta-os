"""Judge replay tool tests (CB2-050). Offline; temp file only."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge_replay  # noqa: E402

ROWS = [
    {"division": "vigiles", "first_category": "person down",
     "review_category": "person down", "review_ok": True},
    {"division": "vigiles", "first_category": "person down",
     "review_category": "normal activity", "review_ok": True},
    {"division": "ignis", "first_category": "visible flame",
     "review_category": None, "review_ok": False},
]


class ReplayToolTests(unittest.TestCase):
    def test_counts_by_outcome_only(self):
        counts = judge_replay.replay_counts(ROWS)
        self.assertEqual(counts, {"confirmed": 1, "cleared": 1,
                                  "inconclusive": 1})

    def test_lines_skip_blanks_and_parse(self):
        text = "\n".join(json.dumps(row) for row in ROWS) + "\n\n"
        self.assertEqual(judge_replay.replay_lines(text),
                         {"confirmed": 1, "cleared": 1,
                          "inconclusive": 1})

    def test_cli_prints_counts_json(self):
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl",
                                         delete=False) as handle:
            for row in ROWS:
                handle.write(json.dumps(row) + "\n")
            path = handle.name
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = judge_replay.main([path])
        finally:
            os.unlink(path)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue()),
                         {"confirmed": 1, "cleared": 1,
                          "inconclusive": 1})


if __name__ == "__main__":
    unittest.main()
