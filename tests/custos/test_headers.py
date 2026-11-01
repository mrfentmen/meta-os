"""Security-headers audit tests for META CUSTOS (RW-004).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The patrol scores the security headers a watched host actually
serves (HSTS, CSP, X-Frame-Options, X-Content-Type-Options,
Referrer-Policy). This is an audit only: the patrol never auto-fixes
a header, never rewrites a config, never touches the watched host
beyond reading its response headers.

Claims pinned here:

  * a host serving all five headers is baseline normal, score 5/5;
  * a host missing any header becomes a "security headers missing"
    record (yellow tier, zero escalation) carrying the missing list;
  * header names match case-insensitively, values are not graded;
  * a headers fetch failure is an error in the summary, never data;
  * a down host is skipped before the headers step, so it gets no
    headers record.
"""

import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T05:00:00Z"

FULL_HEADERS = {
    "strict-transport-security": "max-age=31536000",
    "content-security-policy": "default-src 'self'",
    "x-frame-options": "DENY",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
}


def header_config():
    return {
        "hosts": [
            {"host": "up.example", "port": 443, "expected_ports": [443]},
            {"host": "down.example", "port": 443, "expected_ports": [443]},
        ],
        "inventory": [],
        "cert_warn_days": 21,
        "sensitive_ports": [22],
    }


def fake_cert(_host, _port):
    return 90  # baseline normal: headers, not expiry, under test


def fake_port(host, port):
    return (host, port) == ("up.example", 443)


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def header_records(records):
    return [r for r in observations(records) if r["source"] == "headers"]


def run_with_headers(headers_fn):
    return patrol.run_patrol(
        header_config(), NOW, lambda _url: [], fake_cert, fake_port,
        fetch_headers_fn=headers_fn)


class TestHeaderAudit(unittest.TestCase):
    def test_full_set_is_baseline_normal_score_five(self):
        records, _s, _c = run_with_headers(
            lambda _h, _p: dict(FULL_HEADERS))
        recs = header_records(records)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["host"], "up.example")
        self.assertEqual(rec["category"], "baseline normal")
        self.assertEqual(rec["tier"], "none")
        self.assertEqual(rec["detail"]["score"], 5)
        self.assertEqual(rec["detail"]["max_score"], 5)
        self.assertEqual(rec["detail"]["missing"], [])
        self.assertEqual(rec["detail"]["present"],
                         list(patrol.SECURITY_HEADERS))

    def test_missing_headers_are_yellow_with_missing_list(self):
        partial = {k: v for k, v in FULL_HEADERS.items()
                   if k not in ("content-security-policy",
                                "x-frame-options")}
        records, _s, _c = run_with_headers(lambda _h, _p: partial)
        recs = header_records(records)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["category"], "security headers missing")
        self.assertEqual(rec["tier"], "yellow")
        self.assertEqual(rec["detail"]["score"], 3)
        self.assertEqual(rec["detail"]["missing"],
                         ["content-security-policy", "x-frame-options"])
        # Yellow means zero escalation calls for this category,
        # pinned here (the down host in this config still escalates
        # on its own red service-down record, which is unrelated).
        self.assertNotIn(
            "security headers missing",
            {r["for_category"] for r in records
             if r["record_type"] == "escalation"})

    def test_empty_headers_miss_all_five(self):
        records, _s, _c = run_with_headers(lambda _h, _p: {})
        rec = header_records(records)[0]
        self.assertEqual(rec["category"], "security headers missing")
        self.assertEqual(rec["detail"]["score"], 0)
        self.assertEqual(rec["detail"]["missing"],
                         list(patrol.SECURITY_HEADERS))

    def test_header_names_match_case_insensitively(self):
        mixed = {"Strict-Transport-Security": "max-age=31536000",
                 "Content-Security-Policy": "default-src 'self'",
                 "X-Frame-Options": "DENY",
                 "X-Content-Type-Options": "nosniff",
                 "Referrer-Policy": "no-referrer"}
        records, _s, _c = run_with_headers(lambda _h, _p: mixed)
        rec = header_records(records)[0]
        self.assertEqual(rec["category"], "baseline normal")
        self.assertEqual(rec["detail"]["missing"], [])

    def test_pure_audit_helpers(self):
        present, missing = patrol.header_audit(
            {"X-Frame-Options": "DENY"})
        self.assertEqual(present, ["x-frame-options"])
        self.assertEqual(len(missing), 4)
        self.assertEqual(patrol.classify_headers([]), "baseline normal")
        self.assertEqual(patrol.classify_headers(["x-frame-options"]),
                         "security headers missing")
        self.assertEqual(patrol.tier_for("security headers missing"),
                         "yellow")

    def test_fetch_failure_is_error_not_data(self):
        def broken(_host, _port):
            raise OSError("host unreachable")
        records, _s, _c = run_with_headers(broken)
        self.assertEqual(header_records(records), [])
        summary = records[-1]
        self.assertEqual(summary["record_type"], "patrol-summary")
        self.assertTrue(any("headers fetch failed for up.example:443" in e
                            for e in summary["errors"]))
        # The liveness baseline still recorded; the failure did not
        # stop the patrol.
        self.assertTrue(any(r["host"] == "up.example" and
                            r["category"] == "baseline normal"
                            for r in observations(records)))

    def test_down_host_gets_no_headers_record(self):
        records, _s, _c = run_with_headers(
            lambda _h, _p: dict(FULL_HEADERS))
        self.assertEqual(
            [r for r in header_records(records)
             if r["host"] == "down.example"], [])
        self.assertTrue(any(r["host"] == "down.example" and
                            r["category"] == "service down"
                            for r in observations(records)))


if __name__ == "__main__":
    unittest.main()
