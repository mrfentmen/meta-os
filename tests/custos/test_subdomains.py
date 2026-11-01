"""Subdomain exposure sweep tests for META CUSTOS (RW-005).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The sweep enumerates subdomains of watched domains from the CT
entries fetched this patrol, resolves each one, and compares its
addresses against that domain's configured expected networks. This
is a state check, not an event: unlike the certificate-issued
record, the sweep re-grades the enumerated set every patrol. It
never resolves a name CT did not return for a watched domain, and
it never changes DNS or the host.

Claims pinned here:

  * a subdomain resolving inside its domain's expected networks
    is baseline normal;
  * a subdomain with any address outside its expected networks
    becomes a "subdomain unexpected network" record (yellow tier,
    zero escalation) carrying the unexpected addresses;
  * an unresolvable subdomain is an error in the summary, never
    data, and the patrol still completes;
  * a domain with no expected networks configured is not graded
    and its names are never resolved;
  * wildcard patterns, the bare domain, unrelated domains, and
    duplicates never reach the resolver;
  * the ct_since floor bounds enumeration the same way it bounds
    certificate-issued records;
  * a malformed expected network is a summary error for that
    domain only and grades nothing for it;
  * the sweep re-grades on a later patrol even when the CT ids
    are already in the seen-state.
"""

import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T06:00:00Z"

GOOD_ENTRY = {
    "id": 1,
    "common_name": "good.example.org",
    "name_value": "good.example.org",
    "issuer_name": "Test CA",
    "not_before": "2026-06-01T00:00:00",
    "not_after": "2026-09-01T00:00:00",
}

BAD_ENTRY = {
    "id": 2,
    "common_name": "bad.example.org",
    "name_value": "bad.example.org",
    "issuer_name": "Test CA",
    "not_before": "2026-06-01T00:00:00",
    "not_after": "2026-09-01T00:00:00",
}


def sub_config(entries, networks=None, since=""):
    config = {
        "hosts": [],
        "inventory": [],
        "ct_domains": ["example.org"],
        "ct_since": since,
        "subdomain_expected_networks": networks
        if networks is not None else {"example.org": ["203.0.113.0/24"]},
    }
    fetch = lambda _domain, _template: list(entries)  # noqa: E731
    return config, fetch


def no_network(_host, _port):
    raise AssertionError("no host probes expected in a subdomain patrol")


# The DNS step falls back to ct_domains, so subdomain tests pin it
# with a fixed snapshot: first sighting is a silent baseline, and
# no test ever touches the real resolver.
def fake_dns(_domain):
    return {"A": ["203.0.113.1"], "AAAA": [], "MX": [], "TXT": []}


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def subdomain_records(records):
    return [r for r in observations(records) if r["source"] == "subdomain"]


def run_sub(config, fetch, resolver):
    return patrol.run_patrol(
        config, NOW, lambda _url: [], no_network, no_network,
        fetch_ct_fn=fetch, fetch_dns_fn=fake_dns,
        resolve_subdomain_fn=resolver)


