"""CB2-471..472 — the Officina spec validator."""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "os", "worlds", "officina"),
)

from spec_validate import validate_spec  # noqa: E402

VALID = {
    "fin_height_mm": 20.0,
    "fin_thickness_mm": 1.5,
    "fin_count": 15,
    "base_thickness_mm": 4.0,
}


class SpecValidate(unittest.TestCase):
    def test_valid_spec_has_no_errors(self):
        self.assertEqual(validate_spec(VALID), [])

    def test_non_numeric_dimension_is_named(self):
        errors = validate_spec(dict(VALID, fin_thickness_mm="thick"))
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("fin_thickness_mm:"), errors)
        self.assertIn("number", errors[0])

    def test_missing_field_is_named(self):
        broken = dict(VALID)
        del broken["base_thickness_mm"]
        self.assertEqual(validate_spec(broken), ["base_thickness_mm: missing"])

    def test_out_of_bounds_is_named(self):
        errors = validate_spec(dict(VALID, fin_height_mm=90.0))
        self.assertEqual(len(errors), 1)
        self.assertIn("outside", errors[0])

    def test_bool_is_not_a_number(self):
        errors = validate_spec(dict(VALID, fin_count=True))
        self.assertTrue(any("fin_count" in e and "number" in e for e in errors), errors)

    def test_fractional_fin_count_is_refused(self):
        errors = validate_spec(dict(VALID, fin_count=15.5))
        self.assertTrue(any("whole number" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
