"""CB2-186/187/188: repository listing order, duplicates, cycle filter."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import repository  # noqa: E402


class TestListing(unittest.TestCase):
    def test_insertion_order(self):
        with tempfile.TemporaryDirectory() as td:
            for i in (1, 2, 3):
                repository.file_claim({"claim_id": "C%d" % i,
                                       "statement": "s%d" % i,
                                       "level": 1}, base=td)
            rows = repository.list_records("claims", base=td)
            self.assertEqual([r["claim_id"] for r in rows],
                             ["C1", "C2", "C3"])

    def test_duplicate_refused(self):
        with tempfile.TemporaryDirectory() as td:
            repository.file_claim({"claim_id": "C1", "statement": "s",
                                   "level": 1}, base=td)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                repository.file_claim({"claim_id": "C1", "statement": "s2",
                                       "level": 2}, base=td)

    def test_filter_by_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            repository.file_claim({"claim_id": "A", "statement": "a",
                                   "level": 1, "cycle_id": "CYC-1"}, base=td)
            repository.file_claim({"claim_id": "B", "statement": "b",
                                   "level": 1, "cycle_id": "CYC-2"}, base=td)
            repository.file_claim({"claim_id": "C", "statement": "c",
                                   "level": 1, "cycle_id": "CYC-1"}, base=td)
            rows = repository.list_records("claims", cycle_id="CYC-1", base=td)
            self.assertEqual([r["claim_id"] for r in rows], ["A", "C"])


if __name__ == "__main__":
    unittest.main()
