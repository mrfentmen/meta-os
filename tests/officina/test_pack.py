"""Pack-contract tests for META OFFICINA.

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

The manifest must satisfy the pack contract in os/worlds/README.md
(checked by os/worlds/validate_pack.py), the world registry must
list the pack, and the products file must carry the world entry
without touching the Trio camera list (guarded by the
product-parity test, which asserts exactly three camera products).
"""

import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

sys.path.insert(0, os.path.join(REPO, "os", "worlds"))

from validate_pack import validate_pack  # noqa: E402


class TestPackManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "os", "worlds", "officina",
                               "pack.json")) as f:
            cls.manifest = json.load(f)

    def test_validator_passes(self):
        self.assertEqual(validate_pack(self.manifest), [])

    def test_status_is_partial_not_built(self):
        # Stage 1 runs a loop and a simulator, not a manufacturing
        # line: partial is the honest status, never built.
        self.assertEqual(self.manifest["status"], "partial")

    def test_runtime_parts_exist(self):
        for part in self.manifest["runtime"]["parts"]:
            self.assertTrue(
                os.path.isfile(os.path.join(REPO, part["path"])),
                "missing runtime part: %s" % part["path"],
            )

    def test_exactly_one_messenger_role(self):
        heralds = [a for a in self.manifest["agents"]
                   if "messenger" in a["role"]]
        self.assertEqual(len(heralds), 1)
        self.assertEqual(heralds[0]["nick"], "workshop-herald")

    def test_pack_files_exist(self):
        for name in ("pack.json", "PACK.md"):
            self.assertTrue(os.path.isfile(os.path.join(
                REPO, "os", "worlds", "officina", name)))


class TestRegistry(unittest.TestCase):
    def test_worlds_readme_lists_officina(self):
        with open(os.path.join(REPO, "os", "worlds", "README.md")) as f:
            readme = f.read()
        self.assertIn("| officina |", readme)

    def test_products_file_carries_world_entry_not_camera_product(self):
        with open(os.path.join(REPO, "js", "products.js")) as f:
            source = f.read()
        self.assertIn("WORLD_PRODUCTS", source)
        self.assertIn('id: "officina"', source)
        # The Trio camera list itself is untouched: officina must not
        # appear inside the PRODUCTS array (parity test guards this).
        products_block = source.split("export const PRODUCT_BY_ID")[0]
        self.assertNotIn("officina", products_block)


if __name__ == "__main__":
    unittest.main()
