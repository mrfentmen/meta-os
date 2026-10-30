"""tests/test_intel_trust.py -- OS-112: signed-job trust enforcement.

OS-112 puts a trust gate in front of every claim: a
job signed by a trusted crew is claimable, and the
same job unsigned, signed by an untrusted key,
carrying a bad, expired, or legacy v1 signature is
refused at claim time, with the refusal logged and
board-visible, never silently skipped. These tests
pin the decision, the tick, the brief and federation
shapes, and the no-push half on fixtures:

- A trusted v2 job is claimable, and its badge
  claims clamp to local policy with dropped badges
  named.
- An unsigned job is refused, reason signature
  absent.
- A correctly signed job from an untrusted kid is
  refused, reason untrusted signer.
- A signature transplanted from another job id is
  refused, reason signature bad.
- An expired signature is refused, reason signature
  expired.
- A legacy v1 signature is refused even when its
  kid is trusted.
- Claimed and done jobs are not judged, and
  malformed records never crash.
- A tick journals one refusal per refused job and
  nothing for a claimable job, and a second tick
  journals nothing new.
- A tick never mutates its inputs.
- The refusal note names the reason and every
  dropped badge.
- Brief lines and OS-117 federation events render
  the refusal, and an event without a machine is
  skipped.
- An unset badge policy passes claims through and
  says so, instead of inventing a policy.
- The trust module carries no push path.
- The drill script exists and passes; the eval note
  names OS-112.
- None of the new OS-112 files carries an em dash
  (the new-doc rule).

No bus post, no live Redis, no network, no systemd:
pure fixture calls plus file reads. Signatures in
these tests are real HMAC-SHA256 v2 signatures over
fixture-only secrets, never real crew keys.
"""

import copy
import hashlib
import os
import subprocess
import sys
import unittest

sys.path.insert(0, ".")

import jobs  # noqa: E402
from intel import trust  # noqa: E402

NOW = 100000
TRUST = {"trusted_kids": ["crew-a"],
         "allowed_badges": ["agent"]}
KEYRING = {"crew-a": hashlib.sha256(
    b"os-112-fixture-crew-a").digest()}
OUTSIDER = hashlib.sha256(
    b"os-112-fixture-outsider").digest()
NEW_FILES = [
    "intel/trust.py",
    "intel/drills/trust_enforcement.py",
    "intel/evals/trust_enforcement.md",
    "intel/evals/trust_enforcement.log",
    "tests/test_intel_trust.py",
]


def job(job_id="1", **overrides):
    record = {
        "id": job_id,
        "title": "Fixture job " + job_id,
        "status": "open",
        "spec": "Do the fixture thing.",
        "accept": "Fixture output exists.",
        "branch": "",
        "base": "",
        "room": "fixture-room",
        "created_at": "90000",
        "expires_at": "",
        "nonce": "nonce-" + job_id,
        "machine": "machine-a",
        "created_by": "pax",
        "badge_claims": ["agent"],
    }
    record.update(overrides)
    return record


def sign(record, secret):
    fields = {k: record[k] for k in
              ("title", "accept", "branch", "base", "room",
               "created_at", "expires_at", "nonce")}
    return jobs._sign_job_v2(secret, record["id"],
                             record["sig_kid"], fields,
                             record["spec"])


def trusted_record(job_id="1", **overrides):
    record = job(job_id, sig_kid="crew-a", **overrides)
    record["sig"] = sign(record, KEYRING["crew-a"])
    record["sig_v"] = "2"
    return record


