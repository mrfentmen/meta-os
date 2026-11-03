"""Literature citation tests (CB2-113..114). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


class CitationTests(unittest.TestCase):
    def test_golden_citation_string(self):
        text = literature.format_citation({
            "authors": ["Ada Lovelace"], "year": 1843,
            "title": "Notes on the Engine", "venue": "Taylor",
            "doi": "10.1000/XYZ"})
        self.assertEqual(
            text, "Ada Lovelace (1843). Notes on the Engine. Taylor. "
                  "doi:10.1000/xyz.")

    def test_empty_author_list_uses_the_pinned_fallback(self):
        text = literature.format_citation({
            "authors": [], "year": None, "title": "Untitled"})
        self.assertEqual(text, "Unknown author (n.d.). Untitled.")


if __name__ == "__main__":
    unittest.main()
