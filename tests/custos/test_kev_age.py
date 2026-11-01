"""RW-006 KEV ageing priority tests for META CUSTOS.

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

Pinned on injected feed shapes — no network, no live hosts:

  * matched CVEs are recorded oldest listing first, regardless of
    feed order, with undated entries last;
  * days_since_listing is whole days from dateAdded to the patrol
    time, None for an unparseable or missing date, never negative;
  * a match listed more than kev_age_red_days ago (default 30) is
    flagged aged; exactly 30 days is not aged, 31 days is;
  * aged matches stay red (the existing KEV contract is unchanged:
    ageing orders the queue, it never downgrades a young match);
  * the patrol summary counts aged matches;
  * the threshold is configurable per installation.
"""

import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os", "worlds", "custos", "runtime"))

import patrol  # noqa: E402

NOW = "2026-11-01T03:00:00Z"

# Feed order is deliberately scrambled: young first, oldest in the
# middle, undated and bad-date at the end.
KEV_FEED = [
    {"cveID": "CVE-2024-1002", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2026-10-20"},  # 12 days: young
    {"cveID": "CVE-2024-1005", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2024-01-01"},  # oldest: aged
    {"cveID": "CVE-2024-1003", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2026-10-02"},  # 30 days: boundary
    {"cveID": "CVE-2024-1004", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "2026-10-01"},  # 31 days: aged
    {"cveID": "CVE-2024-1006", "vendorProject": "OpenSSL",
     "product": "OpenSSL"},  # undated: recorded, unaged, last
    {"cveID": "CVE-2024-1007", "vendorProject": "OpenSSL",
     "product": "OpenSSL", "dateAdded": "not a date"},  # bad date: same
]


def fake_config():
    return {
        "hosts": [
            {"host": "up.example", "port": 443, "expected_ports": [443]},
        ],
        "inventory": ["openssl"],
        "cert_warn_days": 21,
        "sensitive_ports": [22, 3306],
    }


def fake_fetch(_url):
    return list(KEV_FEED)


def fake_cert(host, _port):
    return {"up.example": 100}.get(host)


def fake_headers(_host, _port):
    return {h: "present" for h in patrol.SECURITY_HEADERS}


def fake_port_factory(open_map):
    def probe(host, port):
        return open_map.get((host, port), False)
    return probe


def observations(records):
    return [r for r in records if r["record_type"] == "observation"]


def kev_records(records):
    return [r for r in observations(records) if r["source"] == "kev"]


class TestKevAgeDays(unittest.TestCase):
    def test_whole_days_from_date_added(self):
        self.assertEqual(
            patrol.kev_age_days({"dateAdded": "2026-10-01"}, NOW), 31)
        self.assertEqual(
            patrol.kev_age_days({"dateAdded": "2026-10-02"}, NOW), 30)
        self.assertEqual(
            patrol.kev_age_days({"dateAdded": "2026-11-01"}, NOW), 0)

    def test_iso_timestamp_reads_its_date_part(self):
        self.assertEqual(
            patrol.kev_age_days({"dateAdded": "2026-10-15T00:00:00Z"},
                                NOW), 17)

    def test_unparseable_or_missing_date_is_none(self):
        self.assertIsNone(patrol.kev_age_days({"dateAdded": "junk"}, NOW))
        self.assertIsNone(patrol.kev_age_days({"dateAdded": ""}, NOW))
        self.assertIsNone(patrol.kev_age_days({}, NOW))
        self.assertIsNone(patrol.kev_age_days({"dateAdded": None}, NOW))

    def test_future_date_reads_as_zero_never_negative(self):
        self.assertEqual(
            patrol.kev_age_days({"dateAdded": "2027-01-01"}, NOW), 0)


class TestKevAgeSort(unittest.TestCase):
    def test_oldest_first_undated_last_deterministic(self):
        matched = patrol.match_kev(KEV_FEED, ["openssl"])
        ordered = [e["cveID"] for e, _ in
                   patrol.sort_kev_by_age(matched, NOW)]
        self.assertEqual(ordered, [
            "CVE-2024-1005",  # 2024-01-01, oldest
            "CVE-2024-1004",  # 31 days
            "CVE-2024-1003",  # 30 days
            "CVE-2024-1002",  # 12 days
            "CVE-2024-1006",  # undated, by CVE id
            "CVE-2024-1007",  # bad date, by CVE id
        ])


class TestKevAgePatrol(unittest.TestCase):
    def run_fake(self, config=None):
        records, _seen, _ct = patrol.run_patrol(
            config or fake_config(), NOW, fake_fetch, fake_cert,
            fake_port_factory({("up.example", 443): True}),
            fetch_headers_fn=fake_headers)
        return records

    def test_records_oldest_first_with_age_and_aged_flag(self):
        records = self.run_fake()
        kev = kev_records(records)
        self.assertEqual([r["detail"]["cve"] for r in kev], [
            "CVE-2024-1005", "CVE-2024-1004", "CVE-2024-1003",
            "CVE-2024-1002", "CVE-2024-1006", "CVE-2024-1007"])
        by_cve = {r["detail"]["cve"]: r["detail"] for r in kev}
        self.assertGreater(by_cve["CVE-2024-1005"]["days_since_listing"],
                           30)
        self.assertEqual(by_cve["CVE-2024-1004"]["days_since_listing"], 31)
        self.assertEqual(by_cve["CVE-2024-1003"]["days_since_listing"], 30)
        self.assertEqual(by_cve["CVE-2024-1002"]["days_since_listing"], 12)
        self.assertIsNone(by_cve["CVE-2024-1006"]["days_since_listing"])
        self.assertIsNone(by_cve["CVE-2024-1007"]["days_since_listing"])
        self.assertEqual(
            {c: by_cve[c]["aged"] for c in by_cve},
            {"CVE-2024-1005": True, "CVE-2024-1004": True,
             "CVE-2024-1003": False, "CVE-2024-1002": False,
             "CVE-2024-1006": False, "CVE-2024-1007": False})

    def test_aged_matches_stay_red_and_summary_counts_them(self):
        records = self.run_fake()
        kev = kev_records(records)
        for r in kev:
            self.assertEqual(r["category"],
                             "known-exploited vulnerability present")
            self.assertEqual(r["tier"], "red")
        summary = records[-1]
        self.assertEqual(summary["kev_aged_over_threshold"], 2)
        esc = [r for r in records if r["record_type"] == "escalation"]
        self.assertEqual(
            sum(1 for e in esc
                if e["for_category"] ==
                "known-exploited vulnerability present"), 6)

    def test_threshold_is_configurable(self):
        config = fake_config()
        config["kev_age_red_days"] = 10
        records = self.run_fake(config)
        kev = kev_records(records)
        by_cve = {r["detail"]["cve"]: r["detail"] for r in kev}
        self.assertTrue(by_cve["CVE-2024-1002"]["aged"])  # 12 > 10
        self.assertFalse(by_cve["CVE-2024-1006"]["aged"])  # undated
        self.assertEqual(records[-1]["kev_aged_over_threshold"], 4)


if __name__ == "__main__":
    unittest.main()
