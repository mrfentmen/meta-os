"""Literature shelf tests (CB2-104, 122). Pure in-memory index."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


def source(sid, title, shelf=None):
    item = {
        "id": sid, "title": title, "authors": ["Ada"], "year": 2020,
        "citation": "Ada (2020). %s. Venue." % title,
        "retrieved_at": "2026-01-01", "access_note": "open",
        "supports_claim": title, "locator": "https://example.invalid/%s" % sid,
        "content_hash": "a" * 64,
    }
    if shelf is not None:
        item["tags"] = [shelf]
    return item


class ShelfTests(unittest.TestCase):
    def test_tagged_source_lands_on_chemistry_untagged_is_unfiled(self):
        self.assertEqual(literature.assign_shelf(source("A", "A", "chemistry")),
                         "chemistry")
        self.assertEqual(literature.assign_shelf(source("B", "B")),
                         literature.UNFILED_SHELF)

    def test_three_sources_list_in_filing_order(self):
        index = literature.ShelfIndex()
        for sid, title in (("C1", "First"), ("C2", "Second"),
                           ("C3", "Third")):
            self.assertEqual(index.file(source(sid, title, "chemistry")),
                             "chemistry")
        self.assertEqual([row["id"] for row in index.list("chemistry")],
                         ["C1", "C2", "C3"])


if __name__ == "__main__":
    unittest.main()
