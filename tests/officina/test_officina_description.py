"""CB2-456..457 — the rough-words parser's defaults and fallbacks."""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds", "officina", "runtime"
    ),
)

from brief import DEFAULT_PARAMS, parse_rough_words  # noqa: E402


class Description(unittest.TestCase):
    def test_a_plain_description_yields_the_documented_defaults(self):
        brief = parse_rough_words("I need a heatsink, about 50 mm square, no fan")
        self.assertEqual(brief["artefact_class"], "heatsink-fin-geometry")
        self.assertEqual(brief["parameters"], DEFAULT_PARAMS)
        self.assertTrue(brief["gradeable"])

    def test_missing_dimensions_fall_back_to_defaults_and_flag_unknowns(self):
        brief = parse_rough_words("make me a heatsink for a hot chip")
        self.assertEqual(brief["parameters"], DEFAULT_PARAMS)
        # Nothing was stated about the dimensions, so the brief must not
        # pretend it knows them: the unknowns list is the flag.
        self.assertTrue(brief["unknowns"], brief)
        self.assertTrue(
            any(entry.get("slot") for entry in brief["unknowns"]), brief["unknowns"]
        )

    def test_no_artefact_class_is_named_and_not_gradeable(self):
        brief = parse_rough_words("build me something nice")
        self.assertIsNone(brief["artefact_class"])
        self.assertFalse(brief["gradeable"])
        self.assertEqual(brief["unknowns"][0]["slot"], "artefact_class")

    def test_a_stated_footprint_that_differs_is_recorded_as_a_conflict(self):
        brief = parse_rough_words("a heatsink 80 mm square")
        kinds = [conflict["kind"] for conflict in brief["conflicts"]]
        self.assertIn("footprint_mm", kinds)


if __name__ == "__main__":
    unittest.main()
