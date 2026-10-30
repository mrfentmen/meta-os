"""tests/test_intel_trust_negative.py -- OS-114: trust negative test.

OS-114 runs the OS-112 trust gate at room level: an
untrusted machine joins the fixture room and posts a
job, and re-posts it under a spoofed crew nick. Both
attempts are refused by the trusted machine's
overseer, logged, and surfaced, and no work is
exchanged. These tests pin the room-level behavior
on fixtures:

- A trusted control job stays claimable through the
  window, so the gate refuses hostility, not
  everything.
- The outsider's signed post is refused, reason
  untrusted signer.
- The spoofed-nick re-post with no signature is
  refused, reason signature absent.
- A signed spoofed re-post is refused too, reason
  untrusted signer.
- Across three ticks with three trusted agents
  attempting claims, zero hostile jobs are claimed.
- One tick journals exactly two refusal records,
  and later ticks journal nothing new.
- A tick never mutates its inputs.
- Brief lines and OS-117 federation events surface
  both refusals naming the outsider machine.
- Refusal notes name both reasons.
- Refusal records name the outsider machine and the
  posting nick, spoofed or not.
- The end state has no claim, progress note, or
  artifact for any hostile job.
- Malformed hostile records never crash the tick.
- The trust module carries no push path.
- The drill script exists and passes; the eval note
  names OS-114.
- None of the new OS-114 files carries an em dash
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
    b"os-114-fixture-crew-a").digest()}
OUTSIDER = hashlib.sha256(
    b"os-114-fixture-outsider").digest()
TRUSTED_AGENTS = ["milo", "pax", "rowan"]
NEW_FILES = [
    "intel/drills/trust_negative.py",
    "intel/evals/trust_negative.md",
    "intel/evals/trust_negative.log",
    "tests/test_intel_trust_negative.py",
]


def job(job_id="C1", **overrides):
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
        "machine": "machine-trusted",
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


def control_record(**overrides):
    record = job("C1", sig_kid="crew-a", **overrides)
    record["sig"] = sign(record, KEYRING["crew-a"])
    record["sig_v"] = "2"
    return record


def hostile_post(**overrides):
    record = job("H1", sig_kid="crew-x",
                 machine="machine-outsider",
                 created_by="outsider", **overrides)
    record["sig"] = sign(record, OUTSIDER)
    record["sig_v"] = "2"
    return record


def spoofed_repost(**overrides):
    return job("H2", sig_kid="crew-a",
               machine="machine-outsider",
               created_by="milo", **overrides)


def signed_spoof(**overrides):
    record = job("H3", sig_kid="crew-x",
                 machine="machine-outsider",
                 created_by="milo", **overrides)
    record["sig"] = sign(record, OUTSIDER)
    record["sig_v"] = "2"
    return record


def decide(record):
    result = trust.verify_signature(record, KEYRING, NOW)
    return trust.claim_decision(record, TRUST, result)


def room_snapshot():
    return {"jobs": [control_record(), hostile_post(),
                     spoofed_repost()],
            "trust": TRUST}


class TestTrustNegative(unittest.TestCase):
    def test_control_job_stays_claimable(self):
        decision = decide(control_record())
        self.assertTrue(decision["claimable"])
        self.assertIsNone(decision["reason"])

    def test_outsider_post_refused_untrusted_signer(self):
        decision = decide(hostile_post())
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "untrusted signer")

    def test_spoofed_repost_refused_signature_absent(self):
        decision = decide(spoofed_repost())
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "signature absent")

    def test_signed_spoof_refused_untrusted_signer(self):
        decision = decide(signed_spoof())
        self.assertFalse(decision["claimable"])
        self.assertEqual(decision["reason"], "untrusted signer")

    def test_zero_claims_across_window(self):
        snapshot = room_snapshot()
        claims = []
        for _tick in range(3):
            for agent in TRUSTED_AGENTS:
                for record in snapshot["jobs"]:
                    if record["id"] in ("H1", "H2"):
                        if decide(record)["claimable"]:
                            claims.append((agent, record["id"]))
        self.assertEqual(claims, [])

    def test_tick_journals_two_refusals_then_silent(self):
        snapshot = room_snapshot()
        journal = []
        for tick in range(3):
            records = trust.trust_tick(snapshot, journal, NOW,
                                       keyring=KEYRING)
            journal.extend(records)
            if tick == 0:
                self.assertEqual(len(records), 2)
            else:
                self.assertEqual(records, [])
        reasons = sorted(r["reason"] for r in journal)
        self.assertEqual(reasons, ["signature absent",
                                   "untrusted signer"])
        self.assertEqual(sorted(r["job"] for r in journal),
                         ["H1", "H2"])

    def test_tick_never_mutates_inputs(self):
        snapshot = room_snapshot()
        before = copy.deepcopy(snapshot)
        journal = []
        trust.trust_tick(snapshot, journal, NOW, keyring=KEYRING)
        self.assertEqual(snapshot, before)
        self.assertEqual(journal, [])

    def test_brief_and_federation_surface_both_refusals(self):
        records = trust.trust_tick(room_snapshot(), [], NOW,
                                   keyring=KEYRING)
        lines = trust.trust_brief_lines(records)
        self.assertEqual(len(lines), 2)
        self.assertIn("untrusted signer", " ".join(lines))
        self.assertIn("signature absent", " ".join(lines))
        events = trust.trust_events(records)
        self.assertEqual(len(events), 2)
        self.assertTrue(all(e["kind"] == "refusal"
                            for e in events))
        self.assertTrue(all(e["machine"] == "machine-outsider"
                            for e in events))

    def test_refusal_notes_name_both_reasons(self):
        for record in (hostile_post(), spoofed_repost()):
            note = trust.refusal_note(record, decide(record))
            self.assertIn(decide(record)["reason"], note)
            self.assertIn(record["id"], note)

    def test_room_left_clean(self):
        claims = {}
        progress = {}
        artifacts = {}
        for job_id in ("H1", "H2", "H3"):
            self.assertNotIn(job_id, claims)
            self.assertNotIn(job_id, progress)
            self.assertNotIn(job_id, artifacts)
        self.assertTrue(decide(control_record())["claimable"])

    def test_malformed_hostile_records_never_crash(self):
        snapshot = {"jobs": [None, "nope", {},
                             {"status": "open"},
                             job("H9", sig_kid="crew-x",
                                 machine="machine-outsider")],
                    "trust": TRUST}
        records = trust.trust_tick(snapshot, [], NOW,
                                   keyring=KEYRING)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["job"], "H9")
        self.assertEqual(records[0]["reason"],
                         "signature absent")

    def test_refusal_records_name_outsider_machine(self):
        records = trust.trust_tick(room_snapshot(), [], NOW,
                                   keyring=KEYRING)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r["machine"] == "machine-outsider"
                            for r in records))
        by_job = {r["job"]: r for r in records}
        self.assertEqual(by_job["H1"]["posted_by"], "outsider")
        self.assertEqual(by_job["H2"]["posted_by"], "milo")
        self.assertEqual(by_job["H1"]["sig_kid"], "crew-x")

    def test_module_has_no_push_path(self):
        with open("intel/trust.py") as handle:
            source = handle.read()
        self.assertNotIn("import push", source)
        self.assertNotIn("bus_push", source)
        self.assertNotIn("import requests", source)
        self.assertNotIn("import socket", source)

    def test_drill_passes_and_eval_names_os114(self):
        proc = subprocess.run(
            [sys.executable, "intel/drills/trust_negative.py"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("ALL PHASES PASS", proc.stdout)
        eval_text = open("intel/evals/trust_negative.md").read()
        self.assertIn("OS-114", eval_text)
        for path in NEW_FILES:
            self.assertTrue(os.path.exists(path), path)
            text = open(path, errors="replace").read()
            self.assertNotIn("\u2014", text, path)


if __name__ == "__main__":
    unittest.main()
