"""Dispatch URL edge tests (CB2-001..003). Offline; no socket."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_common  # noqa: E402


class DispatchUrlEdgeTests(unittest.TestCase):
    def test_http_https_port_and_trailing_slash_loopback_forms(self):
        for url in (
            "http://127.0.0.1:8935/dispatch-simulated",
            "https://127.0.0.1:8935/dispatch-simulated",
            "http://localhost:8935/dispatch-simulated",
            "http://localhost/dispatch-simulated",
            "http://localhost:8935/dispatch-simulated/",
        ):
            self.assertEqual(crew_common.check_dispatch_url(url), url)
            self.assertEqual(crew.check_dispatch_url(url), url)

    def test_non_loopback_hosts_are_refused(self):
        for url in (
            "http://0.0.0.0:8935/dispatch-simulated",
            "https://api.emergency.example/911",
            "http://192.168.1.5:8935/dispatch-simulated",
            "http://127.0.0.1.evil.example/dispatch-simulated",
        ):
            with self.assertRaises(crew_common.DispatchBoundaryError):
                crew_common.check_dispatch_url(url)
            with self.assertRaises(crew.DispatchBoundaryError):
                crew.check_dispatch_url(url)

    def test_bracketed_ipv6_loopback_is_allowed_but_bare_is_refused(self):
        self.assertEqual(
            crew_common.check_dispatch_url("http://[::1]:8935/dispatch"),
            "http://[::1]:8935/dispatch")
        with self.assertRaises(crew_common.DispatchBoundaryError):
            crew_common.check_dispatch_url("http://::1:8935/dispatch")

    def test_userinfo_is_refused(self):
        for url in (
            "http://user@127.0.0.1:8935/dispatch-simulated",
            "http://user:pass@localhost:8935/dispatch-simulated",
        ):
            with self.assertRaises(crew_common.DispatchBoundaryError):
                crew_common.check_dispatch_url(url)

    def test_query_and_fragment_are_allowed_today(self):
        # Pinned current behaviour: the guard checks authority only,
        # so a loopback URL may carry a query or fragment.
        for url in (
            "http://127.0.0.1:8935/dispatch-simulated?trace=1",
            "http://localhost:8935/dispatch-simulated#receipt",
        ):
            self.assertEqual(crew_common.check_dispatch_url(url), url)


if __name__ == "__main__":
    unittest.main()
