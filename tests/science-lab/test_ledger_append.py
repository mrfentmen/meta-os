"""CB2-189/190: ledger append preserves entries and detects tampering."""
import json
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


class TestLedgerAppend(unittest.TestCase):
    def test_two_entries_stay_intact_and_ordered(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "ledger.jsonl")
            ledger.append_record(path, {"kind": "first"})
            ledger.append_record(path, {"kind": "second"})
            rows = ledger.read_all(path)
            self.assertEqual([r["kind"] for r in rows], ["first", "second"])
            self.assertEqual(rows[1]["prev_hash"], rows[0]["entry_hash"])

    def test_tampered_middle_line_detected(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "ledger.jsonl")
            for i in range(3):
                ledger.append_record(path, {"kind": "entry-%d" % i})
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            middle = json.loads(lines[1])
            middle["kind"] = "tampered"
            lines[1] = json.dumps(middle, sort_keys=True) + "\n"
            with open(path, "w", encoding="utf-8") as fh:
                fh.writelines(lines)
            ok, msg = ledger.verify_chain(path)
            self.assertFalse(ok)
            self.assertIn("line 2", msg)


if __name__ == "__main__":
    unittest.main()
