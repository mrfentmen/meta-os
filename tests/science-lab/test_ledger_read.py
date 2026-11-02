"""CB2-191/199: ledger blank lines ignored; strict entries need timestamps."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import ledger  # noqa: E402


class TestLedgerRead(unittest.TestCase):
    def test_trailing_blank_line_is_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "ledger.jsonl")
            ledger.append_record(path, {"kind": "a"})
            ledger.append_record(path, {"kind": "b"})
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\n\n")
            rows = ledger.read_all(path)
            self.assertEqual(len(rows), 2)
            self.assertEqual([r["kind"] for r in rows], ["a", "b"])

    def test_strict_write_refuses_missing_timestamp(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "ledger.jsonl")
            with self.assertRaisesRegex(ValueError, "recorded_at"):
                ledger.append_record(path, {"kind": "no-time"},
                                     require_timestamp=True)
            self.assertEqual(ledger.read_all(path), [])


if __name__ == "__main__":
    unittest.main()
