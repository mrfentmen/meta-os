"""CB2-197: the repository schema registry loads all five JSON schemas."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import repository  # noqa: E402


class TestSchemasLoad(unittest.TestCase):
    def test_five_schemas_load_and_parse(self):
        schemas = repository.load_schemas()
        self.assertEqual(len(schemas), 5)
        self.assertEqual(set(schemas), {
            "cycle", "experiment", "hypothesis", "repository", "source",
        })
        for name, doc in schemas.items():
            self.assertIsInstance(doc, dict, name)
            self.assertIn("$schema", doc, name)


if __name__ == "__main__":
    unittest.main()
