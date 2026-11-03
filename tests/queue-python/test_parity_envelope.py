"""CB2-344/345 — the Python side of the shared parity fixtures.

The envelope fixture is the same file `crates/parity-tests/tests/parity_fixtures.rs`
reads, and the incident record is the real live reading the queue files. If the
two sides drift, one of the two tests fails on bytes it did not write.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
QUEUE = os.path.join(ROOT, "server", "queue")
sys.path.insert(0, QUEUE)

import crew_common  # noqa: E402
import queue_service  # noqa: E402
import record_validate  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "parity", "envelope.json")
# The v2 record the staged Imperium run produced, extracted byte-for-byte from
# the brief step of os-build/logs/R5-imperium/incident.json.
INCIDENT = os.path.join(ROOT, "tests", "fixtures", "parity", "incident.json")

PRODUCT = "vigiles"
TIMESTAMP = "2026-11-02T00:00:00Z"
FRAME = b"\xff\xd8\xff\xe0PARITY-FRAME"


class EnvelopeParityTest(unittest.TestCase):
    def test_fixture_is_exactly_what_the_builder_writes(self):
        with open(FIXTURE, encoding="utf-8") as f:
            fixture = json.load(f)
        built = crew_common.build_job_envelope(PRODUCT, TIMESTAMP, FRAME)
        self.assertEqual(fixture, built, "the committed fixture matches the builder")

    def test_fixture_validates_in_the_queue_service(self):
        with open(FIXTURE, encoding="utf-8") as f:
            fixture = json.load(f)
        self.assertIsNone(queue_service.validate_envelope(fixture))
        self.assertIsNone(crew_common.envelope_error(fixture))

        # A changed byte length is refused, so the fixture is not passing by default.
        broken = json.loads(json.dumps(fixture))
        broken["image"]["byteLength"] += 1
        self.assertIsNotNone(queue_service.validate_envelope(broken))


class IncidentParityTest(unittest.TestCase):
    def test_live_reading_carries_the_contract_key_set(self):
        with open(INCIDENT, encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(
            sorted(record), sorted(record_validate.REQUIRED_KEYS),
            "the real record carries exactly the five contract keys")
        self.assertTrue(
            set(record["observations"][0]) <= set(record_validate.OBSERVATION_KEYS),
            "every observation field is in the contract (region is optional)")
        for key in ("category", "description", "confidence"):
            self.assertIn(key, record["observations"][0])
        self.assertEqual(record_validate.validate_v2_incident(record), [])


if __name__ == "__main__":
    unittest.main()
