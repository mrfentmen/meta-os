"""intel/trust.py -- signed-job trust list enforcement (OS-112, Milo).

Before any local agent may claim a job, the overseer
verifies the job's HMAC-SHA256 v2 signature against
the local trust list. A job signed by a trusted crew
is claimable; the same job unsigned, signed by an
untrusted key, carrying a bad or expired signature,
or carrying a legacy v1 signature is refused at claim
time. The refusal is a logged, board-visible event,
never a silent skip: the tick journals one
trust-refusal record per job, and refusal_note gives
the overseer the exact text to write into the job
record. The posting crew's badge claims are clamped
to local policy in the same decision, and every
dropped badge is named in the record, never dropped
quietly.

The division of labor is exact, and it matches the
ladder and gate modules before it. This module is the
judgment, not the hands: it never moves a claim, never
writes a job record, never posts to the bus, and has
no push path, so a refusal judged here can never ring
a phone on its own. The overseer claims or refuses
from the decision; the watchman surfaces the journal
record on the board and in the brief. A nick is never
authority here: a job posted under a spoofed crew
nick is judged by its signature alone, so a familiar
name with an untrusted signature is refused exactly
like a stranger's.

Trust list shape (a plain dict, loaded by the caller
from the local chmod-600 config; this module reads no
file and holds no secret):

    {"trusted_kids": ["crew-a", "crew-b"],
     "allowed_badges": ["agent", "driver"]}

The keyring is a second plain dict, kid to secret
(bytes or str), loaded by the caller from the same
local config. Secrets never appear in a job record, a
journal record, a brief line, or a test fixture that
ships as anything but an obvious fixture string.

Signature rules, in the order they are checked:

1. A job without an id, or a job that is not a dict,
   yields no decision and no record: an absent subject
   is not a subject to refuse.
2. Only an open job is judged. A claimed or done job
   is already past the claim gate, and a refused job
   stays refused through the dedupe below.
3. No signature on the record means refused, reason
   "signature absent". An unsigned job is not a job
   with a weak signature; it has no signature at all.
4. A signature that is not v2 means refused, reason
   "legacy v1 signature, v2 required". v1 signatures
   are not bound to the job instance, so a captured
   v1 signature could be transplanted onto another
   job; the trust gate does not accept them.
5. A signing kid outside the trust list means refused,
   reason "untrusted signer". The kid check comes
   before the cryptographic check, so a correctly
   signed job from a crew Dale never trusted is still
   refused, and the reason names the trust failure,
   not the cryptography.
6. A v2 signature that does not recompute, or a job
   past its expiry, means refused, reason "signature
   bad" or "signature expired". A v2 signature
   recomputed for a different job id does not verify
   here, because the v2 payload binds the exact job
   id, kid, timestamps, and nonce.

Badge clamping: badge_claims on the job record is
the posting crew's claimed badges. When the trust
list names allowed_badges, the decision keeps exactly
the claims in that list and drops the rest, naming
every dropped badge in the record. When the trust
list carries no allowed_badges key, there is no local
badge policy to clamp against, so claims pass through
unchanged and the decision carries
badge_policy="unset" instead of inventing a policy.
OS-115 (Dale's federation policy ruling) is the
decision that will fill that policy in; until it
lands, an unset policy is reported, not guessed.

Dedupe: trust_tick skips any job whose refusal
record (dedupe_key trust-refusal:<job>) already
appears in the journal, so a refused job stays
refused with one record across ticks, and a second
tick over a refused room journals nothing new.

Usage: verify_signature(job, keyring, now) checks
the cryptography; claim_decision(job, trust,
verify_result) judges claimability; trust_tick
(snapshot, journal, now) journals refusals for the
snapshot's open jobs; refusal_note(job, decision)
renders the job-record text; trust_brief_lines
(records) renders brief lines; trust_events
(records) renders Hana's OS-117 federation
trust-event shape (kind refusal, machine, detail),
so the refusal surfaces on the board and in the
brief through the existing federation section.
"""

import hashlib
import hmac

__all__ = ["verify_signature", "claim_decision",
           "trust_tick", "refusal_note",
           "trust_brief_lines", "trust_events"]


def _text(value):
    """A str for a str value, else None (never a guess)."""
    if isinstance(value, str) and value:
        return value
    return None


