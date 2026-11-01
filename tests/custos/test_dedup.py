"""Alert-dedup tests for META CUSTOS (RW-008).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The patrol collapses identical alert findings inside a configured
window into one record with a count. The synthetic repeat feed here
is a headers audit that serves the same missing headers on every
patrol, plus a down host for the red case — injected signals only,
no network, no live hosts.

Claims pinned here:

  * a repeated yellow finding inside the window emits no second
    record; the second patrol's summary reports it suppressed, with
    its running count;
  * a repeated red finding inside the window produces no duplicate
    escalation (the first occurrence already ran the chain);
  * baseline normal records are never deduped — liveness history
    keeps one record per patrol;
  * after the window passes, the same finding emits again and its
    count resets;
  * a finding whose detail changes is a new finding, not a repeat;
  * duplicates inside one patrol's list fold into one record
    carrying "occurrences";
  * with no window configured, or no dedup state supplied, every
    patrol records what it finds (pre-RW-008 behaviour);
  * an invalid window is a summary error and dedup stays off;
  * the dedup state survives a save/load round-trip through the
    patrol state file, while load_state's 3-tuple return is
    unchanged.
"""

import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import dedup  # noqa: E402
import patrol  # noqa: E402

NOW1 = "2026-11-01T05:00:00Z"
NOW2 = "2026-11-01T05:30:00Z"
NOW3 = "2026-11-01T05:45:00Z"
NOW_LATE = "2026-11-01T07:00:00Z"

