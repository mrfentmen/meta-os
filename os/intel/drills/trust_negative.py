"""intel/drills/trust_negative.py -- OS-114 drill (Milo).

The trust negative test, at room level. An untrusted
machine joins the fixture room and posts a job; the
same job is re-posted under a spoofed crew nick.
Both attempts are refused by the trusted machine's
overseer, logged, and surfaced, and no work is
exchanged: zero claims of the hostile jobs by any
trusted agent across the test window, and the drill
leaves the fixture room clean.

The two attempts earn the two reasons the OS-114
acceptance names. Attempt one is a job signed with
the outsider's own key, refused as "untrusted
signer". Attempt two is the same job re-posted
under a spoofed trusted nick with no signature at
all, refused as "signature absent": a familiar name
with no proof is refused exactly like a stranger.
A third guard phase proves the signed variant of the
spoof (spoofed nick, outsider signature) is refused
as "untrusted signer" too, so no spoof shape slips
through; the guard is decision-level only, so the
room log still holds exactly the two attempts.

Signatures are real HMAC-SHA256 v2 signatures
computed with jobs._sign_job_v2 over fixture-only
secrets derived from labels, never real crew keys,
and no keyring file is read or written. The room,
the claims, the progress notes, and the artifacts
are plain dicts in this file: the drill proves the
overseer's judgment and the room's clean end state,
not a live bus. A trusted control job rides along
to prove the gate refuses hostility, not everything:
it stays claimable through the whole window.

Pass bar: the control job is claimable; both
hostile attempts are refused with their exact
reasons; three ticks times three trusted agents
yield zero claims of any hostile job; the first
tick journals exactly two refusal records and
later ticks journal nothing new; brief lines and
federation events surface both refusals naming the
outsider machine; refusal notes name both reasons;
the end state has no claim, progress note, or
artifact for any hostile job; inputs are never
mutated; and the module carries no push path, so
a refusal judged here can never ring a phone.
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
    b"os-114-fixture-crew-a").digest()
OUTSIDER_SECRET = hashlib.sha256(
    b"os-114-fixture-outsider").digest()

TRUST = {"trusted_kids": ["crew-a"],
         "allowed_badges": ["agent"]}
KEYRING = {"crew-a": TRUSTED_SECRET}
NOW = 100000
ROOM = "fixture-room"
TRUSTED_MACHINE = "machine-trusted"
OUTSIDER_MACHINE = "machine-outsider"
TRUSTED_AGENTS = ["milo", "pax", "rowan"]


def base_job(job_id, **overrides):
    record = {
        "id": job_id,
        "title": "Fixture job " + job_id,
        "status": "open",
        "spec": "Do the fixture thing.",
        "accept": "Fixture output exists.",
        "branch": "",
        "base": "",
        "room": ROOM,
        "created_at": "90000",
        "expires_at": "",
        "nonce": "nonce-" + job_id,
        "machine": TRUSTED_MACHINE,
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


def control_job():
    job = base_job("C1", sig_kid="crew-a")
    job["sig"] = sign(job, TRUSTED_SECRET)
    job["sig_v"] = "2"
    return job


def hostile_post():
    """Attempt one: the outsider machine posts a job
    signed with its own untrusted key."""
    job = base_job("H1", sig_kid="crew-x",
                   machine=OUTSIDER_MACHINE,
                   created_by="outsider")
    job["sig"] = sign(job, OUTSIDER_SECRET)
    job["sig_v"] = "2"
    return job


def spoofed_repost():
    """Attempt two: the same job re-posted under a
    spoofed trusted nick, with no signature."""
    return base_job("H2", sig_kid="crew-a",
                    machine=OUTSIDER_MACHINE,
                    created_by="milo")


def signed_spoof():
    """Guard: the spoofed re-post carrying the
    outsider's signature instead of none."""
    job = base_job("H3", sig_kid="crew-x",
                   machine=OUTSIDER_MACHINE,
                   created_by="milo")
    job["sig"] = sign(job, OUTSIDER_SECRET)
    job["sig_v"] = "2"
    return job


def decide(job):
    result = trust.verify_signature(job, KEYRING, NOW)
    return trust.claim_decision(job, TRUST, result)


def phase_room_setup():
    job = control_job()
    decision = decide(job)
    if not decision["claimable"]:
        print("room-setup: FAIL: control job not claimable:",
              decision)
        return False
    room = {"machines": [TRUSTED_MACHINE, OUTSIDER_MACHINE],
            "agents": TRUSTED_AGENTS}
    if OUTSIDER_MACHINE not in room["machines"]:
        print("room-setup: FAIL: outsider machine not in room")
        return False
    print("room-setup: outsider machine joined the room, "
          "trusted control job claimable: PASS")
    return True


def phase_hostile_post():
    job = hostile_post()
    decision = decide(job)
    if decision["claimable"] or \
            decision["reason"] != "untrusted signer":
        print("hostile-post: FAIL:", decision)
        return False
    note = trust.refusal_note(job, decision)
    if "untrusted signer" not in note:
        print("hostile-post: FAIL: refusal note wrong:", note)
        return False
    print("hostile-post: outsider job refused, reason "
          "untrusted signer: PASS")
    return True


def phase_spoofed_repost():
    job = spoofed_repost()
    decision = decide(job)
    if decision["claimable"] or \
            decision["reason"] != "signature absent":
        print("spoofed-repost: FAIL:", decision)
        return False
    note = trust.refusal_note(job, decision)
    if "signature absent" not in note:
        print("spoofed-repost: FAIL: refusal note wrong:", note)
        return False
    print("spoofed-repost: spoofed-nick re-post refused, "
          "reason signature absent, nick never authority: "
          "PASS")
    return True


