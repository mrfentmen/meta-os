"""Pack-contract tests for META CUSTOS.

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The manifest must satisfy the pack contract in os/worlds/README.md
(checked by os/worlds/validate_pack.py), the world registry must
list the pack, and the products file must carry the world entry
without touching the Trio camera list (guarded by the
product-parity test, which asserts exactly three camera products).
"""

import json
import os
import unittest
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

sys.path.insert(0, os.path.join(REPO, "os", "worlds"))

from validate_pack import validate_pack  # noqa: E402


class TestPackManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "os", "worlds", "custos",
                               "pack.json")) as f:
            cls.manifest = json.load(f)

    def test_validator_passes(self):
        self.assertEqual(validate_pack(self.manifest), [])

    def test_status_is_partial_not_built(self):
        # Stage 1 runs a patrol loop, not a standing service:
        # partial is the honest status, never built.
        self.assertEqual(self.manifest["status"], "partial")

    def test_runtime_parts_exist(self):
        for part in self.manifest["runtime"]["parts"]:
            self.assertTrue(
                os.path.isfile(os.path.join(REPO, "os", part["path"])),
                "missing runtime part: %s" % part["path"],
            )

    def test_exactly_one_messenger_agent(self):
        messengers = [a for a in self.manifest["agents"]
                      if a["nick"].endswith("messenger")]
        self.assertEqual(len(messengers), 1)
        self.assertEqual(messengers[0]["nick"], "escalation-messenger")

    def test_alert_kinds_cover_the_categories(self):
        kinds = {a["kind"] for a in self.manifest["alerts"]}
        for kind in ("certificate-expiring", "certificate-expired",
                     "known-exploited-vulnerability-present",
                     "service-down", "anomalous-exposure",
                     "certificate-issued"):
            self.assertIn(kind, kinds)

    def test_warning_is_yellow_critical_is_red(self):
        # The pack language for the tier rule: warning alerts are the
        # yellow tier (record + flag), critical alerts are red.
        for alert in self.manifest["alerts"]:
            if alert["kind"] == "machine-watch-escalation":
                continue
            if alert["kind"] in ("certificate-expiring",
                                 "anomalous-exposure",
                                 "certificate-issued"):
                self.assertEqual(alert["severity"], "warning")
            else:
                self.assertEqual(alert["severity"], "critical")

    def test_only_the_escalation_summary_crosses_the_bus(self):
        for alert in self.manifest["alerts"]:
            if alert["crosses_bus"]:
                self.assertEqual(alert["kind"], "machine-watch-escalation")
                self.assertEqual(alert["privacy"], "summary")

    def test_pack_files_exist(self):
        for name in ("pack.json", "PACK.md"):
            self.assertTrue(os.path.isfile(os.path.join(
                REPO, "os", "worlds", "custos", name)))


class TestRegistry(unittest.TestCase):
    def test_worlds_readme_lists_custos(self):
        with open(os.path.join(REPO, "os", "worlds", "README.md")) as f:
            readme = f.read()
        self.assertIn("| custos |", readme)

    def test_products_world_entry_without_touching_trio(self):
        with open(os.path.join(REPO, "js", "products.js")) as f:
            text = f.read()
        self.assertIn("export const WORLD_PRODUCTS", text)
        world_block = text.split("export const WORLD_PRODUCTS", 1)[1]
        self.assertIn('id: "custos"', world_block)
        self.assertIn('"os/worlds/custos"', world_block)
        # The Trio camera list itself is untouched: custos must not
        # appear before the WORLD_PRODUCTS marker.
        trio_block = text.split("export const WORLD_PRODUCTS", 1)[0]
        self.assertNotIn("custos", trio_block)


if __name__ == "__main__":
    unittest.main()
