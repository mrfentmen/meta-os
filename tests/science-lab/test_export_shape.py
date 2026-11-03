"""CB2-192/193: session export shape and explicit null sections."""
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

import export  # noqa: E402


class TestExportShape(unittest.TestCase):
    def test_all_sections_present(self):
        doc = export.export_session("CYCLE-EXAMPLE-001", write=False)
        for key in export.EXPORT_SECTIONS:
            self.assertIn(key, doc)
        self.assertTrue(doc["claims"])

    def test_optional_data_is_explicit_null(self):
        with tempfile.TemporaryDirectory() as td:
            cycle = {
                "cycle_id": "CYCLE-NULL",
                "phase": "problem",
                "inputs": {},
                "outputs": {},
                "gate_state": "open",
            }
            with open(os.path.join(td, "CYCLE-NULL.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(cycle, fh)
            old = export.CYCLES_DIR
            export.CYCLES_DIR = td
            try:
                doc = export.export_session("CYCLE-NULL", write=False)
            finally:
                export.CYCLES_DIR = old
        self.assertIn("parked_gate", doc)
        self.assertIsNone(doc["parked_gate"])

    def test_review_fields_are_exported(self):
        doc = export.export_session("CYCLE-EXAMPLE-001", write=False)
        for key in export.REVIEW_FIELDS:
            self.assertIn(key, doc)


if __name__ == "__main__":
    unittest.main()
