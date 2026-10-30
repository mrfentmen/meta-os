"""intel/drills/trust_enforcement.py -- OS-112 drill (Milo).

A fixture room with a trusted crew job, an unsigned
job, an untrusted-kid job, a transplanted-signature
job, an expired job, a legacy v1 job, and a job
posted under a spoofed crew nick. Signatures are
real HMAC-SHA256 v2 signatures computed with
jobs._sign_job_v2 over fixture-only secrets derived
from labels, never real crew keys, and no keyring
file is read or written.

Pass bar: the trusted job is claimable with its
over-claimed badge dropped and named; every other
job is refused with the exact reason its case earns;
a tick journals one refusal record per refused job
and nothing for the trusted job; a second tick
journals nothing new; inputs are never mutated;
and the module carries no push path, so a refusal
judged here can never ring a phone on its own.
"""

import copy
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", ".."))

import jobs  # noqa: E402
from intel import trust  # noqa: E402

# Fixture-only secrets, derived from labels, not
# stored as literals: these are test keys, never real
# crew keys, and they never leave this drill file.
TRUSTED_SECRET = hashlib.sha256(
    b"os-112-fixture-crew-a").digest()
UNTRUSTED_SECRET = hashlib.sha256(
    b"os-112-fixture-outsider").digest()

TRUST = {"trusted_kids": ["crew-a"],
         "allowed_badges": ["agent"]}
KEYRING = {"crew-a": TRUSTED_SECRET}
NOW = 100000


def base_job(job_id, **overrides):
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


def sign(job, secret):
    fields = {k: job[k] for k in
              ("title", "accept", "branch", "base", "room",
               "created_at", "expires_at", "nonce")}
    return jobs._sign_job_v2(secret, job["id"],
                             job["sig_kid"], fields,
                             job["spec"])


def trusted_job():
    job = base_job("1", sig_kid="crew-a",
                   badge_claims=["agent", "driver"])
    job["sig"] = sign(job, TRUSTED_SECRET)
    job["sig_v"] = "2"
    return job


def phase_trusted():
    job = trusted_job()
    result = trust.verify_signature(job, KEYRING, NOW)
    decision = trust.claim_decision(job, TRUST, result)
    if result != "OK" or not decision["claimable"]:
        print("trusted: FAIL: trusted v2 job not claimable:",
              result, decision)
        return False
    if decision["allowed_badges"] != ["agent"] or \
            decision["dropped_badges"] != ["driver"]:
        print("trusted: FAIL: badge clamp wrong:", decision)
        return False
    print("trusted: trusted v2 job claimable, driver badge "
          "dropped and named: PASS")
    return True


def phase_unsigned():
    job = base_job("2", sig_kid="crew-a")
    decision = trust.claim_decision(job, TRUST, "UNSIGNED")
    if decision["claimable"] or \
            decision["reason"] != "signature absent":
        print("unsigned: FAIL:", decision)
        return False
    print("unsigned: refused, reason signature absent: PASS")
    return True


def phase_untrusted():
    job = base_job("3", sig_kid="crew-x")
    job["sig"] = sign(job, UNTRUSTED_SECRET)
    job["sig_v"] = "2"
    result = trust.verify_signature(job, KEYRING, NOW)
    decision = trust.claim_decision(job, TRUST, result)
    if decision["claimable"] or \
            decision["reason"] != "untrusted signer":
        print("untrusted: FAIL:", result, decision)
        return False
    print("untrusted: correctly signed by an untrusted kid "
          "refused, reason untrusted signer: PASS")
    return True


def phase_transplant():
    donor = base_job("9", sig_kid="crew-a")
    donor["sig"] = sign(donor, TRUSTED_SECRET)
    job = base_job("10", sig_kid="crew-a")
    job["sig"] = donor["sig"]
    job["sig_v"] = "2"
    result = trust.verify_signature(job, KEYRING, NOW)
    decision = trust.claim_decision(job, TRUST, result)
    if result != "BAD" or decision["claimable"] or \
            decision["reason"] != "signature bad":
        print("transplant: FAIL:", result, decision)
        return False
    print("transplant: signature lifted from job 9 refused "
          "on job 10, reason signature bad: PASS")
    return True