def _as_int(value):
    """An int for an int or integer-valued str, else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _secret_bytes(secret):
    if isinstance(secret, bytes):
        return secret
    if isinstance(secret, str):
        return secret.encode("utf-8")
    return None


def _canonical_v2(job):
    """The v2 payload jobs.py signs, rebuilt from a job dict.

    Mirrors jobs._canonical_payload_v2 field for field
    (jid, kid, title, spec, accept, branch, base, room,
    created_at, expires_at, nonce), so a signature
    computed at post time recomputes here only for the
    exact job it was computed for.
    """
    import json

    payload = {
        "jid": str(job.get("id", "")),
        "kid": str(job.get("sig_kid", "")),
        "title": job.get("title", "") or "",
        "spec": job.get("spec", "") or "",
        "accept": job.get("accept", "") or "",
        "branch": job.get("branch", "") or "",
        "base": job.get("base", "") or "",
        "room": job.get("room", "") or "",
        "created_at": str(job.get("created_at", "")),
        "expires_at": str(job.get("expires_at", "")),
        "nonce": str(job.get("nonce", "")),
    }
    return json.dumps(payload, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def verify_signature(job, keyring, now=None):
    """Verify a job dict's v2 signature against a keyring.

    Returns one of 'OK', 'BAD', 'UNSIGNED', 'EXPIRED'.
    A job with no sig field is UNSIGNED. A job whose
    kid is absent from the keyring is BAD: the keyring
    is the local trusted keys, so an unknown kid is a
    signature this machine cannot vouch for. A v1
    signature is BAD here because the trust gate
    requires v2 (claim_decision names the legacy
    reason separately). Expiry is checked against
    `now` when given, else the job's own clock is not
    trusted and an expires_at in the past against a
    missing now reads EXPIRED only when the caller
    passes now; without now, expiry is not judged.
    """
    if not isinstance(job, dict):
        return "BAD"
    sig = job.get("sig")
    if not sig:
        return "UNSIGNED"
    if job.get("sig_v", "1") != "2":
        return "BAD"
    kid = job.get("sig_kid", "")
    if not isinstance(keyring, dict) or kid not in keyring:
        return "BAD"
    secret = _secret_bytes(keyring[kid])
    if secret is None:
        return "BAD"
    expires = _as_int(job.get("expires_at"))
    if expires is not None and now is not None and now > expires:
        return "EXPIRED"
    good = hmac.compare_digest(
        hmac.new(secret, _canonical_v2(job),
                 hashlib.sha256).hexdigest(), sig)
    return "OK" if good else "BAD"


def _badge_lists(job, trust):
    """(allowed, dropped, policy_unset) for a job's claims."""
    claims = job.get("badge_claims")
    if not isinstance(claims, list):
        claims = []
    claims = [c for c in claims
              if isinstance(c, str) and c]
    allowed_badges = trust.get("allowed_badges") \
        if isinstance(trust, dict) else None
    if allowed_badges is None:
        return claims, [], True
    allowed_set = [b for b in allowed_badges
                   if isinstance(b, str)]
    allowed = [c for c in claims if c in allowed_set]
    dropped = [c for c in claims if c not in allowed_set]
    return allowed, dropped, False


def claim_decision(job, trust, verify_result=None):
    """Judge whether a job may be claimed. Returns a dict
    or None for a job that is not judged (malformed, or
    not open). The dict carries claimable, reason
    (None when claimable), sig_kid, allowed_badges,
    dropped_badges, and badge_policy ('set'/'unset').
    """
    if not isinstance(job, dict):
        return None
    if not _text(job.get("id")):
        return None
    if job.get("status") not in (None, "open"):
        return None
    trust = trust if isinstance(trust, dict) else {}
    trusted = trust.get("trusted_kids")
    trusted = [k for k in trusted
               if isinstance(k, str)] \
        if isinstance(trusted, list) else []
    allowed, dropped, policy_unset = _badge_lists(job, trust)
    decision = {
        "job": job["id"],
        "claimable": False,
        "reason": None,
        "sig_kid": job.get("sig_kid", "") or "",
        "allowed_badges": allowed,
        "dropped_badges": dropped,
        "badge_policy": "unset" if policy_unset else "set",
    }
    if not job.get("sig"):
        decision["reason"] = "signature absent"
        return decision
    if job.get("sig_v", "1") != "2":
        decision["reason"] = "legacy v1 signature, v2 required"
        return decision
    kid = job.get("sig_kid", "")
    if kid not in trusted:
        decision["reason"] = "untrusted signer"
        return decision
    if verify_result is None:
        verify_result = "BAD"
    if verify_result == "EXPIRED":
        decision["reason"] = "signature expired"
        return decision
    if verify_result != "OK":
        decision["reason"] = "signature bad"
        return decision
    decision["claimable"] = True
    return decision


