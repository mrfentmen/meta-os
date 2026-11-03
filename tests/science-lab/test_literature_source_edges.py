"""Literature source edge tests (CB2-101, 105, 124). Offline."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


def source(**kw):
    item = {
        "id": "SRC-1", "title": "A Study", "authors": ["Ada Lovelace"],
        "year": 2020, "doi": "10.1000/ABC",
        "citation": "Ada Lovelace (2020). A Study. Venue. doi:10.1000/ABC.",
        "retrieved_at": "2026-01-01", "access_note": "open access",
        "supports_claim": "the study supports it", "locator": "doi:10.1000/abc",
        "content_hash": "a" * 64,
    }
    item.update(kw)
    return item


class SourceEdgeTests(unittest.TestCase):
    def test_missing_title_is_rejected_with_a_named_error(self):
        record = source()
        record.pop("title")
        with self.assertRaisesRegex(ValueError, "title"):
            literature.parse_source(record)

    def test_missing_abstract_stays_none_never_invented(self):
        parsed = literature.parse_source(source())
        self.assertIsNone(parsed["abstract"])

    def test_archive_url_identifier_is_not_misclassified_as_doi(self):
        parsed = literature.parse_source(source(
            doi=None, citation="Old archive item (1901). Notes. Archive.",
            locator="https://archive.org/details/old-item",
            identifier="https://archive.org/details/old-item"))
        self.assertIsNone(parsed["doi"])
        self.assertEqual(parsed["identifier_type"], "archive-url")
        self.assertEqual(parsed["identifier"],
                         "https://archive.org/details/old-item")


if __name__ == "__main__":
    unittest.main()