def phase_expired():
    job = base_job("4", sig_kid="crew-a",
                   expires_at="99999")
    job["sig"] = sign(job, TRUSTED_SECRET)
    job["sig_v"] = "2"
    result = trust.verify_signature(job, KEYRING, NOW)
    decision = trust.claim_decision(job, TRUST, result)
    if result != "EXPIRED" or decision["claimable"] or \
            decision["reason"] != "signature expired":
        print("expired: FAIL:", result, decision)
        return False
    print("expired: refused, reason signature expired: PASS")
    return True


def phase_legacy():
    job = base_job("5", sig_kid="crew-a", sig="deadbeef",
                   sig_v="1")
    decision = trust.claim_decision(job, TRUST, "OK")
    if decision["claimable"] or decision["reason"] != \
            "legacy v1 signature, v2 required":
        print("legacy: FAIL:", decision)
        return False
    print("legacy: v1 job refused, reason legacy v1 "
          "signature, v2 required: PASS")
    return True


def phase_spoofed_nick():
    job = base_job("6", sig_kid="crew-x",
                   created_by="milo")
    job["sig"] = sign(job, UNTRUSTED_SECRET)
    job["sig_v"] = "2"
    result = trust.verify_signature(job, KEYRING, NOW)
    decision = trust.claim_decision(job, TRUST, result)
    if decision["claimable"] or \
            decision["reason"] != "untrusted signer":
        print("spoofed-nick: FAIL:", result, decision)
        return False
    print("spoofed-nick: familiar nick, untrusted signature "
          "refused: PASS")
    return True


def phase_tick():
    jobs_list = [trusted_job(),
                 base_job("2", sig_kid="crew-a"),
                 base_job("3", sig_kid="crew-x")]
    jobs_list[2]["sig"] = sign(jobs_list[2], UNTRUSTED_SECRET)
    jobs_list[2]["sig_v"] = "2"
    snapshot = {"jobs": jobs_list, "trust": TRUST}
    before = copy.deepcopy(snapshot)
    records = trust.trust_tick(snapshot, [], NOW,
                               keyring=KEYRING)
    if len(records) != 2:
        print("tick: FAIL: expected 2 refusal records, got",
              len(records))
        return False
    reasons = sorted(r["reason"] for r in records)
    if reasons != ["signature absent", "untrusted signer"]:
        print("tick: FAIL: reasons wrong:", reasons)
        return False
    second = trust.trust_tick(snapshot, records, NOW,
                              keyring=KEYRING)
    if second:
        print("tick: FAIL: second tick journaled", len(second))
        return False
    if snapshot != before:
        print("tick: FAIL: tick mutated its inputs")
        return False
    real = trust.claim_decision(jobs_list[1], TRUST, "UNSIGNED")
    note = trust.refusal_note(jobs_list[1], real)
    if note is None or "signature absent" not in note:
        print("tick: FAIL: refusal note wrong:", note)
        return False
    lines = trust.trust_brief_lines(records)
    events = trust.trust_events(records)
    if len(lines) != 2 or len(events) != 2 or \
            events[0]["kind"] != "refusal":
        print("tick: FAIL: brief/events wrong:", lines, events)
        return False
    print("tick: 2 refusal records, trusted job silent, "
          "second tick silent, inputs immutable, brief "
          "and federation events render: PASS")
    return True


def phase_no_push():
    path = os.path.join(os.path.dirname(__file__),
                        "..", "trust.py")
    source = open(path).read()
    if "import push" in source or "bus_push" in source \
            or "push.py" in source:
        print("no-push: FAIL: trust module carries a push path")
        return False
    print("no-push: refusal is journal only, no push path, "
          "Dale contacted at no step: PASS")
    return True


def main():
    phases = [phase_trusted, phase_unsigned,
              phase_untrusted, phase_transplant,
              phase_expired, phase_legacy,
              phase_spoofed_nick, phase_tick,
              phase_no_push]
    ok = True
    for phase in phases:
        if not phase():
            ok = False
    if ok:
        print("trust_enforcement: ALL PHASES PASS")
        return 0
    print("trust_enforcement: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
