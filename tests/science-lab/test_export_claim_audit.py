"""CB2-200: exported claims must carry a backing record id."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import export  # noqa: E402


class TestClaimAudit(unittest.TestCase):
    def test_five_backed_and_one_unbacked(self):
        claims = [
            {"claim_id": "C%d" % i, "backing_record_id": "EXP-%d" % i}
            for i in range(1, 6)
        ]
        claims.append({"claim_id": "C-BAD", "statement": "no trail"})
        result = export.audit_claim_backing(claims)
        self.assertEqual(result["claims_checked"], 6)
        self.assertEqual(len(result["flagged"]), 1)
        self.assertEqual(result["flagged"][0]["claim_id"], "C-BAD")
        self.assertFalse(result["ok"])

    def test_all_backed_is_clean(self):
        claims = [{"claim_id": "C1", "experiment_id": "EXP-1"}]
        result = export.audit_claim_backing(claims)
        self.assertTrue(result["ok"])
        self.assertEqual(result["flagged"], [])


if __name__ == "__main__":
    unittest.main()
