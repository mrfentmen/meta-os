"""DNS drift watcher tests for META CUSTOS (RW-003).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The snapshots below are synthetic, labelled as such: DNS answers
are the patrol's input shape, not captured traffic, and the point
pinned here is the diff logic, not any real domain's records.

Claims pinned here:

  * a first sighting only establishes the baseline: it stores the
    snapshot and writes no record;
  * an unchanged snapshot writes no record;
  * a changed snapshot becomes one "dns drift" record (yellow tier,
    zero escalation) carrying the added/removed diff per type;
  * a DNS fetch failure is an error in the summary, never data,
    and leaves the baseline untouched;
  * dns_domains falls back to ct_domains when absent;
  * the seen-state round-trips the DNS baseline, and a pre-DNS
    state file (no seen_dns key) loads as an empty baseline.
"""

import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T05:00:00Z"
DOMAIN = "example.org"

BASE = {
    "A": ["93.184.216.34"],
    "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
    "MX": ["10 mail.example.org."],
    "TXT": ['"v=spf1 -all"'],
}
CHANGED = {
    "A": ["93.184.216.35"],
    "AAAA": ["2606:2800:220:1:248:1893:25c8:1946"],
    "MX": ["10 mail.example.org.", "20 backup.example.org."],
    "TXT": ['"v=spf1 -all"'],
}


def dns_config(domains=None, ct_domains=None):
    config = {"hosts": [], "inventory": []}
    if domains is not None:
        config["dns_domains"] = domains
    if ct_domains is not None:
        config["ct_domains"] = ct_domains
    return config


def no_network(_host, _port):
    raise AssertionError("no host probes expected in a DNS-only patrol")


def run(config, fetch, seen_dns=None):
    return patrol.run_patrol(
        config, NOW, lambda _url: [], no_network, no_network,
        fetch_dns_fn=fetch, seen_dns=seen_dns)


def dns_records(records):
    return [r for r in records
            if r["record_type"] == "observation"
            and r["source"] == "dns"]


class TestDNSDrift(unittest.TestCase):
    def test_first_sighting_stores_silently(self):
        seen_dns = {}
        records, _seen, _seen_ct = run(
            dns_config([DOMAIN]), lambda _d: dict(BASE), seen_dns)
        self.assertEqual(dns_records(records), [])
        self.assertEqual(seen_dns[DOMAIN], patrol.normalize_snapshot(BASE))

    def test_unchanged_snapshot_writes_no_record(self):
        seen_dns = {DOMAIN: patrol.normalize_snapshot(BASE)}
        records, _seen, _seen_ct = run(
            dns_config([DOMAIN]), lambda _d: dict(BASE), seen_dns)
        self.assertEqual(dns_records(records), [])
        summary = records[-1]
        self.assertEqual(summary["dns_domains_checked"], 1)
        self.assertEqual(summary["observations"]["dns drift"], 0)

    def test_changed_snapshot_becomes_yellow_record_with_diff(self):
        seen_dns = {DOMAIN: patrol.normalize_snapshot(BASE)}
        records, _seen, _seen_ct = run(
            dns_config([DOMAIN]), lambda _d: dict(CHANGED), seen_dns)
        found = dns_records(records)
        self.assertEqual(len(found), 1)
        rec = found[0]
        self.assertEqual(rec["category"], "dns drift")
        self.assertEqual(rec["tier"], "yellow")
        self.assertEqual(rec["host"], DOMAIN)
        self.assertEqual(rec["detail"]["added"],
                         {"A": ["93.184.216.35"],
                          "MX": ["20 backup.example.org"]})
        self.assertEqual(rec["detail"]["removed"],
                         {"A": ["93.184.216.34"]})
        # Yellow means zero escalation calls, pinned here.
        self.assertEqual([r for r in records
                          if r["record_type"] == "escalation"], [])
        # The baseline advances to the new snapshot.
        self.assertEqual(seen_dns[DOMAIN],
                         patrol.normalize_snapshot(CHANGED))

    def test_removal_only_is_still_a_record(self):
        before = dict(CHANGED)
        after = dict(CHANGED)
        after["MX"] = ["10 mail.example.org."]
        seen_dns = {DOMAIN: patrol.normalize_snapshot(before)}
        records, _seen, _seen_ct = run(
            dns_config([DOMAIN]), lambda _d: dict(after), seen_dns)
        found = dns_records(records)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["detail"]["added"], {})
        self.assertEqual(found[0]["detail"]["removed"],
                         {"MX": ["20 backup.example.org"]})

    def test_fetch_failure_is_summary_error_not_data(self):
        before = patrol.normalize_snapshot(BASE)
        seen_dns = {DOMAIN: dict(before)}

        def failing(_domain):
            raise RuntimeError("resolver down")

        records, _seen, _seen_ct = run(
            dns_config([DOMAIN]), failing, seen_dns)
        self.assertEqual(dns_records(records), [])
        self.assertEqual(records[-1]["errors"],
                         ["dns fetch failed for %s: resolver down" % DOMAIN])
        self.assertEqual(seen_dns[DOMAIN], before)

    def test_dns_domains_fall_back_to_ct_domains(self):
        seen_dns = {}
        records, _seen, _seen_ct = run(
            dns_config(ct_domains=[DOMAIN]), lambda _d: dict(BASE),
            seen_dns)
        self.assertEqual(dns_records(records), [])
        self.assertIn(DOMAIN, seen_dns)

    def test_normalize_strips_txt_quotes_and_mx_dots(self):
        snapshot = patrol.normalize_snapshot({
            "A": ["93.184.216.34", "93.184.216.34"],
            "MX": ["10 mail.example.org."],
            "TXT": ['"v=spf1 -all"'],
            "CNAME": ["noise.example.org."],
        })
        self.assertEqual(snapshot["A"], ["93.184.216.34"])
        self.assertEqual(snapshot["MX"], ["10 mail.example.org"])
        self.assertEqual(snapshot["TXT"], ["v=spf1 -all"])
        self.assertNotIn("CNAME", snapshot)

    def test_state_roundtrip_keeps_dns_baseline(self):
        seen_dns = {DOMAIN: patrol.normalize_snapshot(BASE)}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "state.json")
            patrol.save_state(path, {"CVE-2024-0001"}, {123},
                              seen_dns)
            seen_cve, seen_ct, loaded = patrol.load_state(path)
        self.assertEqual(seen_cve, {"CVE-2024-0001"})
        self.assertEqual(seen_ct, {123})
        self.assertEqual(loaded, seen_dns)

    def test_pre_dns_state_file_loads_empty_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old-state.json")
            with open(path, "w") as f:
                json.dump({"seen_cve": [], "seen_ct": []}, f)
            _seen_cve, _seen_ct, loaded = patrol.load_state(path)
        self.assertEqual(loaded, {})


if __name__ == "__main__":
    unittest.main()
