"""Gateway query tests (CB2-111..112, 123). No network."""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import gateway  # noqa: E402


def make_shelves():
    root = tempfile.mkdtemp(prefix="gateway-query-")
    data = {
        "chemistry.json": {"sources": [{
            "id": "C1", "title": "Chemistry hit",
            "citation": "Chem (2020). Chemistry hit.", "claim": "chemistry",
            "locator": "doi:10.1000/c"}]},
        "biology.json": {"sources": [{
            "id": "B1", "title": "Biology hit",
            "citation": "Bio (2020). Biology hit.", "claim": "biology",
            "locator": "doi:10.1000/b"}]},
    }
    for name, payload in data.items():
        with open(os.path.join(root, name), "w") as fh:
            json.dump(payload, fh)
    return root


class QueryTests(unittest.TestCase):
    def test_empty_query_is_refused_before_lookup(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            gateway.search_shelf("  ", shelves_dir=make_shelves())

    def test_hit_has_only_id_title_and_shelf(self):
        hits = gateway.search_shelf("chemistry", shelves_dir=make_shelves())
        self.assertEqual(set(hits[0]), {"id", "title", "shelf"})
        self.assertEqual(hits[0]["id"], "C1")
        self.assertEqual(hits[0]["shelf"], "chemistry")

    def test_shelf_routing_searches_only_that_shelf(self):
        root = make_shelves()
        self.assertEqual(gateway.search_shelf(
            "biology", shelf="chemistry", shelves_dir=root), [])
        hit = gateway.search_shelf(
            "biology", shelf="biology", shelves_dir=root)
        self.assertEqual([row["id"] for row in hit], ["B1"])


if __name__ == "__main__":
    unittest.main()
