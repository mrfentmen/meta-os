"""tests/test_intel_cursor.py — intel/ingest.py absolute cursor (FND-015).

The JSONL store carries stable ids ("<room>-<seq>"), so a reader that
keeps the returned cursor gets exactly the entries appended since —
no re-reads, no duplicates — even across restarts. The store records
messages this participant sent only, so it never replaces the bus
list read: snapshot() must keep returning bus messages even when a
store file exists for the room.
"""

import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import store  # noqa: E402
from intel import ingest  # noqa: E402


class CursorTest(RelayTestCase):
    def _write_store(self, room, n, nick="pax"):
        """Write n JSONL entries straight to the (patched) store path."""
        path = store.store_path(room)
        with open(path, "w", encoding="utf-8") as f:
            for i in range(1, n + 1):
                f.write(json.dumps({
                    "id": f"{room}-{i}" if room else str(i),
                    "room": room, "nick": nick,
                    "text": f"message {i}", "ts": 1000 + i,
                    "edited": False, "edit_history": [],
                }, sort_keys=True) + "\n")
        return path

    def test_1500_messages_in_order_no_duplicates(self):
        # FND-015 acceptance: 1,500-message fixture, all in order.
        self._write_store("build", 1500)
        messages, cursor = ingest.messages_from_cursor("build")
        self.assertEqual(len(messages), 1500)
        self.assertEqual(messages[0], "pax: message 1")
        self.assertEqual(messages[-1], "pax: message 1500")
        self.assertEqual(len(set(messages)), 1500)
        self.assertEqual(cursor, "build-1500")

    def test_cursor_resume_returns_only_new_entries(self):
        self._write_store("build", 5)
        messages, cursor = ingest.messages_from_cursor("build")
        self.assertEqual(len(messages), 5)
        path = store.store_path("build")
        with open(path, "a", encoding="utf-8") as f:
            for i in (6, 7, 8):
                f.write(json.dumps({
                    "id": f"build-{i}", "room": "build",
                    "nick": "pax", "text": f"message {i}",
                    "ts": 1000 + i, "edited": False,
                    "edit_history": [],
                }, sort_keys=True) + "\n")
        messages2, cursor2 = ingest.messages_from_cursor("build",
                                                         after_id=cursor)
        self.assertEqual(messages2, ["pax: message 6", "pax: message 7",
                                     "pax: message 8"])
        self.assertEqual(cursor2, "build-8")
        # Nothing new: empty list, cursor unchanged.
        messages3, cursor3 = ingest.messages_from_cursor("build",
                                                          after_id=cursor2)
        self.assertEqual(messages3, [])
        self.assertEqual(cursor3, "build-8")

    def test_no_store_file_yields_empty(self):
        messages, cursor = ingest.messages_from_cursor("quiet")
        self.assertEqual(messages, [])
        self.assertIsNone(cursor)
        self.assertEqual(ingest.store_messages("quiet"), [])

    def test_store_messages_renders_bus_shape(self):
        self._write_store("build", 2)
        self.assertEqual(ingest.store_messages("build"),
                         ["pax: message 1", "pax: message 2"])

    def test_snapshot_still_reads_bus_list_with_store_present(self):
        # The store holds sent messages only: it must never shadow
        # the bus list that snapshot() reports for the room.
        self._write_store("build", 3)
        self.fake.bus_push("milo: from the bus",
                           key="muse-bus:room:build")
        self.fake.bus_push("hana: also bus",
                           key="muse-bus:room:build")
        snap = ingest.snapshot("build")
        self.assertEqual(snap["messages"],
                         ["milo: from the bus", "hana: also bus"])

    def test_unknown_cursor_reads_from_start(self):
        self._write_store("build", 2)
        messages, cursor = ingest.messages_from_cursor(
            "build", after_id="build-999")
        self.assertEqual(messages, ["pax: message 1", "pax: message 2"])
        self.assertEqual(cursor, "build-2")
