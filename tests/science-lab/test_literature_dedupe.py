"""Literature dedupe tests (CB2-102..103). Pure."""
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
        "id": "SRC-1", "title": "A Study", "authors": ["Ada"],
        "year": 2020, "doi": "10.1000/ABC",
        "citation": "Ada (2020). A Study. Venue. doi:10.1000/ABC.",
        "retrieved_at": "2026-01-01", "access_note": "open",
        "supports_claim": "claim", "locator": "doi:10.1000/abc",
        "content_hash": "a" * 64,
    }
    item.update(kw)
    return item


class DedupeTests(unittest.TestCase):
    def test_same_doi_with_different_casing_is_one_source(self):
        kept = literature.dedupe_sources([
            source(id="A", doi="10.1000/ABC"),
            source(id="B", doi="10.1000/abc", title="Other title"),
        ])
        self.assertEqual([item["id"] for item in kept], ["A"])

    def test_no_doi_dedupes_on_normalised_title(self):
        one = source(id="A", doi=None, citation="No doi here.",
                     locator="https://example.invalid/a")
        two = source(id="B", doi=None, citation="No doi here.",
                     locator="https://example.invalid/b", title="A  study!")
        kept = literature.dedupe_sources([one, two])
        self.assertEqual([item["id"] for item in kept], ["A"])


if __name__ == "__main__":
    unittest.main()
