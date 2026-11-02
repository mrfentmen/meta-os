"""Tests for the Imperium judge (server/queue/judge.py) and the
service routing it drives. Offline; run with the queue suite."""
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402
import judge  # noqa: E402


class RoutingTests(unittest.TestCase):
    def test_each_division_routes_to_its_service(self):
        self.assertEqual(judge.service_route("vigiles")["service"], "police")
        self.assertEqual(judge.service_route("ignis")["service"],
                         "fire department")
        self.assertEqual(judge.service_route("medicus")["service"],
                         "hospital (EMS receiving)")

    def test_unknown_division_has_no_route(self):
        self.assertIsNone(judge.service_route("custodes"))


class CombineTests(unittest.TestCase):
    def rule(self, division, first, review, ok=True):
        return judge.combine(division, first, review, ok,
                             crew_common.is_flagged_category)

    def test_agreeing_flagged_readings_confirm(self):
        verdict, reasons = self.rule("vigiles", "person down", "person down")
        self.assertEqual(verdict, "confirmed")
        self.assertTrue(reasons)

    def test_different_flagged_readings_still_confirm(self):
        verdict, _ = self.rule("vigiles", "person down",
                               "possible altercation")
        self.assertEqual(verdict, "confirmed")

    def test_baseline_review_clears(self):
        verdict, reasons = self.rule("vigiles", "person down",
                                     "normal activity")
        self.assertEqual(verdict, "cleared")
        self.assertIn("look-alike", reasons[0])

    def test_failed_review_is_inconclusive_never_confirmed(self):
        verdict, _ = self.rule("vigiles", "person down", None, ok=False)
        self.assertEqual(verdict, "inconclusive")


class ParseVerdictTests(unittest.TestCase):
    def test_three_verdicts_map(self):
        self.assertEqual(judge.parse_verdict(
            '{"verdict": "confirm", "category": "person down",'
            ' "reasons": ["both readings agree"]}')[0], "confirmed")
        self.assertEqual(judge.parse_verdict(
            '{"verdict": "reject", "reasons": []}')[0], "cleared")
        self.assertEqual(judge.parse_verdict(
            '{"verdict": "investigate", "reasons": []}')[0],
            "inconclusive")

    def test_garbage_never_confirms(self):
        for bad in ("not json", "[]", '{"verdict": "send it"}', '{}'):
            self.assertEqual(judge.parse_verdict(bad)[0], "inconclusive",
                             bad)


class PromptTests(unittest.TestCase):
    def test_prompt_carries_both_readings_and_the_service(self):
        text = judge.build_judge_prompt(
            "ignis",
            {"assessment": {"category": "visible flame"}},
            {"assessment": {"category": "visible smoke"}})
        self.assertIn("visible flame", text)
        self.assertIn("visible smoke", text)
        self.assertIn("fire department", text)
        self.assertIn("no human sits between your ruling", text)


class RoutedDispatchTests(unittest.TestCase):
    def test_posts_to_the_services_simulated_path(self):
        seen = {}

        def fake_http_dispatch(url):
            seen["url"] = url
            return lambda package: {"receipt_id": "sim-1"}

        with unittest.mock.patch.object(crew, "http_dispatch",
                                        fake_http_dispatch):
            dispatch = crew.routed_dispatch(
                "http://127.0.0.1:8935/dispatch-simulated")
            receipt = dispatch({"service": judge.service_route("medicus")})
        self.assertEqual(receipt["receipt_id"], "sim-1")
        self.assertEqual(
            seen["url"],
            "http://127.0.0.1:8935/dispatch-simulated/hospital")

    def test_non_loopback_base_is_refused(self):
        with self.assertRaises(crew.DispatchBoundaryError):
            crew.routed_dispatch("https://api.emergency.example/911")


if __name__ == "__main__":
    unittest.main()
