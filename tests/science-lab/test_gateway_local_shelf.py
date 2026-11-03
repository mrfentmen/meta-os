"""Gateway LOCAL-SHELF tests (CB2-109..110). No network."""
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


def shelf_dir():
    root = tempfile.mkdtemp(prefix="gateway-shelf-")
    with open(os.path.join(root, "chemistry.json"), "w") as fh:
        json.dump({"sources": [{
            "id": "S1", "title": "Solubility study",
            "citation": "Ada (2020). Solubility study.",
            "claim": "solubility", "locator": "doi:10.1000/x"}]}, fh)
    return root


class LocalShelfTests(unittest.TestCase):
    def test_local_shelf_answers_without_constructing_adapter(self):
        calls = []

        def factory():
            calls.append(True)
            raise AssertionError("remote adapter must not be constructed")

        hits = gateway.search_shelf(
            "solubility", shelves_dir=shelf_dir(), adapter_factory=factory)
        self.assertEqual(len(hits), 1)
        self.assertEqual(calls, [])

    def test_remote_adapter_raises_unimplemented_and_names_it(self):
        calls = []
        with self.assertRaises(NotImplementedError) as raised:
            gateway.remote_query(
                "solubility", adapter="openalex",
                adapter_factory=lambda: calls.append(True))
        self.assertIn("UNIMPLEMENTED", str(raised.exception))
        self.assertIn("openalex", str(raised.exception))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
