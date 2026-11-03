"""Literature source schema conformance (CB2-125). Offline."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


def source(n=1, **kw):
    item = {
        "id": "S%d" % n, "title": "Study %d" % n, "authors": ["Ada"],
        "year": 2020, "doi": "10.1000/S%d" % n,
        "citation": "Ada (2020). Study %d. Venue. doi:10.1000/S%d."
                    % (n, n),
        "retrieved_at": "2026-01-01", "access_note": "open",
        "supports_claim": "claim %d" % n,
        "locator": "doi:10.1000/S%d" % n, "content_hash": "a" * 64,
    }
    item.update(kw)
    return item


class SchemaFitTests(unittest.TestCase):
    def test_every_parsed_fixture_source_validates(self):
        parsed = [literature.parse_source(source(n))
                  for n in (1, 2, 3)]
        for record in parsed:
            self.assertEqual(
                literature.validate_source_against_schema(record), [],
                record["id"])


if __name__ == "__main__":
    unittest.main()
