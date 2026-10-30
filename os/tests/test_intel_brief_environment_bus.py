"""intel/brief.py: OS-103 follow-up — environment_bus_record.

Before this change no caller in the repo filled the
environment record's bus part from a messages list: the
OS-103 Bus line rendered only from a hand-stated record.
Now environment_bus_record reads the message count out of
the snapshot's own messages list, with rooms stated by the
caller (snapshot messages carry no room field), and
build_environment_record merges that part in with one
stamp, so a boot brief over a merged record carries the
Bus line. Budget still comes from its own source (no
spend-ledger filler is claimed here), and a record with
only the bus part still renders the other three lines
as not reported.
"""

import sys
import tempfile
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


MESSAGES = [
    {"nick": "rowan", "text": "hello", "ts": 1793093400},
    "milo: working on it",
    {"nick": "pax", "text": "noted", "ts": 1793093401},
    42,
    None,
]


class EnvironmentBusRecordTest(unittest.TestCase):
    def test_count_and_rooms_in_caller_order_duplicates_dropped(self):
        record = brief.environment_bus_record(
            MESSAGES, rooms=["main", "build", "main"],
            now=1793093400)
        self.assertEqual(record["messages"], 3)
        self.assertEqual(record["rooms"], ["main", "build"])
        self.assertEqual(record["as_of"], 1793093400)

    def test_single_room_string_is_wrapped_and_bad_rooms_dropped(self):
        record = brief.environment_bus_record(
            MESSAGES, rooms="main", now=1793093400)
        self.assertEqual(record["rooms"], ["main"])
        record = brief.environment_bus_record(
            MESSAGES, rooms=["main", "", 7, None], now=1793093400)
        self.assertEqual(record["rooms"], ["main"])
        record = brief.environment_bus_record(
            MESSAGES, now=1793093400)
        self.assertEqual(record["rooms"], [])

    def test_non_list_returns_none_so_line_reads_not_reported(self):
        self.assertIsNone(brief.environment_bus_record(None))
        self.assertIsNone(brief.environment_bus_record(
            {"nick": "rowan", "text": "hello"}))
        lines = brief.environment_lines({})
        self.assertIn("not reported", lines[1])

    def test_empty_list_is_zero_messages_not_not_reported(self):
        record = brief.environment_bus_record(
            [], rooms="main", now=1793093400)
        self.assertEqual(record["messages"], 0)
        lines = brief.environment_lines(
            {"bus": record, "as_of": 1793093400})
        self.assertIn("0 messages", lines[1])
        self.assertNotIn("not reported", lines[1])

    def test_builder_record_renders_bus_line_and_others_not_reported(self):
        bus = brief.environment_bus_record(
            MESSAGES, rooms="main", now=1793093400)
        lines = brief.environment_lines(
            {"bus": bus, "as_of": 1793093400})
        self.assertIn("Bus: 3 messages in room main", lines[1])
        self.assertIn("not reported", lines[0])
        self.assertIn("not reported", lines[2])
        self.assertIn("not reported", lines[3])

    def test_merged_record_carries_bus_with_one_stamp(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"messages": MESSAGES, "jobs": []},
                repo_path=path, now=1793093400, room="main")
        self.assertEqual(record["as_of"], 1793093400)
        self.assertEqual(record["bus"]["messages"], 3)
        self.assertEqual(record["bus"]["rooms"], ["main"])
        self.assertEqual(record["bus"]["as_of"], 1793093400)
        self.assertNotIn("repo", record)
        lines = brief.environment_lines(record)
        self.assertIn("Bus: 3 messages in room main", lines[1])
        self.assertIn("not reported", lines[0])
        self.assertIn("not reported", lines[3])

    def test_merged_record_without_messages_leaves_bus_out(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"jobs": []}, repo_path=path, now=1793093400,
                room="main")
        self.assertNotIn("bus", record)
        lines = brief.environment_lines(record)
        self.assertIn("not reported", lines[1])
        self.assertNotIn("0 messages", lines[1])

    def test_boot_template_brief_carries_merged_bus_line(self):
        with tempfile.TemporaryDirectory() as path:
            record = brief.build_environment_record(
                {"messages": MESSAGES, "jobs": []},
                repo_path=path, now=1793093400, room="main")
        text = brief.compose_template_brief(
            {"messages": [], "jobs": [],
             "environment": record}, boot=True)
        self.assertIn("Bus: 3 messages in room main", text)


if __name__ == "__main__":
    unittest.main()
