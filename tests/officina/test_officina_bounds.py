"""CB2-451..453 — Officina dimension bounds, through simulate().

The module's validator is `simulate`: it never raises on a bad design,
it returns `feasible=False` with the violation named. These tests pin
the declared ranges and both edges.
"""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds", "officina", "runtime"
    ),
)

from heatsink import (  # noqa: E402
    BASE_THICKNESS_MM,
    FIN_HEIGHT_MM,
    HeatsinkParams,
    simulate,
)


def params(**overrides):
    base = dict(fin_height_mm=20.0, fin_thickness_mm=1.5, fin_count=15, base_thickness_mm=4.0)
    base.update(overrides)
    return HeatsinkParams(**base)


class Bounds(unittest.TestCase):
    def test_declared_ranges(self):
        self.assertEqual(FIN_HEIGHT_MM, (5.0, 80.0))
        self.assertEqual(BASE_THICKNESS_MM, (2.0, 12.0))

    def test_max_fin_height_is_accepted(self):
        result = simulate(params(fin_height_mm=FIN_HEIGHT_MM[1]))
        self.assertTrue(result.feasible, result.violations)

    def test_one_millimetre_over_max_fin_height_is_refused(self):
        result = simulate(params(fin_height_mm=FIN_HEIGHT_MM[1] + 1.0))
        self.assertFalse(result.feasible)
        self.assertTrue(
            any("fin_height_mm outside" in v for v in result.violations), result.violations
        )

    def test_base_thickness_below_minimum_is_refused(self):
        result = simulate(params(base_thickness_mm=BASE_THICKNESS_MM[0] - 0.1))
        self.assertFalse(result.feasible)
        self.assertTrue(
            any("base_thickness_mm outside" in v for v in result.violations), result.violations
        )

    def test_base_thickness_at_minimum_is_accepted(self):
        result = simulate(params(base_thickness_mm=BASE_THICKNESS_MM[0]))
        self.assertTrue(result.feasible, result.violations)

    def test_zero_dimension_is_named_not_divided_by(self):
        result = simulate(params(fin_thickness_mm=0.0))
        self.assertFalse(result.feasible)
        self.assertEqual(result.r_th_c_per_w, float("inf"))
        self.assertTrue(any("must be > 0" in v for v in result.violations), result.violations)


if __name__ == "__main__":
    unittest.main()
