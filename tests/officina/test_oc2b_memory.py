"""Tests for Officina stage 2d workshop memory (OC2B-363–365).

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Offline and $0: the store in these tests lives in a temp dir, never
the repo. Append-only is pinned by the 50-entry test: the oldest
entry must still be present.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "officina", "runtime",
    ),
)

from brief import run_rough_words  # noqa: E402
from memory import (  # noqa: E402
    append_entry,
    read_all,
    recall_for_brief,
    record_outcome,
)
from pack_export import check_pack, export_pack  # noqa: E402

WORDS_A = (
    "a heatsink for a toasty little board, about 50mm square, "
    "no fan, keep it compact, under 2 degrees per watt"
)
WORDS_B = (
    "a quiet fanless heatsink for a hot chip, about 50mm square, "
    "keep it small, under 2 degrees per watt"
)


class TestWorkshopMemory(unittest.TestCase):
    def test_append_then_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            record = run_rough_words(WORDS_A)
            check = check_pack(export_pack(record))
            stored = append_entry(
                store, record_outcome(WORDS_A, record, check))
            self.assertEqual(stored["seq"], 1)
            entries = read_all(store)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["entry"]["rough_words"],
                             WORDS_A)
            self.assertEqual(
                entries[0]["entry"]["final_params"],
                record["final_params"])

    def test_two_sequential_briefs_second_reads_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            rec1 = run_rough_words(WORDS_A)
            append_entry(store, record_outcome(
                WORDS_A, rec1, check_pack(export_pack(rec1))))
            rec2 = run_rough_words(WORDS_B)
            append_entry(store, record_outcome(
                WORDS_B, rec2, check_pack(export_pack(rec2))))
            recall = recall_for_brief(store)
            self.assertEqual(recall["total_entries"], 2)
            self.assertEqual(recall["oldest_seq"], 1)
            first = recall["window"][0]["entry"]
            self.assertEqual(first["rough_words"], WORDS_A)
            self.assertIn("final_params", first)

    def test_append_50_oldest_still_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = os.path.join(tmp, "memory.jsonl")
            for i in range(50):
                append_entry(store, {"kind": "probe", "i": i})
            entries = read_all(store)
            self.assertEqual(len(entries), 50)
            self.assertEqual(entries[0]["seq"], 1)
            self.assertEqual(entries[0]["entry"],
                             {"kind": "probe", "i": 0})
            recall = recall_for_brief(store, limit=5)
            self.assertEqual(recall["total_entries"], 50)
            self.assertEqual(recall["oldest_seq"], 1)
            # The full history is still there behind the window.
            self.assertEqual(len(read_all(store)), 50)

    def test_outcome_records_honest_numbers(self):
        record = run_rough_words(WORDS_A)
        check = check_pack(export_pack(record))
        outcome = record_outcome(WORDS_A, record, check)
        self.assertEqual(outcome["proven"], record["proven"])
        self.assertEqual(outcome["final_r_th_c_per_w"],
                         record["final_grade"]["r_th_c_per_w"])
        self.assertEqual(outcome["pack_check_ok"], check["ok"])

    def test_missing_store_reads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                read_all(os.path.join(tmp, "nope.jsonl")), [])


if __name__ == "__main__":
    unittest.main()
