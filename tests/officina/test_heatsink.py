"""Pinning tests for the Officina heatsink simulator.

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Everything here is offline and $0: pure math, no model calls, no
network, no bus. The golden value pins the simulator against
regression; the independent recomputation in
test_golden_value_matches_hand_arithmetic re-derives the same
number from the documented formulas, so a formula change fails
loudly instead of drifting silently.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "officina", "runtime",
    ),
)

from heatsink import (  # noqa: E402
    Conditions,
    HeatsinkParams,
    fin_efficiency,
    simulate,
)


class TestFinEfficiency(unittest.TestCase):
    def test_zero_height_is_perfect(self):
        self.assertEqual(fin_efficiency(5.0, 0.0), 1.0)

    def test_unit_mh_matches_tanh(self):
        self.assertAlmostEqual(
            fin_efficiency(1.0, 1.0), math.tanh(1.0), places=12
        )

    def test_efficiency_falls_with_height(self):
        self.assertGreater(fin_efficiency(10.0, 0.005),
                           fin_efficiency(10.0, 0.04))

    def test_efficiency_stays_in_unit_interval(self):
        for mh in (0.01, 0.2, 1.0, 5.0):
            eta = fin_efficiency(1.0, mh)
            self.assertGreater(eta, 0.0)
            self.assertLessEqual(eta, 1.0)


class TestGoldenValue(unittest.TestCase):
    GOLDEN = HeatsinkParams(40.0, 1.0, 20, 3.0)
    GOLDEN_R = 1.2889610642

    def test_golden_value(self):
        result = simulate(self.GOLDEN)
        self.assertTrue(result.feasible)
        self.assertAlmostEqual(result.r_th_c_per_w, self.GOLDEN_R, places=6)

    def test_golden_value_matches_hand_arithmetic(self):
        # Independent re-derivation from the documented formulas.
        h, k, dt = 10.0, 205.0, 55.0
        t, height, n = 0.001, 0.04, 20
        length, width = 0.05, 0.05
        m = math.sqrt(2.0 * h / (k * t))
        eta = math.tanh(m * height) / (m * height)
        q = n * eta * h * (2.0 * height * length) * dt
        q += h * (width * length - n * t * length) * dt
        self.assertAlmostEqual(
            simulate(self.GOLDEN).r_th_c_per_w, dt / q, places=9
        )

    def test_determinism(self):
        self.assertEqual(
            simulate(self.GOLDEN).r_th_c_per_w,
            simulate(self.GOLDEN).r_th_c_per_w,
        )


class TestMonotonicityAndConstraints(unittest.TestCase):
    def test_taller_fins_cool_better(self):
        short = simulate(HeatsinkParams(5.0, 1.0, 10, 3.0))
        tall = simulate(HeatsinkParams(40.0, 1.0, 10, 3.0))
        self.assertTrue(short.feasible)
        self.assertTrue(tall.feasible)
        self.assertLess(tall.r_th_c_per_w, short.r_th_c_per_w)

    def test_gap_violation_is_a_named_failure(self):
        result = simulate(HeatsinkParams(20.0, 3.0, 30, 3.0))
        self.assertFalse(result.feasible)
        self.assertTrue(any("gap" in v for v in result.violations))
        # The score is still computed for the failure ledger.
        self.assertTrue(math.isfinite(result.r_th_c_per_w))

    def test_volume_violation_is_a_named_failure(self):
        result = simulate(HeatsinkParams(40.0, 3.0, 30, 8.0))
        self.assertFalse(result.feasible)
        self.assertTrue(any("volume" in v for v in result.violations))

    def test_range_violation_is_a_named_failure(self):
        result = simulate(HeatsinkParams(40.0, 0.4, 10, 3.0))
        self.assertFalse(result.feasible)
        self.assertTrue(any("thickness" in v for v in result.violations))

    def test_bad_conditions_raise(self):
        with self.assertRaises(ValueError):
            simulate(
                HeatsinkParams(40.0, 1.0, 20, 3.0),
                Conditions(h_w_m2k=0.0),
            )


if __name__ == "__main__":
    unittest.main()