class TestSubdomainSweep(unittest.TestCase):
    def test_in_network_subdomain_is_baseline_normal(self):
        config, fetch = sub_config([GOOD_ENTRY])
        records, _s, _c = run_sub(
            config, fetch, lambda name: ["203.0.113.7"])
        recs = subdomain_records(records)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["host"], "good.example.org")
        self.assertEqual(rec["category"], "baseline normal")
        self.assertEqual(rec["tier"], "none")
        self.assertEqual(rec["detail"]["parent_domain"], "example.org")
        self.assertEqual(rec["detail"]["addresses"], ["203.0.113.7"])
        self.assertEqual(rec["detail"]["unexpected_addresses"], [])
        self.assertEqual(records[-1]["subdomains_checked"], 1)

    def test_out_of_network_subdomain_is_yellow_with_unexpected_list(self):
        config, fetch = sub_config([BAD_ENTRY])
        records, _s, _c = run_sub(
            config, fetch, lambda name: ["198.51.100.9"])
        recs = subdomain_records(records)
        self.assertEqual(len(recs), 1)
        rec = recs[0]
        self.assertEqual(rec["category"], "subdomain unexpected network")
        self.assertEqual(rec["tier"], "yellow")
        self.assertEqual(rec["detail"]["addresses"], ["198.51.100.9"])
        self.assertEqual(rec["detail"]["unexpected_addresses"],
                         ["198.51.100.9"])
        self.assertEqual(rec["detail"]["expected_networks"],
                         ["203.0.113.0/24"])
        # Yellow means zero escalation calls for this category.
        self.assertNotIn(
            "subdomain unexpected network",
            {r["for_category"] for r in records
             if r["record_type"] == "escalation"})

    def test_mixed_addresses_flag_only_the_outsiders(self):
        config, fetch = sub_config([GOOD_ENTRY])
        records, _s, _c = run_sub(
            config, fetch,
            lambda name: ["198.51.100.9", "203.0.113.7"])
        rec = subdomain_records(records)[0]
        self.assertEqual(rec["category"], "subdomain unexpected network")
        self.assertEqual(rec["detail"]["addresses"],
                         ["198.51.100.9", "203.0.113.7"])
        self.assertEqual(rec["detail"]["unexpected_addresses"],
                         ["198.51.100.9"])

    def test_unresolvable_subdomain_is_error_not_data(self):
        config, fetch = sub_config([GOOD_ENTRY])

        def broken(_name):
            raise OSError("DNS unreachable")

        records, _s, _c = run_sub(config, fetch, broken)
        self.assertEqual(subdomain_records(records), [])
        summary = records[-1]
        self.assertEqual(summary["record_type"], "patrol-summary")
        self.assertTrue(any("subdomain resolve failed for good.example.org"
                            in e for e in summary["errors"]))
        self.assertEqual(summary["subdomains_checked"], 1)

    def test_empty_resolution_is_error_not_baseline(self):
        config, fetch = sub_config([GOOD_ENTRY])
        records, _s, _c = run_sub(config, fetch, lambda _name: [])
        self.assertEqual(subdomain_records(records), [])
        summary = records[-1]
        self.assertTrue(any("no addresses for good.example.org" in e
                            for e in summary["errors"]))

    def test_domain_without_expected_networks_is_never_resolved(self):
        config, fetch = sub_config([GOOD_ENTRY], networks={})

        def must_not_run(_name):
            raise AssertionError("resolver must not run without networks")

        records, _s, _c = run_sub(config, fetch, must_not_run)
        self.assertEqual(subdomain_records(records), [])
        self.assertEqual(records[-1]["subdomains_checked"], 0)
        self.assertEqual(records[-1]["errors"], [])

    def test_wildcards_bare_and_foreign_names_never_reach_resolver(self):
        entries = [{
            "id": 3,
            "common_name": "*.example.org",
            "name_value": "*.example.org\nexample.org\n"
                           "other.example.net good.example.org\n"
                           "GOOD.example.org",
            "not_before": "2026-06-01T00:00:00",
        }]
        config, fetch = sub_config(entries)
        seen_names = []

        def counting(name):
            seen_names.append(name)
            return ["203.0.113.7"]

        records, _s, _c = run_sub(config, fetch, counting)
        # Only the one distinct concrete subdomain, lowercased.
        self.assertEqual(seen_names, ["good.example.org"])
        self.assertEqual(len(subdomain_records(records)), 1)

    def test_ct_since_floor_bounds_enumeration(self):
        old = dict(GOOD_ENTRY, id=9, not_before="2020-01-01T00:00:00")
        config, fetch = sub_config([old], since="2026-01-01")

        def must_not_run(_name):
            raise AssertionError("old entries must not be enumerated")

        records, _s, _c = run_sub(config, fetch, must_not_run)
        self.assertEqual(subdomain_records(records), [])
        self.assertEqual(records[-1]["subdomains_checked"], 0)

    def test_malformed_network_is_domain_only_error(self):
        entries = [GOOD_ENTRY,
                   dict(BAD_ENTRY, common_name="bad.other.org",
                        name_value="bad.other.org")]
        config = {
            "hosts": [],
            "inventory": [],
            "ct_domains": ["example.org", "other.org"],
            "ct_since": "",
            "subdomain_expected_networks": {
                "example.org": ["not-a-network"],
                "other.org": ["203.0.113.0/24"],
            },
        }
        fetch = lambda _domain, _template: list(entries)  # noqa: E731
        records, _s, _c = run_sub(
            config, fetch, lambda name: ["198.51.100.9"])
        # The bad-network domain graded nothing; the good domain
        # still flagged its out-of-network subdomain.
        self.assertEqual([r["host"] for r in subdomain_records(records)],
                         ["bad.other.org"])
        summary = records[-1]
        self.assertTrue(any("subdomain networks invalid for example.org"
                            in e for e in summary["errors"]))

    def test_sweep_regrades_on_later_patrol_despite_seen_ct(self):
        config, fetch = sub_config([BAD_ENTRY])
        resolver = lambda name: ["198.51.100.9"]  # noqa: E731
        _r1, _s1, seen_ct = run_sub(config, fetch, resolver)
        records, _s2, _c2 = patrol.run_patrol(
            config, NOW, lambda _url: [], no_network, no_network,
            fetch_ct_fn=fetch, seen_ct=seen_ct,
            fetch_dns_fn=fake_dns, resolve_subdomain_fn=resolver)
        # The CT event is deduped (no second certificate-issued
        # record), but the subdomain state check runs again.
        self.assertEqual([r for r in observations(records)
                          if r["source"] == "ct"], [])
        self.assertEqual(len(subdomain_records(records)), 1)
        self.assertEqual(subdomain_records(records)[0]["category"],
                         "subdomain unexpected network")

    def test_pure_helpers(self):
        self.assertEqual(patrol.tier_for("subdomain unexpected network"),
                         "yellow")
        self.assertEqual(
            patrol.extract_subdomains(
                [{"common_name": "",
                  "name_value": "a.example.org b.example.org",
                  "not_before": "2026-06-01T00:00:00"}],
                "example.org"),
            ["a.example.org", "b.example.org"])
        networks = patrol.parse_expected_networks(["203.0.113.0/24",
                                                   "198.51.100.9"])
        self.assertEqual(patrol.classify_subdomain(["203.0.113.7"],
                                                   networks),
                         ("baseline normal", []))
        self.assertEqual(patrol.classify_subdomain(["198.51.100.9"],
                                                   networks),
                         ("baseline normal", []))
        self.assertEqual(patrol.classify_subdomain(["192.0.2.1"],
                                                   networks),
                         ("subdomain unexpected network", ["192.0.2.1"]))
        # An unparseable address cannot be shown inside an expected
        # network, so it counts unexpected.
        self.assertEqual(patrol.classify_subdomain(["not-an-ip"],
                                                   networks),
                         ("subdomain unexpected network", ["not-an-ip"]))
        with self.assertRaises(ValueError):
            patrol.parse_expected_networks(["not-a-network"])


if __name__ == "__main__":
    unittest.main()
