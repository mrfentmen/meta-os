"""Literature year tests (CB2-106). The module refuses ranges."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


class YearTests(unittest.TestCase):
    def test_four_digit_year_parses(self):
        self.assertEqual(literature.parse_year("2004"), 2004)
        self.assertEqual(literature.parse_year(2004), 2004)

    def test_range_is_refused_not_split(self):
        with self.assertRaisesRegex(literature.LiteratureSourceError,
                                    "range"):
            literature.parse_year("2001-2004")

    def test_short_or_non_numeric_year_is_refused(self):
        for bad in ("04", "abcd", True, 99):
            with self.assertRaises(literature.LiteratureSourceError):
                literature.parse_year(bad)


if __name__ == "__main__":
    unittest.main()
