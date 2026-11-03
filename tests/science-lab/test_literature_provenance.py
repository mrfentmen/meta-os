"""Literature provenance tests (CB2-115). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


def source():
    return {
        "id": "S1", "title": "A study", "authors": ["Ada"], "year": 2020,
        "citation": "Ada (2020). A study.", "retrieved_at": "2026-01-01",
        "access_note": "open", "supports_claim": "claim",
        "locator": "https://example.invalid/s", "content_hash": "a" * 64,
        "server": "openalex", "tags": ["chemistry"],
    }


class ProvenanceTests(unittest.TestCase):
    def test_origin_survives_parse_and_shelf_filing(self):
        parsed = literature.parse_source(source())
        self.assertEqual(parsed["origin"], "openalex")
        index = literature.ShelfIndex()
        self.assertEqual(index.file(source()), "chemistry")
        self.assertEqual(index.list("chemistry")[0]["origin"], "openalex")


if __name__ == "__main__":
    unittest.main()
