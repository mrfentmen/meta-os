"""tests/test_intel_cost.py -- INT-007 cost check, pinned.

The scripted run in intel/cost_check.py is the acceptance
artifact; these tests pin it inside the unit harness so a
regression in any row (prompt sizes, call counts, rates,
totals, headroom) fails the suite, not just the standalone
run. The check makes no Spark call, posts nothing, and
touches no network: inputs are measured from repo files
and code, prices are the client's own estimate rates.

What is pinned, and what is not: the dollar totals are a
projection at placeholder rates (the client source labels
its defaults "Planning placeholders for cost estimates
only -- NOT pricing facts"), so the pinned claim is the
headroom shape -- worst case with boot brief $0.1440
against the $75 reserved half, 520x breakeven -- not a
fact about real Muse pricing. GOV-001 (endpoint/key)
stays unnamed and is not unblocked by this check.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import cost_check  # noqa: E402


class CostCheckTest(RelayTestCase):
    def test_check_passes_with_exact_totals(self):
        rows, rate_in, rate_out, _sources = cost_check.build_rows()
        summary = cost_check.totals(rows)
        self.assertTrue(summary["passed"], summary)
        self.assertEqual(rate_in, 3.0)
        self.assertEqual(rate_out, 15.0)
        self.assertEqual(summary["expected_usd"], 0.021258)
        self.assertEqual(summary["worst_usd"], 0.12789)
        self.assertEqual(summary["worst_with_boot_usd"], 0.143982)
        self.assertEqual(summary["headroom_vs_reserved_usd"], 74.856018)
        self.assertEqual(
            summary["breakeven_multiplier_vs_reserved"], 520)
        self.assertEqual(len(rows), 5)
        self.assertEqual(sum(row["count_base"] for row in rows), 5)
        self.assertEqual(sum(row["count_worst"] for row in rows), 8)

    def test_check_twice_identical(self):
        first, _a, _b, _c = cost_check.build_rows()
        second, _d, _e, _f = cost_check.build_rows()
        self.assertEqual(cost_check.totals(first),
                         cost_check.totals(second))
        self.assertEqual(
            [(row["call"], row["tokens_in"],
              row["tokens_out_expected"]) for row in first],
            [(row["call"], row["tokens_in"],
              row["tokens_out_expected"]) for row in second])

    def test_table_renders_rows_budgets_and_headroom(self):
        rows, rate_in, rate_out, sources = cost_check.build_rows()
        summary = cost_check.totals(rows)
        table = cost_check.render(rows, summary, rate_in, rate_out,
                                  sources)
        for name in ("morning brief (Shot 2)",
                     "dispatch plan (Shot 5)",
                     "closing brief (Shot 11)",
                     "alert polish (Shots 8/8b)",
                     "boot brief (Shot 0, OS-004 go only)"):
            self.assertIn(name, table)
        self.assertIn("$0.1440", table)
        self.assertIn("$74.8560", table)
        self.assertIn("520x", table)
        self.assertIn("NOT pricing facts", table)
        self.assertIn("PASS", table)


if __name__ == "__main__":
    unittest.main()
