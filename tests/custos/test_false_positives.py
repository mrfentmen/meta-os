"""False-positive log tests for META CUSTOS (RW-009).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

Pinned on injected signals, no network. The claims:

  * a dismissed finding is suppressed on the next patrol and never
    escalated, while the same category on another host still raises;
  * a dismissal without a reason never suppresses anything;
  * a malformed review file is a summary error and suppresses
    nothing (fail open, never invented suppression);
  * a suppressed finding is still audited as a "dismissed" record
    carrying its reason, not silently dropped;
  * a state-check finding (headers, subdomain) stays suppressed on
    every later patrol, not just the first, because the filter runs
    on every patrol before escalation.
"""

import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import false_positives as fp  # noqa: E402
import patrol  # noqa: E402

NOW = "2026-11-01T03:00:00Z"

KEV_FEED = [
    {"cveID": "CVE-2024-0001", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2024-05-01"},
]


def fake_config():
    return {
        "hosts": [
            {"host": "up.example", "port": 443, "expected_ports": [443]},
            {"host": "down.example", "port": 443, "expected_ports": [443]},
        ],
        "inventory": ["openssl"],
        "cert_warn_days": 21,
        "sensitive_ports": [22, 3306],
    }


def fake_fetch(_url):
    return list(KEV_FEED)


def fake_cert(host, _port):
    return {"up.example": 10}.get(host)


def fake_headers(_host, _port):
    return {"strict-transport-security": "present",
            "content-security-policy": "present",
            "x-frame-options": "present",
            "x-content-type-options": "present"}
    # Referrer-Policy missing: headers-missing yellow for up.example.


def fake_port(host, port):
    return (host, port) == ("up.example", 443)


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def dismissed(records):
    return [r for r in records if r["record_type"] == "dismissed"]


def escalations(records):
    return [r for r in records if r["record_type"] == "escalation"]


def run(dismissals=None, review_errors=None):
    records, _seen, _ct = patrol.run_patrol(
        fake_config(), NOW, fake_fetch, fake_cert, fake_port,
        fetch_headers_fn=fake_headers, dismissals=dismissals,
        review_errors=review_errors)
    return records


class TestKeys(unittest.TestCase):
    def test_kev_key_is_cve(self):
        record = patrol.make_record(
            NOW, "kev", None, "known-exploited vulnerability present",
            {"cve": "CVE-2024-0001"})
        self.assertEqual(fp.key_for_record(record), "CVE-2024-0001")

    def test_headers_key_is_missing_list(self):
        record = patrol.make_record(
            NOW, "headers", "up.example", "security headers missing",
            {"missing": ["referrer-policy"]})
        self.assertEqual(fp.key_for_record(record), "referrer-policy")

    def test_missing_key_is_never_dismissed(self):
        record = patrol.make_record(
            NOW, "kev", None, "known-exploited vulnerability present",
            {})
        self.assertIsNone(fp.key_for_record(record))
        self.assertEqual(fp.is_dismissed(
            record, {("known-exploited vulnerability present", None,
                      "CVE-2024-0001"): "nope"}), (False, None))


class TestSuppression(unittest.TestCase):
    def test_dismissed_red_is_not_observed_and_not_escalated(self):
        dismissals = [{"category": "service down",
                       "host": "down.example", "key": "443",
                       "reason": "host decommissioned"}]
        records = run(dismissals=dismissals)
        self.assertEqual([r for r in observations(records)
                          if r["category"] == "service down"], [])
        self.assertEqual([e for e in escalations(records)
                          if e["for_category"] == "service down"], [])
        d = dismissed(records)
        self.assertEqual(len(d), 1)
        self.assertEqual(d[0]["host"], "down.example")
        self.assertEqual(d[0]["reason"], "host decommissioned")
        summary = records[-1]
        self.assertEqual(summary["false_positives_suppressed"], 1)
        self.assertEqual(summary["false_positive_review_entries"], 1)
        # The undismissed KEV red still escalates: suppression is
        # per-signature, not a global mute.
        self.assertEqual(summary["escalations"], 1)

    def test_same_category_other_host_still_raises(self):
        dismissals = [{"category": "certificate expiring",
                       "host": "other.example", "key": "443",
                       "reason": "not this host"}]
        records = run(dismissals=dismissals)
        self.assertTrue(any(r["host"] == "up.example" and
                            r["category"] == "certificate expiring"
                            for r in observations(records)))
        self.assertEqual(records[-1]["false_positives_suppressed"], 0)

    def test_same_category_other_key_still_raises(self):
        dismissals = [{"category": "known-exploited vulnerability present",
                       "host": None, "key": "CVE-2099-9999",
                       "reason": "different CVE"}]
        records = run(dismissals=dismissals)
        self.assertTrue(any(r["category"] ==
                            "known-exploited vulnerability present"
                            for r in observations(records)))

    def test_state_check_stays_suppressed_every_patrol(self):
        dismissals = [{"category": "security headers missing",
                       "host": "up.example", "key": "referrer-policy",
                       "reason": "header set by upstream proxy, accepted"}]
        for _ in range(2):
            records = run(dismissals=dismissals)
            self.assertEqual([r for r in observations(records)
                              if r["category"] ==
                              "security headers missing"], [])
            self.assertEqual(len(dismissed(records)), 1)

    def test_observation_tallies_exclude_dismissed(self):
        dismissals = [{"category": "service down",
                       "host": "down.example", "key": "443",
                       "reason": "decommissioned"}]
        summary = run(dismissals=dismissals)[-1]
        self.assertEqual(summary["observations"]["service down"], 0)


class TestReviewFile(unittest.TestCase):
    def write(self, text):
        fd, path = tempfile.mkstemp()
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.unlink, path)
        return path

    def test_missing_file_is_empty_not_error(self):
        self.assertEqual(fp.load_review("/nonexistent/review.jsonl"),
                         ([], []))

    def test_jsonl_load_and_reason_required(self):
        path = self.write(
            '{"category": "service down", "host": "down.example", '
            '"key": "443", "reason": "decommissioned"}\n'
            '{"category": "service down", "host": "x.example", '
            '"key": "443"}\n')
        dismissals, errors = fp.load_review(path)
        self.assertEqual(len(dismissals), 1)
        self.assertEqual(len(errors), 1)
        self.assertIn("missing reason", errors[0])

    def test_malformed_file_suppresses_nothing_and_errors(self):
        path = self.write("this is not json\n")
        dismissals, errors = fp.load_review(path)
        self.assertEqual(dismissals, [])
        self.assertTrue(errors)
        records = run(dismissals=dismissals, review_errors=errors)
        self.assertTrue(any(r["category"] == "service down"
                            for r in observations(records)))
        self.assertTrue(any("false-positive review" in e
                            for e in records[-1]["errors"]))

    def test_append_then_load_roundtrip(self):
        path = self.write("")
        fp.append_dismissal(path, "service down", "down.example",
                            "443", "decommissioned")
        dismissals, errors = fp.load_review(path)
        self.assertEqual(errors, [])
        self.assertEqual(dismissals[0]["reason"], "decommissioned")
        with self.assertRaises(ValueError):
            fp.append_dismissal(path, "service down", "down.example",
                                "443", "")

    def test_first_reason_wins_on_duplicate_signature(self):
        mapping = fp.build_dismissal_map([
            {"category": "service down", "host": "down.example",
             "key": "443", "reason": "first"},
            {"category": "service down", "host": "down.example",
             "key": "443", "reason": "second"}])
        self.assertEqual(mapping[("service down", "down.example", "443")],
                         "first")


if __name__ == "__main__":
    unittest.main()
