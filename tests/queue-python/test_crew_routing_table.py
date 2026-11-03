"""Division routing table tests (CB2-010..011). Offline; no HTTP."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402


class RoutingTableTests(unittest.TestCase):
    def test_vigiles_routes_to_police(self):
        route = judge.service_route("vigiles")
        self.assertEqual(route["service"], "police")
        self.assertEqual(route["path"], "/police")

    def test_ignis_routes_to_fire(self):
        route = judge.service_route("ignis")
        self.assertEqual(route["service"], "fire department")
        self.assertEqual(route["path"], "/fire")

    def test_medicus_routes_to_hospital(self):
        route = judge.service_route("medicus")
        self.assertEqual(route["service"], "hospital (EMS receiving)")
        self.assertEqual(route["path"], "/hospital")

    def test_unknown_division_never_defaults_to_an_endpoint(self):
        self.assertIsNone(judge.service_route("custodes"))
        self.assertIsNone(judge.service_route(""))
        self.assertIsNone(judge.service_route(None))


if __name__ == "__main__":
    unittest.main()
