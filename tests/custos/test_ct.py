"""Certificate Transparency watcher tests for META CUSTOS (RW-001).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The fixture entry below is a REAL crt.sh response entry, captured
2026-11-01 from https://crt.sh/?q=%25.letsencrypt.org&output=json
(the radiantlock.letsencrypt.org certificate, id 1485147627). The
multi-entry case reuses that entry's schema with synthetic ids,
labelled as such in the test, because a second real entry would
only duplicate the same fields.

Claims pinned here:

  * a newly issued cert for a watched domain becomes a
    "certificate issued" record (yellow tier, zero escalation);
  * ct_since bounds a first patrol: older certs are skipped;
  * a cert id already in the seen-state is never re-recorded;
  * a CT fetch failure is an error in the summary, never data.
"""

import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T04:00:00Z"

# Real crt.sh entry, captured 2026-11-01 (see module docstring).
REAL_ENTRY = {
    "issuer_ca_id": 16418,
    "issuer_name": "C=US, O=Let's Encrypt, CN=Let's Encrypt Authority X3",
    "common_name": "radiantlock.letsencrypt.org",
    "name_value": "radiantlock.letsencrypt.org",
    "id": 1485147627,
    "not_before": "2019-05-12T21:42:32",
    "not_after": "2019-08-10T21:42:32",
    "serial_number": "0313e984aa6b184b7fcc9fcd54ed5df8f1bf",
    "result_count": 2,
}


def ct_config(since="2019-01-01"):
    return {
        "hosts": [],
        "inventory": [],
        "ct_domains": ["letsencrypt.org"],
        "ct_since": since,
    }


def no_network(_host, _port):
    raise AssertionError("no host probes expected in a CT-only patrol")


class TestCT(unittest.TestCase):
    def test_new_cert_becomes_yellow_record(self):
        fetch = lambda _domain, _template: [REAL_ENTRY]
        records, _seen, seen_ct = patrol.run_patrol(
            ct_config(), NOW, lambda _url: [], no_network, no_network,
            fetch_ct_fn=fetch)
        ct_records = [r for r in records
                      if r["record_type"] == "observation"
                      and r["source"] == "ct"]
        self.assertEqual(len(ct_records), 1)
        rec = ct_records[0]
        self.assertEqual(rec["category"], "certificate issued")
        self.assertEqual(rec["tier"], "yellow")
        self.assertEqual(rec["host"], "letsencrypt.org")
        self.assertEqual(rec["detail"]["ct_id"], 1485147627)
        self.assertEqual(rec["detail"]["common_name"],
                         "radiantlock.letsencrypt.org")
        # Yellow means zero escalation calls, pinned here.
        self.assertEqual([r for r in records
                          if r["record_type"] == "escalation"], [])
        self.assertIn(1485147627, seen_ct)

    def test_ct_since_bounds_first_patrol(self):
        fetch = lambda _domain, _template: [REAL_ENTRY]
        records, _seen, _ct = patrol.run_patrol(
            ct_config(since="2020-01-01"), NOW, lambda _url: [],
            no_network, no_network, fetch_ct_fn=fetch)
        ct_records = [r for r in records
                      if r["record_type"] == "observation"
                      and r["source"] == "ct"]
        self.assertEqual(ct_records, [])

    def test_seen_cert_never_re_recorded(self):
        fetch = lambda _domain, _template: [REAL_ENTRY]
        _r1, _s1, seen_ct = patrol.run_patrol(
            ct_config(), NOW, lambda _url: [], no_network, no_network,
            fetch_ct_fn=fetch)
        records, _s2, _ct2 = patrol.run_patrol(
            ct_config(), NOW, lambda _url: [], no_network, no_network,
            fetch_ct_fn=fetch, seen_ct=seen_ct)
        ct_records = [r for r in records
                      if r["record_type"] == "observation"
                      and r["source"] == "ct"]
        self.assertEqual(ct_records, [])

    def test_ct_fetch_failure_is_error_not_data(self):
        def broken(_domain, _template):
            raise OSError("ct log unreachable")
        records, _s, _c = patrol.run_patrol(
            ct_config(), NOW, lambda _url: [], no_network, no_network,
            fetch_ct_fn=broken)
        self.assertEqual([r for r in records
                          if r["record_type"] == "observation"
                          and r["source"] == "ct"], [])
        summary = records[-1]
        self.assertEqual(len(summary["errors"]), 1)
        self.assertIn("ct fetch failed", summary["errors"][0])
        # The patrol still completed with a summary, not a crash.
        self.assertEqual(summary["record_type"], "patrol-summary")


if __name__ == "__main__":
    unittest.main()
