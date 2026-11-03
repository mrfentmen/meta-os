"""Append-only JSONL tests (CB2-015..016). Temp dirs; no network."""
import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_records  # noqa: E402


class AppendOnlyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.records = crew_records.CrewRecords(directory=self.tmp)
        self.events = os.path.join(self.tmp, "events.jsonl")

    def test_append_preserves_existing_lines_byte_for_byte(self):
        before = b'{"type": "one"}\n{"type": "two"}\n'
        with open(self.events, "wb") as f:
            f.write(before)
        self.records.append_event({"type": "three"})
        with open(self.events, "rb") as f:
            after = f.read()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(after.splitlines()), 3)
        self.assertEqual(json.loads(after.splitlines()[-1])["type"],
                         "three")

    def test_torn_final_line_is_returned_as_partial(self):
        text = '{"a": 1}\n{"b": 2}\n{"c": '
        records, partial = crew_records.parse_jsonl(text)
        self.assertEqual(records, [{"a": 1}, {"b": 2}])
        self.assertEqual(partial, '{"c":')

    def test_tail_reader_returns_intact_records_and_skips_partial(self):
        with open(self.events, "w") as f:
            f.write('{"type": "one"}\n{"type": "two"}\n{"type": ')
        got = self.records.recent_events(10)
        self.assertEqual([e["type"] for e in got], ["one", "two"])

    def test_partial_is_none_when_every_line_parses(self):
        records, partial = crew_records.parse_jsonl(
            '{"a": 1}\n{"b": 2}\n')
        self.assertEqual(len(records), 2)
        self.assertIsNone(partial)


if __name__ == "__main__":
    unittest.main()
