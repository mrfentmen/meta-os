"""Simulated dispatch receipt id tests (CB2-012). Offline; no socket."""
import hashlib
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import queue_service  # noqa: E402


class ReceiptIdTests(unittest.TestCase):
    PACKAGE = {"simulated": True, "kind": "imperium-dispatch-package",
               "incident_id": "incident-1"}

    def test_sim_prefix_and_sixteen_hex_characters(self):
        receipt = queue_service.receipt_id_for(self.PACKAGE)
        self.assertTrue(receipt.startswith("sim-"))
        self.assertEqual(len(receipt), len("sim-") + 16)
        int(receipt[4:], 16)  # raises if the suffix is not hex

    def test_same_package_has_the_same_receipt(self):
        self.assertEqual(
            queue_service.receipt_id_for(self.PACKAGE),
            queue_service.receipt_id_for(dict(self.PACKAGE)))

    def test_key_order_does_not_change_the_receipt(self):
        one = {"b": 2, "a": 1}
        two = {"a": 1, "b": 2}
        self.assertEqual(queue_service.receipt_id_for(one),
                         queue_service.receipt_id_for(two))

    def test_different_packages_have_different_receipts(self):
        other = dict(self.PACKAGE, incident_id="incident-2")
        self.assertNotEqual(queue_service.receipt_id_for(self.PACKAGE),
                            queue_service.receipt_id_for(other))

    def test_matches_the_documented_hash_formula(self):
        expected = "sim-" + hashlib.sha256(
            json.dumps(self.PACKAGE, sort_keys=True).encode()
        ).hexdigest()[:16]
        self.assertEqual(queue_service.receipt_id_for(self.PACKAGE),
                         expected)


if __name__ == "__main__":
    unittest.main()
