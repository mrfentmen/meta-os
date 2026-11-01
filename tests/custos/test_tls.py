"""TLS configuration grader tests for META CUSTOS (RW-002).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

All postures below are injected: the development machine has no
direct network path to watched hosts (a raw TLS handshake from
here dies in the middlebox), so the grader is pinned on recorded
posture shapes, exactly like the certificate and liveness probes.
The real probe (patrol.probe_tls) is one handshake returning the
version and cipher the host actually negotiated; grading is pure.

Claims pinned here:

  * a negotiated version below the stated baseline minimum is a
    "tls configuration drift" record (yellow tier, zero
    escalation);
  * a negotiated cipher matching a forbidden substring is drift,
    whatever the version;
  * a posture meeting the baseline is a "baseline normal" record
    carrying the version and cipher it was graded on;
  * an unrecognized version string grades as drift with its
    reason stated, never as a silent pass;
  * a failed TLS probe is an error in the summary, never data,
    never a patrol crash.
"""

import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T05:00:00Z"

BASELINE = {"min_version": "TLSv1.2",
            "forbidden_ciphers": ["RC4", "3DES", "DES", "NULL",
                                  "EXPORT", "MD5", "RC2"]}

STRONG = {"version": "TLSv1.3", "cipher": "TLS_AES_256_GCM_SHA384"}
GOOD_12 = {"version": "TLSv1.2",
           "cipher": "ECDHE-RSA-AES256-GCM-SHA384"}
OLD_VERSION = {"version": "TLSv1.1", "cipher": "ECDHE-RSA-AES256-SHA"}
WEAK_CIPHER = {"version": "TLSv1.2", "cipher": "RC4-SHA"}
WEAK_CIPHER_LOWER = {"version": "TLSv1.2", "cipher": "rc4-md5"}
UNKNOWN_VERSION = {"version": "TLSv9.9", "cipher": "TLS_AES_256_GCM_SHA384"}


def tls_config(hosts, baseline=None):
    config = {
        "hosts": [{"host": h, "port": 443, "expected_ports": [443]}
                  for h in hosts],
        "inventory": [],
    }
    if baseline is not None:
        config["tls_baseline"] = baseline
    return config


def no_network(_host, _port):
    raise AssertionError("no host probes expected beyond the injected TLS probe")


class TestGradeTls(unittest.TestCase):
    def test_strong_posture_is_baseline_normal(self):
        category, reason = patrol.grade_tls(STRONG, BASELINE)
        self.assertEqual(category, "baseline normal")
        self.assertEqual(reason, "meets baseline")

    def test_good_tls12_is_baseline_normal(self):
        category, _reason = patrol.grade_tls(GOOD_12, BASELINE)
        self.assertEqual(category, "baseline normal")

    def test_old_version_is_drift(self):
        category, reason = patrol.grade_tls(OLD_VERSION, BASELINE)
        self.assertEqual(category, "tls configuration drift")
        self.assertIn("TLSv1.1", reason)
        self.assertIn("TLSv1.2", reason)

    def test_weak_cipher_is_drift_despite_good_version(self):
        category, reason = patrol.grade_tls(WEAK_CIPHER, BASELINE)
        self.assertEqual(category, "tls configuration drift")
        self.assertIn("RC4-SHA", reason)
        self.assertIn("RC4", reason)

    def test_forbidden_match_is_case_insensitive(self):
        category, _reason = patrol.grade_tls(WEAK_CIPHER_LOWER, BASELINE)
        self.assertEqual(category, "tls configuration drift")

    def test_stricter_baseline_drifts_tls12(self):
        strict = dict(BASELINE, min_version="TLSv1.3")
        category, reason = patrol.grade_tls(GOOD_12, strict)
        self.assertEqual(category, "tls configuration drift")
        self.assertIn("TLSv1.3", reason)

    def test_unknown_version_is_drift_not_silent_pass(self):
        category, reason = patrol.grade_tls(UNKNOWN_VERSION, BASELINE)
        self.assertEqual(category, "tls configuration drift")
        self.assertIn("unrecognized", reason)

    def test_missing_baseline_uses_default(self):
        category, _reason = patrol.grade_tls(OLD_VERSION, None)
        self.assertEqual(category, "tls configuration drift")
        category, _reason = patrol.grade_tls(GOOD_12, None)
        self.assertEqual(category, "baseline normal")

    def test_version_rank_order(self):
        ranks = patrol.TLS_VERSION_RANK
        self.assertLess(ranks["TLSv1.1"], ranks["TLSv1.2"])
        self.assertLess(ranks["TLSv1.2"], ranks["TLSv1.3"])
        self.assertLess(ranks["SSLv3"], ranks["TLSv1.0"])