def _already_refused(journal, job_id):
    for record in journal or []:
        if isinstance(record, dict) and \
                record.get("dedupe_key") == \
                "trust-refusal:" + str(job_id):
            return True
    return False


def trust_tick(snapshot, journal, now, keyring=None,
               verify_results=None):
    """Journal one trust-refusal record per refused open
    job in the snapshot. snapshot: {"jobs": [...],
    "trust": {...}}. keyring, when given, lets the tick
    verify signatures itself; otherwise verify_results
    maps job id to a verify result, and a job with no
    entry verifies as BAD. Returns the new records
    only; inputs are never mutated. A claimable job
    journals nothing: trust silence is the normal
    case, not a record.
    """
    if not isinstance(snapshot, dict):
        return []
    jobs = snapshot.get("jobs")
    if not isinstance(jobs, list):
        return []
    trust = snapshot.get("trust")
    if not isinstance(trust, dict):
        trust = {}
    verify_results = verify_results \
        if isinstance(verify_results, dict) else {}
    records = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if _already_refused(journal, job.get("id")) or \
                _already_refused(records, job.get("id")):
            continue
        if keyring is not None:
            result = verify_signature(job, keyring, now)
        else:
            result = verify_results.get(job.get("id"), "BAD")
        decision = claim_decision(job, trust, result)
        if decision is None or decision["claimable"]:
            continue
        record = {
            "kind": "trust-refusal",
            "dedupe_key": "trust-refusal:" + str(job["id"]),
            "job": job["id"],
            "title": job.get("title", "") or "",
            "machine": job.get("machine", "") or
            job.get("created_host", "") or "",
            "posted_by": job.get("created_by", "") or "",
            "reason": decision["reason"],
            "sig_kid": decision["sig_kid"],
            "dropped_badges": decision["dropped_badges"],
            "badge_policy": decision["badge_policy"],
            "created_at": now,
        }
        records.append(record)
    return records


def refusal_note(job, decision):
    """The exact text the overseer writes into the job
    record on refusal. Names the reason, the signing
    kid when known, and every dropped badge; says
    plainly when no badge was dropped."""
    if decision is None:
        return None
    title = job.get("title", "") if isinstance(job, dict) \
        else ""
    parts = ["Refused at claim time: " + decision["reason"] + "."]
    if decision.get("sig_kid"):
        parts.append("Signing kid: " + decision["sig_kid"] + ".")
    dropped = decision.get("dropped_badges") or []
    if dropped:
        parts.append("Badge claims dropped by local policy: "
                     + ", ".join(dropped) + ".")
    if title:
        parts.insert(0, "Job " + str(job.get("id")) + " ("
                     + title + "):")
    return " ".join(parts)


def trust_brief_lines(records):
    """One brief line per trust-refusal record."""
    lines = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "trust-refusal":
            continue
        line = ("Trust refusal: job " + str(record.get("job"))
                + " refused: " + str(record.get("reason")))
        dropped = record.get("dropped_badges") or []
        if dropped:
            line += ("; badges dropped: " + ", ".join(dropped))
        lines.append(line)
    return lines


def trust_events(records):
    """Trust-refusal records in Hana's OS-117
    federation trust-event shape: kind refusal,
    machine, detail. A record without a machine is
    skipped, matching federation_lines, which skips
    a trust event without a machine name."""
    events = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "trust-refusal":
            continue
        machine = record.get("machine")
        if not (isinstance(machine, str) and machine):
            continue
        detail = "job " + str(record.get("job")) + " refused: " \
            + str(record.get("reason"))
        dropped = record.get("dropped_badges") or []
        if dropped:
            detail += "; badges dropped: " + ", ".join(dropped)
        events.append({"kind": "refusal", "machine": machine,
                       "detail": detail})
    return events
