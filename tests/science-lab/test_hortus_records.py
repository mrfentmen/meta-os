"""CB2-212/213/225: generation record writing, duplicates, listing."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import records  # noqa: E402


class TestGenerationRecords(unittest.TestCase):
    def test_one_generation_writes_one_record(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "generations.jsonl")
            rec = records.write_generation(path, 1, ["P1", "P2"],
                                           ["C1", "C2"])
            self.assertEqual(rec["parent_ids"], ["P1", "P2"])
            self.assertEqual(rec["child_ids"], ["C1", "C2"])
            self.assertEqual(len(records.load_records(path)), 1)

    def test_duplicate_child_id_refused(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "generations.jsonl")
            records.write_generation(path, 1, ["P1"], ["C1"])
            with self.assertRaisesRegex(ValueError, "duplicate child"):
                records.write_generation(path, 2, ["C1"], ["C1"])

    def test_generation_filter(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "generations.jsonl")
            records.write_generation(path, 1, ["P1"], ["C1"])
            records.write_generation(path, 2, ["C1"], ["C2"])
            records.write_generation(path, 2, ["C1"], ["C3"])
            rows = records.list_generations(path, generation=2)
            self.assertEqual([r["generation"] for r in rows], [2, 2])
            self.assertEqual(sorted(r["child_ids"][0] for r in rows),
                             ["C2", "C3"])


if __name__ == "__main__":
    unittest.main()