class TestTlsInPatrol(unittest.TestCase):
    def _run(self, postures, hosts, baseline=None):
        def probe_tls(host, _port):
            return postures.get(host)
        records, _seen, _ct = patrol.run_patrol(
            tls_config(hosts, baseline), NOW, lambda _url: [],
            lambda _host, _port: 365, lambda _host, _port: True,
            probe_tls_fn=probe_tls)
        return records

    def _tls_records(self, records):
        return [r for r in records
                if r["record_type"] == "observation"
                and r["source"] == "tls"]

    def test_drift_host_becomes_yellow_record_zero_escalation(self):
        records = self._run({"a.example": OLD_VERSION}, ["a.example"],
                            BASELINE)
        tls = self._tls_records(records)
        self.assertEqual(len(tls), 1)
        self.assertEqual(tls[0]["category"], "tls configuration drift")
        self.assertEqual(tls[0]["tier"], "yellow")
        self.assertEqual(tls[0]["host"], "a.example")
        self.assertEqual(tls[0]["detail"]["version"], "TLSv1.1")
        self.assertEqual(tls[0]["detail"]["cipher"],
                         "ECDHE-RSA-AES256-SHA")
        self.assertEqual(tls[0]["detail"]["baseline_min_version"],
                         "TLSv1.2")
        # Yellow means zero escalation calls, pinned here.
        self.assertEqual([r for r in records
                          if r["record_type"] == "escalation"], [])

    def test_good_host_records_posture_as_baseline_normal(self):
        records = self._run({"a.example": STRONG}, ["a.example"], BASELINE)
        tls = self._tls_records(records)
        self.assertEqual(len(tls), 1)
        self.assertEqual(tls[0]["category"], "baseline normal")
        self.assertEqual(tls[0]["detail"]["version"], "TLSv1.3")
        self.assertEqual(tls[0]["detail"]["cipher"],
                         "TLS_AES_256_GCM_SHA384")
        self.assertEqual(tls[0]["detail"]["grade_reason"],
                         "meets baseline")

    def test_failed_probe_is_summary_error_never_data(self):
        records = self._run({}, ["a.example"], BASELINE)
        self.assertEqual(self._tls_records(records), [])
        summary = records[-1]
        self.assertEqual(summary["record_type"], "patrol-summary")
        self.assertIn("tls probe failed for a.example:443",
                      summary["errors"])
        self.assertEqual([r for r in records
                          if r["record_type"] == "escalation"], [])

    def test_summary_counts_tls_drift(self):
        records = self._run({"a.example": WEAK_CIPHER,
                             "b.example": STRONG},
                            ["a.example", "b.example"], BASELINE)
        summary = records[-1]
        self.assertEqual(summary["observations"]["tls configuration drift"],
                         1)
        self.assertEqual(summary["observations"]["baseline normal"], 5)
        # Service + cert baselines for both hosts, plus a tls
        # baseline for the good host; the drift host's tls record
        # lands in the drift count instead.

    def test_service_down_host_gets_no_tls_record(self):
        records, _seen, _ct = patrol.run_patrol(
            tls_config(["a.example"], BASELINE), NOW, lambda _url: [],
            lambda _host, _port: 365, lambda _host, _port: False,
            probe_tls_fn=lambda _h, _p: STRONG)
        self.assertEqual(self._tls_records(records), [])


if __name__ == "__main__":
    unittest.main()
