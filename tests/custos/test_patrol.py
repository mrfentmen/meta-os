"""Patrol-loop tests for META CUSTOS.

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The patrol's classification core is pinned on injected signals
(recorded feed shapes, fixed probe answers) — no network, no live
hosts. The claims pinned here are the pack's safety claims:

  * certificate states fall on the right side of the tier boundary;
  * the KEV match is against the configured inventory, and a matched
    CVE is never re-alerted on a later patrol;
  * yellow observations produce ZERO escalation records;
  * red observations escalate only to the labelled SIMULATED endpoint;
  * a feed that cannot be fetched is an error in the summary, never
    data.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T03:00:00Z"

KEV_FEED = [
    {"cveID": "CVE-2024-0001", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2024-05-01"},
    {"cveID": "CVE-2024-0002", "vendorProject": "Acme",
     "product": "Widget", "dateAdded": "2024-05-02"},
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
    return {"up.example": 10}.get(host)  # 10 days left: expiring


def fake_port_factory(open_map):
    def probe(host, port):
        return open_map.get((host, port), False)
    return probe


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def escalations(records):
    return [r for r in records if r["record_type"] == "escalation"]


class TestClassify(unittest.TestCase):
    def test_certificate_boundaries(self):
        self.assertEqual(patrol.classify_certificate(-1, 21),
                         "certificate expired")
        self.assertEqual(patrol.classify_certificate(0, 21),
                         "certificate expiring")
        self.assertEqual(patrol.classify_certificate(21, 21),
                         "certificate expiring")
        self.assertEqual(patrol.classify_certificate(22, 21),
                         "baseline normal")

    def test_tier_mapping(self):
        self.assertEqual(patrol.tier_for("baseline normal"), "none")
        self.assertEqual(patrol.tier_for("certificate expiring"), "yellow")
        self.assertEqual(patrol.tier_for("anomalous exposure"), "yellow")
        self.assertEqual(patrol.tier_for("certificate expired"), "red")
        self.assertEqual(
            patrol.tier_for("known-exploited vulnerability present"), "red")
        self.assertEqual(patrol.tier_for("service down"), "red")

    def test_kev_matching_is_inventory_against_feed_text(self):
        matched = patrol.match_kev(KEV_FEED, ["openssl"])
        self.assertEqual([e["cveID"] for e, _ in matched], ["CVE-2024-0001"])
        self.assertEqual(patrol.match_kev(KEV_FEED, ["nginx"]), [])
        matched = patrol.match_kev(KEV_FEED, ["ACME WIDGET"])
        self.assertEqual([e["cveID"] for e, _ in matched], ["CVE-2024-0002"])

    def test_exposure_classification(self):
        self.assertEqual(patrol.classify_exposure([22, 443], [443], 443),
                         [22])
        self.assertEqual(patrol.classify_exposure([443], [443], 443), [])
        self.assertEqual(patrol.classify_exposure([22], [22, 443], 443), [])


class TestCertExpiryParsing(unittest.TestCase):
    def test_space_padded_and_zero_padded_days(self):
        # getpeercert pads single-digit days with a space, not a zero.
        self.assertEqual(
            patrol.parse_cert_expiry("Nov  1 00:00:00 2027 GMT"),
            datetime(2027, 11, 1, tzinfo=timezone.utc))
        self.assertEqual(
            patrol.parse_cert_expiry("Nov 01 00:00:00 2027 GMT"),
            datetime(2027, 11, 1, tzinfo=timezone.utc))

    def test_unparseable_date_is_none_never_an_exception(self):
        self.assertIsNone(patrol.parse_cert_expiry("not a date"))
        self.assertIsNone(patrol.parse_cert_expiry(""))
        self.assertIsNone(patrol.parse_cert_expiry(None))


class TestPatrol(unittest.TestCase):
    def run_fake(self, open_map, fetch=fake_fetch, seen=None):
        return patrol.run_patrol(fake_config(), NOW, fetch, fake_cert,
                                 fake_port_factory(open_map), seen)

    def test_full_patrol_categories_tiers_and_escalations(self):
        open_map = {("up.example", 443): True}
        records, seen = self.run_fake(open_map)
        obs = observations(records)
        cats = {(r["host"], r["category"]) for r in obs}
        self.assertIn((None, "known-exploited vulnerability present"), cats)
        self.assertIn(("up.example", "baseline normal"), cats)
        self.assertIn(("up.example", "certificate expiring"), cats)
        self.assertIn(("down.example", "service down"), cats)
        # Red: the KEV match and the down service. Yellow (the expiring
        # certificate) must produce ZERO escalation records.
        esc = escalations(records)
        self.assertEqual(len(esc), 2)
        self.assertEqual({e["for_category"] for e in esc},
                         {"known-exploited vulnerability present",
                          "service down"})
        for e in esc:
            self.assertEqual(e["endpoint"], "SIMULATED")
        self.assertIn("CVE-2024-0001", seen)
        summary = records[-1]
        self.assertEqual(summary["record_type"], "patrol-summary")
        self.assertEqual(summary["escalations"], 2)
        self.assertEqual(summary["errors"], [])

    def test_kev_dedupe_across_patrols(self):
        open_map = {("up.example", 443): True}
        _records, seen = self.run_fake(open_map)
        records2, _seen2 = self.run_fake(open_map, seen=seen)
        kev_records = [r for r in observations(records2)
                       if r["source"] == "kev"]
        self.assertEqual(kev_records, [])

    def test_anomalous_exposure_is_yellow_and_never_escalates(self):
        open_map = {("up.example", 443): True, ("up.example", 22): True}
        records, _seen = self.run_fake(open_map)
        exposure = [r for r in observations(records)
                    if r["category"] == "anomalous exposure"]
        self.assertEqual(len(exposure), 1)
        self.assertEqual(exposure[0]["tier"], "yellow")
        self.assertEqual(exposure[0]["detail"]["port"], 22)
        esc_cats = {e["for_category"] for e in escalations(records)}
        self.assertNotIn("anomalous exposure", esc_cats)

    def test_declared_sensitive_port_is_not_anomalous(self):
        config = fake_config()
        config["hosts"][0]["expected_ports"] = [443, 22]
        open_map = {("up.example", 443): True, ("up.example", 22): True}
        records, _seen = patrol.run_patrol(
            config, NOW, fake_fetch, fake_cert,
            fake_port_factory(open_map))
        self.assertEqual([r for r in observations(records)
                          if r["category"] == "anomalous exposure"], [])

    def test_cert_probe_failure_is_an_error_not_data(self):
        def no_cert(_host, _port):
            return None
        records, _seen = patrol.run_patrol(
            fake_config(), NOW, fake_fetch, no_cert,
            fake_port_factory({("up.example", 443): True}))
        self.assertEqual([r for r in observations(records)
                          if r["source"] == "cert"], [])
        summary = records[-1]
        self.assertIn("cert probe failed for up.example:443",
                      summary["errors"])
        # The liveness baseline still recorded; the failure did not
        # stop the patrol.
        self.assertTrue(any(r["host"] == "up.example" and
                            r["category"] == "baseline normal"
                            for r in observations(records)))

    def test_feed_failure_is_an_error_not_data(self):
        def broken_fetch(_url):
            raise OSError("feed unreachable")
        records, _seen = self.run_fake({("up.example", 443): True},
                                       fetch=broken_fetch)
        self.assertEqual([r for r in observations(records)
                          if r["source"] == "kev"], [])
        summary = records[-1]
        self.assertEqual(len(summary["errors"]), 1)
        self.assertIn("kev fetch failed", summary["errors"][0])
        # Host checks still ran: the failure did not stop the patrol.
        self.assertTrue(any(r["host"] == "down.example"
                            for r in observations(records)))


if __name__ == "__main__":
    unittest.main()
