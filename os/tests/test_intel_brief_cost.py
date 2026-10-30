"""tests/test_intel_brief_cost.py -- BRF-027 brief cost check, pinned.

The scripted run in intel/brief_cost_check.py is the acceptance
artifact; these tests pin it inside the unit harness so a
regression in any row (prompt sizes, call counts, rates,
totals, headroom) fails the suite, not just the standalone
run. The check makes no Spark call, posts nothing, and
touches no network: inputs are measured from repo code over
a hand-written busy snapshot in the BRF-017 shape, prices
are the client's own estimate rates.

What is pinned, and what is not: the dollar totals are a
projection at placeholder rates (the client source labels
its defaults "Planning placeholders for cost estimates
only -- NOT pricing facts"), so the pinned claim is the
headroom shape -- worst single busy brief $0.0170 against
the $75 reserved half, 4415x breakeven -- not a fact about
real Muse pricing. The template actual is $0 because the
run made no Spark call; no spend-ledger entry is written
by the script, because an estimate is not spend. A live
Spark brief's ledger entry, and a re-check on Buffy's busy
fixture, are still owed when they land. GOV-001 (endpoint/
key) stays unnamed and is not unblocked by this check.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import brief, brief_cost_check  # noqa: E402


class BriefCostCheckTest(RelayTestCase):
    def test_check_passes_with_exact_totals(self):
        rows, rate_in, rate_out = brief_cost_check.build_rows()
        text, passed = brief_cost_check.render(rows, rate_in,
                                               rate_out)
        self.assertTrue(passed, text)
        self.assertIn("PASS", text)
        self.assertEqual(rate_in, 3.0)
        self.assertEqual(rate_out, 15.0)
        self.assertEqual(len(rows), 2)
        scored, stress = rows
        self.assertEqual(scored["variant"], "scored 2-word titles")
        self.assertEqual(scored["jobs"], 22)
        self.assertEqual(scored["template_words"], 202)
        self.assertEqual(scored["tokens_in"], 416)
        self.assertEqual(scored["tokens_out_expected"], 266)
        self.assertEqual(scored["cost_expected"], 0.005238)
        self.assertEqual(scored["cost_worst"], 0.016608)
        self.assertEqual(stress["variant"], "long-title stress")
        self.assertEqual(stress["jobs"], 22)
        self.assertEqual(stress["template_words"], 218)
        self.assertEqual(stress["tokens_in"], 542)
        self.assertEqual(stress["tokens_out_expected"], 298)
        self.assertEqual(stress["cost_expected"], 0.006096)
        self.assertEqual(stress["cost_worst"], 0.016986)
        for row in rows:
            self.assertEqual(row["template_actual_usd"], 0.0)
            self.assertLess(row["cost_worst"], 75.0)
            self.assertLess(row["cost_worst"], 150.0)
            self.assertLessEqual(row["template_words"], 220)
        self.assertIn("4415x", text)

    def test_script_main_passes(self):
        summary, code = brief_cost_check.main()
        self.assertEqual(code, 0)
        self.assertTrue(summary["passed"])

    def test_template_brief_record_carries_null_spend(self):
        snapshot = brief_cost_check.busy_snapshot()
        text, record = brief.generate_brief(
            snapshot, "build", kind="morning", dry_run=True)
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertEqual(record["model"], "template")
        self.assertIsNone(record["spend_id"])
        self.assertEqual(record["kind"], "morning")


if __name__ == "__main__":
    unittest.main()
