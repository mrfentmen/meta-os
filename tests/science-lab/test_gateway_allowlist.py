"""Gateway allowlist tests (CB2-107..108). No network."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import gateway  # noqa: E402

NINE = ("openalex", "archive-org", "open-library", "gbif", "wikidata",
        "wikisource", "ietf", "federal-register", "osv")


class AllowlistTests(unittest.TestCase):
    def test_all_nine_allowlisted_servers_are_accepted(self):
        self.assertEqual(set(NINE), set(gateway.ALLOWLIST))
        for server in NINE:
            self.assertEqual(gateway.validate_server(server), server)

    def test_near_miss_hyphen_and_unknown_are_refused(self):
        for server in ("open-alex", "openalex-", "OpenAlex", "example"):
            with self.assertRaises(gateway.GatewayRefused):
                gateway.validate_server(server)

    def test_empty_name_is_refused(self):
        with self.assertRaises(gateway.GatewayRefused):
            gateway.validate_server("  ")


if __name__ == "__main__":
    unittest.main()
