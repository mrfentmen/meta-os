"""Literature corpus test (CB2-116). Pure; 12 local fixture records."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


def source(n, **kw):
    item = {
        "id": "S%d" % n, "title": "Study %d" % n,
        "authors": ["Ada"], "year": 2020, "doi": "10.1000/S%d" % n,
        "citation": "Ada (2020). Study %d. Venue. doi:10.1000/S%d."
                    % (n, n),
        "retrieved_at": "2026-01-01", "access_note": "open",
        "supports_claim": "claim %d" % n,
        "locator": "doi:10.1000/S%d" % n, "content_hash": "a" * 64,
    }
    item.update(kw)
    return item


class CorpusTests(unittest.TestCase):
    def test_twelve_records_count_by_outcome(self):
        valid = [source(i) for i in range(1, 7)]
        duplicates = [source(1), source(2), source(3)]
        malformed = [
            source(7, title=""),
            source(8, citation=""),
            source(9, content_hash="not-a-hash"),
        ]
        result = literature.parse_source_corpus(
            valid + duplicates + malformed)
        self.assertEqual(result["counts"], {
            "received": 12, "parsed": 6, "rejected": 3, "duplicates": 3})
        self.assertEqual(len(result["parsed"]), 6)
        self.assertEqual(len(result["rejected"]), 3)


if __name__ == "__main__":
    unittest.main()