class TestTrust(unittest.TestCase):
    def test_trusted_v2_claimable_with_badge_clamp(self):
        record = trusted_record(badge_claims=["agent", "driver"])
        decision = trust.claim_decision(
            record, TRUST,
            trust.verify_signature(record, KEYRING, NOW))
        self.assertTrue(decision["claimable"])
        self.assertIsNone(decision["reason"])
        self.assertEqual(decision["allowed_badges"], ["agent"])
        self.assertEqual(decision["dropped_badges"], ["driver"])

    def test_unsigned_refused(self):
        record = job(sig_kid="crew-a")
        decision = trust.claim_decision(record, TRUST, "UNSIGNED")
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "signature absent")

    def test_untrusted_signer_refused(self):
        record = job(sig_kid="crew-x")
        record["sig"] = sign(record, OUTSIDER)
        record["sig_v"] = "2"
        decision = trust.claim_decision(
            record, TRUST,
            trust.verify_signature(record, KEYRING, NOW))
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "untrusted signer")

    def test_transplanted_signature_refused(self):
        donor = trusted_record("9")
        record = job("10", sig_kid="crew-a", sig=donor["sig"],
                     sig_v="2")
        decision = trust.claim_decision(
            record, TRUST,
            trust.verify_signature(record, KEYRING, NOW))
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "signature bad")

    def test_expired_signature_refused(self):
        record = trusted_record(expires_at="99999")
        decision = trust.claim_decision(
            record, TRUST,
            trust.verify_signature(record, KEYRING, NOW))
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "signature expired")

    def test_legacy_v1_refused_even_when_trusted(self):
        record = job(sig_kid="crew-a", sig="deadbeef",
                     sig_v="1")
        decision = trust.claim_decision(record, TRUST, "OK")
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"],
                         "legacy v1 signature, v2 required")

    def test_non_open_and_malformed_never_crash(self):
        self.assertIsNone(trust.claim_decision(
            trusted_record(status="claimed"), TRUST, "OK"))
        self.assertIsNone(trust.claim_decision(
            trusted_record(status="done"), TRUST, "OK"))
        self.assertIsNone(trust.claim_decision(
            {"status": "open"}, TRUST, "OK"))
        self.assertIsNone(trust.claim_decision(
            None, TRUST, "OK"))
        self.assertEqual(trust.trust_tick(
            {"jobs": [None, "nope", {}], "trust": TRUST},
            [], NOW, keyring=KEYRING), [])

    def test_tick_journals_refusals_once(self):
        snapshot = {"jobs": [trusted_record(),
                             job("2", sig_kid="crew-a")],
                    "trust": TRUST}
        records = trust.trust_tick(snapshot, [], NOW,
                                   keyring=KEYRING)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["job"], "2")
        self.assertEqual(records[0]["dedupe_key"],
                         "trust-refusal:2")
        second = trust.trust_tick(snapshot, records, NOW,
                                  keyring=KEYRING)
        self.assertEqual(second, [])

    def test_tick_never_mutates_inputs(self):
        snapshot = {"jobs": [trusted_record(),
                             job("2", sig_kid="crew-a")],
                    "trust": TRUST}
        before = copy.deepcopy(snapshot)
        journal = []
        trust.trust_tick(snapshot, journal, NOW,
                         keyring=KEYRING)
        self.assertEqual(snapshot, before)
        self.assertEqual(journal, [])

    def test_refusal_note_names_reason_and_badges(self):
        record = trusted_record(badge_claims=["agent", "driver"])
        decision = trust.claim_decision(record, TRUST, "OK")
        decision["claimable"] = False
        decision["reason"] = "untrusted signer"
        note = trust.refusal_note(record, decision)
        self.assertIn("untrusted signer", note)
        self.assertIn("driver", note)

    def test_brief_and_federation_events(self):
        record = {"kind": "trust-refusal", "job": "2",
                  "reason": "signature absent",
                  "machine": "machine-a",
                  "dropped_badges": ["driver"]}
        self.assertEqual(trust.trust_brief_lines([record]),
                         ["Trust refusal: job 2 refused: "
                          "signature absent; badges dropped: "
                          "driver"])
        events = trust.trust_events([record])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["kind"], "refusal")
        self.assertEqual(events[0]["machine"], "machine-a")
        self.assertIn("signature absent", events[0]["detail"])
        self.assertEqual(trust.trust_events(
            [{"kind": "trust-refusal", "job": "3",
              "reason": "x", "machine": ""}]), [])

    def test_unset_badge_policy_passes_through(self):
        record = trusted_record(badge_claims=["agent", "driver"])
        decision = trust.claim_decision(
            record, {"trusted_kids": ["crew-a"]},
            trust.verify_signature(record, KEYRING, NOW))
        self.assertTrue(decision["claimable"])
        self.assertEqual(decision["badge_policy"], "unset")
        self.assertEqual(decision["dropped_badges"], [])

    def test_module_has_no_push_path(self):
        with open("intel/trust.py") as handle:
            source = handle.read()
        self.assertNotIn("import push", source)
        self.assertNotIn("bus_push", source)
        self.assertNotIn("import requests", source)
        self.assertNotIn("import socket", source)

    def test_drill_passes_and_eval_names_os112(self):
        proc = subprocess.run(
            [sys.executable, "intel/drills/trust_enforcement.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("ALL PHASES PASS", proc.stdout)
        eval_text = open("intel/evals/trust_enforcement.md").read()
        self.assertIn("OS-112", eval_text)
        for path in NEW_FILES:
            self.assertTrue(os.path.exists(path), path)
            text = open(path, errors="replace").read()
            self.assertNotIn("\u2014", text, path)


if __name__ == "__main__":
    unittest.main()