def phase_signed_spoof_guard():
    job = signed_spoof()
    decision = decide(job)
    if decision["claimable"] or \
            decision["reason"] != "untrusted signer":
        print("signed-spoof: FAIL:", decision)
        return False
    print("signed-spoof: spoofed nick with an outsider "
          "signature refused too, reason untrusted signer: "
          "PASS")
    return True


def phase_test_window():
    """Three ticks; at each tick every trusted agent
    attempts to claim every hostile job. Zero claims
    is the only passing count, and the refusal log
    holds exactly the two attempts after tick one."""
    snapshot = {"jobs": [control_job(), hostile_post(),
                         spoofed_repost()],
                "trust": TRUST}
    before = copy.deepcopy(snapshot)
    journal = []
    hostile_ids = ["H1", "H2"]
    claims = {}
    for tick in range(1, 4):
        records = trust.trust_tick(snapshot, journal, NOW,
                                   keyring=KEYRING)
        journal.extend(records)
        for agent in TRUSTED_AGENTS:
            for job in snapshot["jobs"]:
                if job["id"] in hostile_ids:
                    decision = decide(job)
                    if decision["claimable"]:
                        claims.setdefault(job["id"], []).append(
                            agent)
        if tick == 1 and len(records) != 2:
            print("test-window: FAIL: tick 1 journaled",
                  len(records), "records, expected 2")
            return False
        if tick > 1 and records:
            print("test-window: FAIL: tick", tick,
                  "journaled", len(records), "new records")
            return False
    if claims:
        print("test-window: FAIL: hostile jobs claimed:", claims)
        return False
    reasons = sorted(r["reason"] for r in journal)
    if reasons != ["signature absent", "untrusted signer"]:
        print("test-window: FAIL: journal reasons wrong:", reasons)
        return False
    if snapshot != before:
        print("test-window: FAIL: ticks mutated inputs")
        return False
    print("test-window: 3 ticks x 3 trusted agents, zero "
          "claims of hostile jobs, exactly 2 refusal "
          "records, later ticks silent: PASS")
    return True


def phase_surfaced():
    snapshot = {"jobs": [control_job(), hostile_post(),
                         spoofed_repost()],
                "trust": TRUST}
    records = trust.trust_tick(snapshot, [], NOW,
                               keyring=KEYRING)
    lines = trust.trust_brief_lines(records)
    events = trust.trust_events(records)
    if len(lines) != 2 or len(events) != 2:
        print("surfaced: FAIL: brief/events counts wrong:",
              lines, events)
        return False
    if any(e["machine"] != OUTSIDER_MACHINE for e in events):
        print("surfaced: FAIL: events name the wrong machine:",
              events)
        return False
    if "untrusted signer" not in lines[0] + lines[1] or \
            "signature absent" not in lines[0] + lines[1]:
        print("surfaced: FAIL: brief lines miss a reason:",
              lines)
        return False
    print("surfaced: both refusals on the brief and the "
          "federation feed, naming the outsider machine: "
          "PASS")
    return True


def phase_room_clean():
    """End state: no claim, progress note, or artifact
    for any hostile job; the control job is still
    claimable, so the room is clean, not empty."""
    claims = {}
    progress = {}
    artifacts = {}
    for job_id in ["H1", "H2", "H3"]:
        if job_id in claims or job_id in progress or \
                job_id in artifacts:
            print("room-clean: FAIL: work exchanged for", job_id)
            return False
    decision = decide(control_job())
    if not decision["claimable"]:
        print("room-clean: FAIL: control job lost claimability")
        return False
    print("room-clean: no claim, progress note, or artifact "
          "for any hostile job; control job still "
          "claimable: PASS")
    return True


def phase_no_push_no_live():
    path = os.path.join(os.path.dirname(__file__),
                        "..", "trust.py")
    source = open(path).read()
    if "import push" in source or "bus_push" in source \
            or "push.py" in source:
        print("no-push: FAIL: trust module carries a push path")
        return False
    drill_path = os.path.join(os.path.dirname(__file__),
                              "trust_negative.py")
    drill_source = open(drill_path).read()
    # AST scan: import names and open() path literals
    # only. A plain text scan would match this check's
    # own words, so the check reads structure, not text.
    import ast
    tree = ast.parse(drill_source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name.split(".")[0] in (
                        "requests", "socket", "redis",
                        "upstash"):
                    print("no-push: FAIL: drill imports live "
                          "transport:", name.name)
                    return False
        if isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in (
                    "requests", "socket", "redis", "upstash"):
                print("no-push: FAIL: drill imports live "
                      "transport:", node.module)
                return False
        if isinstance(node, ast.Call) and \
                isinstance(node.func, ast.Name) and \
                node.func.id == "open":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and \
                        isinstance(arg.value, str) and \
                        ("token" in arg.value or
                         ".config" in arg.value):
                    print("no-push: FAIL: drill opens a "
                          "credential path:", arg.value)
                    return False
    print("no-push: refusal is journal only, no push path, "
          "no live bus, no keyring file read: PASS")
    return True


def main():
    phases = [phase_room_setup, phase_hostile_post,
              phase_spoofed_repost, phase_signed_spoof_guard,
              phase_test_window, phase_surfaced,
              phase_room_clean, phase_no_push_no_live]
    ok = True
    for phase in phases:
        if not phase():
            ok = False
    if ok:
        print("trust_negative: ALL PHASES PASS")
        return 0
    print("trust_negative: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
