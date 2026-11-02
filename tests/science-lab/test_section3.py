"""Section 3 Task 29: falsifier rejection, prereg order, critique gate."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import reasoning  # noqa: E402
import reasoning_chain as rc  # noqa: E402
import ledger  # noqa: E402


class TestReasoning(unittest.TestCase):
    def test_falsifierless_rejected(self):
        with self.assertRaises(ValueError):
            reasoning.new_hypothesis("H1", "q?", "p", "m", "a", "", [], "x")
        hyps, rej = reasoning.generate_hypotheses(
            {"question": "q?", "claims": [{"id": "c1", "text": "x"}],
             "sources": []}, n=3)
        self.assertTrue(len(hyps) >= 3)

    def test_prereg_precedes_result(self):
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "L.jsonl")
            e = reasoning.preregister("H9", "R2>=0.5", 0.5, "full set", lp)
            self.assertIn("entry_hash", e)
            # late prereg after result refused
            ledger.append_record(lp, {"kind": "experiment-result",
                                      "hypothesis_id": "H9"})
            with self.assertRaises(ValueError):
                reasoning.preregister("H9", "t", 1, "s", lp)

    def test_missing_critique_blocks_gate(self):
        chain = rc.build_chain({"id": "b"}, [{"id": "H1"}], [{"step": 1}],
                               "prereghash123", None)
        ok, msg = rc.gate_to_computational(chain)
        self.assertFalse(ok)
        self.assertIn("critique", msg.lower())

    def test_example_honest(self):
        import json
        d = json.load(open(os.path.join(
            _LAB, "records", "examples", "reasoning_example.json")))
        self.assertFalse(d["gate"]["allowed"])
        self.assertIn("TO_BE_READ_AT_RUN", json.dumps(d))


if __name__ == "__main__":
    unittest.main()
