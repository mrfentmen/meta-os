"""CB2-183/184/185/198: typed repository writes and schema refusal."""
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


def _experiment(**overrides):
    record = {
        "id": "EXP-001",
        "research_question": "Does the fixture reproduce?",
        "hypothesis_id": "H-001",
        "hypothesis_version": "1",
        "original_data": "fixture rows 1-5",
        "data_source": "offline fixture",
        "software": {"name": "science-lab", "version": "1"},
        "model": {"name": "none", "version": "1"},
        "parameters": {"threshold": 1.5},
        "random_seed": 7,
        "input_hash": "a" * 64,
        "output_hash": "b" * 64,
        "execution_logs": ["offline fixture"],
        "verification_status": "reproduced",
        "is_prediction": False,
        "evidence_level": 3,
    }
    record.update(overrides)
    return record


class TestRepositoryRecords(unittest.TestCase):
    def test_valid_experiment_validates_and_reads_back(self):
        with tempfile.TemporaryDirectory() as td:
            filed = repository.write_record("experiments", _experiment(), base=td)
            self.assertEqual(filed["id"], "EXP-001")
            back = repository.get_record("experiments", "EXP-001", base=td)
            self.assertEqual(back, filed)

    def test_failing_schema_names_field(self):
        bad = _experiment()
        bad.pop("input_hash")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                repository.write_record("experiments", bad, base=td)
            self.assertIn("input_hash", str(ctx.exception))

    def test_wrong_schema_type_refused(self):
        claim = {"claim_id": "C-1", "statement": "s", "level": 2}
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError) as ctx:
                repository.write_record("experiments", claim, base=td)
            self.assertIn("id", str(ctx.exception))

    def test_duplicate_id_refused(self):
        with tempfile.TemporaryDirectory() as td:
            repository.write_record("experiments", _experiment(), base=td)
            with self.assertRaisesRegex(ValueError, "duplicate"):
                repository.write_record("experiments", _experiment(), base=td)


if __name__ == "__main__":
    unittest.main()