FULL_HEADERS = {
    "strict-transport-security": "max-age=31536000",
    "content-security-policy": "default-src 'self'",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


def headers_config(window=None):
    config = {
        "hosts": [{"host": "up.example", "port": 443,
                   "expected_ports": [443]}],
        "inventory": [],
        "cert_warn_days": 21,
        "sensitive_ports": [22],
    }
    if window is not None:
        config["dedup_window_seconds"] = window
    return config


def fake_cert(_host, _port):
    return 90  # baseline normal: headers, not expiry, under test


def fake_port_up(host, port):
    return (host, port) == ("up.example", 443)


def fake_port_down(_host, _port):
    return False


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def summary(records):
    return records[-1]


def run_headers(config, now, dedup_state, headers):
    return patrol.run_patrol(
        config, now, lambda _url: [], fake_cert, fake_port_up,
        fetch_headers_fn=lambda _h, _p: dict(headers),
        seen_dedup=dedup_state)


class TestFindingKey(unittest.TestCase):
    def test_key_ignores_detail_order(self):
        first = patrol.make_record(NOW1, "headers", "up.example",
                                   "security headers missing",
                                   {"port": 443, "missing": ["a", "b"]})
        second = patrol.make_record(NOW1, "headers", "up.example",
                                    "security headers missing",
                                    {"missing": ["a", "b"], "port": 443})
        self.assertEqual(dedup.finding_key(first),
                         dedup.finding_key(second))

    def test_key_changes_with_detail(self):
        first = patrol.make_record(NOW1, "headers", "up.example",
                                   "security headers missing",
                                   {"missing": ["a"]})
        second = patrol.make_record(NOW1, "headers", "up.example",
                                    "security headers missing",
                                    {"missing": ["b"]})
        self.assertNotEqual(dedup.finding_key(first),
                            dedup.finding_key(second))

    def test_within_patrol_duplicates_fold_with_occurrences(self):
        base = patrol.make_record(NOW1, "headers", "up.example",
                                  "security headers missing",
                                  {"missing": ["a"]})
        repeat = patrol.make_record(NOW1, "headers", "up.example",
                                    "security headers missing",
                                    {"missing": ["a"]})
        kept, collapsed, suppressed, _counts = dedup.apply_dedup(
            [base, repeat], {}, NOW1, 3600)
        self.assertEqual(len(kept), 1)
        self.assertEqual(collapsed, 1)
        self.assertEqual(suppressed, 0)
        self.assertEqual(kept[0]["detail"]["occurrences"], 2)


class TestWindowDedup(unittest.TestCase):
    def test_repeat_yellow_suppressed_with_count(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        state = {}
        records, _s, _c = run_headers(headers_config(3600), NOW1, state,
                                      partial)
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)
        records2, _s, _c = run_headers(headers_config(3600), NOW2, state,
                                       partial)
        yellow2 = [r for r in observations(records2)
                   if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow2), 0)
        self.assertEqual(summary(records2)["dedup_suppressed"], 1)
        self.assertEqual(list(summary(records2)["dedup_counts"].values()),
                         [2])
        # Third patrol inside the same window: count keeps growing.
        records3, _s, _c = run_headers(headers_config(3600), NOW3, state,
                                       partial)
        self.assertEqual(summary(records3)["dedup_suppressed"], 1)
        self.assertEqual(list(summary(records3)["dedup_counts"].values()),
                         [3])

    def test_baseline_records_never_deduped(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        state = {}
        records, _s, _c = run_headers(headers_config(3600), NOW1, state,
                                      partial)
        records2, _s, _c = run_headers(headers_config(3600), NOW2, state,
                                       partial)
        baseline = [r for r in observations(records2)
                    if r["category"] == "baseline normal"]
        # Service liveness + certificate: one record per patrol.
        self.assertEqual(len(baseline), 2)

    def test_repeat_red_produces_no_duplicate_escalation(self):
        config = {
            "hosts": [{"host": "down.example", "port": 443,
                       "expected_ports": [443]}],
            "inventory": [],
            "cert_warn_days": 21,
            "sensitive_ports": [22],
            "dedup_window_seconds": 3600,
        }
        state = {}
        records, _s, _c = patrol.run_patrol(
            config, NOW1, lambda _url: [], fake_cert, fake_port_down,
            seen_dedup=state)
        self.assertEqual(summary(records)["escalations"], 1)
        records2, _s, _c = patrol.run_patrol(
            config, NOW2, lambda _url: [], fake_cert, fake_port_down,
            seen_dedup=state)
        down = [r for r in observations(records2)
                if r["category"] == "service down"]
        self.assertEqual(len(down), 0)
        self.assertEqual(summary(records2)["escalations"], 0)
        self.assertEqual(summary(records2)["dedup_suppressed"], 1)

    def test_window_expiry_reemits_and_resets_count(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        state = {}
        run_headers(headers_config(3600), NOW1, state, partial)
        run_headers(headers_config(3600), NOW2, state, partial)
        records, _s, _c = run_headers(headers_config(3600), NOW_LATE,
                                      state, partial)
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)
        self.assertEqual(summary(records)["dedup_suppressed"], 0)
        self.assertEqual(summary(records)["dedup_counts"], {})

    def test_changed_detail_is_a_new_finding(self):
        first = {k: v for k, v in FULL_HEADERS.items()
                 if k != "content-security-policy"}
        second = {k: v for k, v in FULL_HEADERS.items()
                  if k not in ("content-security-policy",
                               "x-frame-options")}
        state = {}
        run_headers(headers_config(3600), NOW1, state, first)
        records, _s, _c = run_headers(headers_config(3600), NOW2, state,
                                      second)
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)
        self.assertEqual(summary(records)["dedup_suppressed"], 0)

    def test_no_window_means_no_dedup(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        state = {}
        run_headers(headers_config(), NOW1, state, partial)
        records, _s, _c = run_headers(headers_config(), NOW2, state,
                                      partial)
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)
        self.assertEqual(summary(records)["dedup_suppressed"], 0)

    def test_no_state_dict_means_no_dedup(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        run_headers(headers_config(3600), NOW1, None, partial)
        records, _s, _c = patrol.run_patrol(
            headers_config(3600), NOW2, lambda _url: [], fake_cert,
            fake_port_up,
            fetch_headers_fn=lambda _h, _p: dict(partial))
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)

    def test_invalid_window_is_error_and_dedup_off(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k != "content-security-policy"}
        state = {}
        records, _s, _c = run_headers(headers_config(-5), NOW1, state,
                                      partial)
        self.assertTrue(any("dedup window invalid" in e
                            for e in summary(records)["errors"]))
        yellow = [r for r in observations(records)
                  if r["category"] == "security headers missing"]
        self.assertEqual(len(yellow), 1)
        self.assertIsNone(summary(records)["dedup_window_seconds"])


class TestDedupStateFile(unittest.TestCase):
    def test_save_load_round_trip_keeps_load_state_shape(self):
        state = {}
        run_headers(headers_config(3600), NOW1, state,
                    {k: v for k, v in FULL_HEADERS.items()
                     if k != "content-security-policy"})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            patrol.save_state(path, {"CVE-2024-0001"}, {123},
                              {"example.org": {"A": ["1.2.3.4"]}},
                              state)
            seen_cve, seen_ct, seen_dns = patrol.load_state(path)
            self.assertEqual(seen_cve, {"CVE-2024-0001"})
            self.assertEqual(seen_ct, {123})
            self.assertEqual(seen_dns,
                             {"example.org": {"A": ["1.2.3.4"]}})
            loaded = patrol.load_dedup_state(path)
            self.assertEqual(loaded, state)
            self.assertEqual(len(loaded), 1)


if __name__ == "__main__":
    unittest.main()
