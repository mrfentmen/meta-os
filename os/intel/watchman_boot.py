"""intel/watchman_boot.py -- watchman state after reboot (OS-129, Milo).

The watchman itself survives the machine dying. At boot it
rebuilds its picture purely from queue claims and leases:
it never reads a stored message counter, so no stale
counter gap and no missed ring across the reboot boundary,
and a deliberately corrupted stored counter value changes
nothing in its behaviour. Its first post-boot cycle rings
for every job that arrived while the machine was down,
and for every claimed job whose lease died during the
downtime (the lease sweep requeues those), and it rings
for each such job exactly once. Its first post-boot cycle
also reconciles with the lease sweep: the recovered count
it reports matches the sweep record.

This module is the verification half of OS-129. It does
not ring any bell itself and it moves no claim: it
computes, from fixture queue state, the ring set a correct
watchman must produce, and checks that set against the
sweep record. The mechanical half (the resident watchman
program that actually rings) is Pax OS-118. The drill
proves the computation on fixtures; a live boot on a
booted test image is not claimed here, because no test
image runs in this repo.

Rules, all pure functions of queue state:

- Downtime window: (down_since, boot_at]. A job posted
  in that window arrived while the machine was down, so
  the first post-boot cycle must ring for it. A job
  posted at or before down_since was already visible
  before the machine died, so it does not ring at boot.
- Lease death: a claimed job whose lease_expires_at falls
  in the window died during the downtime; the sweep
  requeues it, so the first post-boot cycle must ring for
  it. A claimed job whose lease is still alive at boot
  does not ring: its worker may still be alive.
- Done jobs never ring. Malformed records (not a dict,
  no id, no usable timestamps) never ring and never
  crash: an absent subject is not a subject to ring for.
- Dedupe: a job id rings at most once per boot cycle,
  however many times it appears in the input, and a job
  id already in the rung ledger (rung by an earlier
  post-boot cycle) never rings again.
- No counter anywhere: no function here takes a counter
  argument, and no function reads one. A snapshot that
  carries a stored counter value, corrupted or not, yields
  the identical ring set, because the counter is never
  consulted. That is the proof the drift failure mode is
  designed out, not patched.
- Reconciliation: the lease-expired ring ids must equal
  the sweep record's requeued ids. When they match, the
  verification note reports recovered counts that agree;
  when they differ, the note names the mismatched ids
  and reports reconcile False, never a fudged count.

Inputs are never mutated: every function copies what it
returns, and the rung ledger passed in is left alone;
the caller owns the ledger update. No push path, no
announcement path, no network: a verification note can
never contact Dale.

Usage: post_boot_rings(jobs, down_since, boot_at,
rung_ledger) returns the ring list; verify_boot_cycle(...)
returns the verification note dict (with its rings and
its brief lines via boot_brief_lines(note)).
"""

__all__ = ["post_boot_rings", "verify_boot_cycle",
           "boot_brief_lines", "sweep_mismatch"]


def _num(value):
    """An int/float timestamp, else None. Bools are not times."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _job_id(job):
    if not isinstance(job, dict):
        return None
    job_id = job.get("id")
    if isinstance(job_id, str) and job_id.strip():
        return job_id.strip()
    return None


def post_boot_rings(jobs, down_since, boot_at, rung_ledger=None):
    """The ring set for the first post-boot cycle.

    jobs: iterable of job records. down_since: the moment
    the machine went down. boot_at: the moment it came
    back. rung_ledger: an iterable of job ids already rung
    (earlier post-boot cycles); None means nothing rung.
    Returns a list of ring dicts in input order:
    {"job_id", "reason", "posted_at", "lease_expires_at"}.
    reason is "arrived_during_downtime" for an open job
    posted in the window, or "lease_expired_during_downtime"
    for a claimed job whose lease died in the window.
    """
    rung = set(rung_ledger or [])
    rings = []
    seen = set()
    for job in jobs or []:
        job_id = _job_id(job)
        if job_id is None or job_id in seen or job_id in rung:
            continue
        status = job.get("status")
        posted_at = _num(job.get("posted_at"))
        lease_expires_at = _num(job.get("lease_expires_at"))
        reason = None
        if status == "open" and posted_at is not None:
            if down_since < posted_at <= boot_at:
                reason = "arrived_during_downtime"
        elif status == "claimed" and lease_expires_at is not None:
            if down_since < lease_expires_at <= boot_at:
                reason = "lease_expired_during_downtime"
        if reason is None:
            continue
        seen.add(job_id)
        rings.append({
            "job_id": job_id,
            "reason": reason,
            "posted_at": posted_at,
            "lease_expires_at": lease_expires_at,
        })
    return rings


def sweep_mismatch(rings, sweep_requeued):
    """Job ids where rings and the sweep record disagree.

    sweep_requeued: the job ids the lease sweep says it
    requeued. Returns {"missing": [...], "extra": [...]}:
    missing are lease-expired rings the sweep did not
    requeue; extra are sweep requeues with no matching
    ring. Both lists are sorted, so the report is stable.
    """
    ring_leases = sorted(
        r["job_id"] for r in rings
        if r["reason"] == "lease_expired_during_downtime")
    swept = sorted(set(sweep_requeued or []))
    return {
        "missing": [j for j in ring_leases if j not in swept],
        "extra": [j for j in swept if j not in ring_leases],
    }


def verify_boot_cycle(jobs, down_since, boot_at, sweep_requeued,
                      rung_ledger=None):
    """The OS-129 verification note for one boot cycle.

    Returns a dict: the rings, the counts (arrived,
    lease_expired, total), the sweep reconciliation
    (reconciled bool plus any mismatch ids), and a
    counter_proof entry: the ring set recomputed with a
    corrupted stored counter injected into the snapshot
    is identical, proving no counter is ever read. The
    note carries no push and no announcement field.
    """
    rings = post_boot_rings(jobs, down_since, boot_at, rung_ledger)
    mismatch = sweep_mismatch(rings, sweep_requeued)
    reconciled = not mismatch["missing"] and not mismatch["extra"]
    # Counter proof: inject a corrupted stored counter into
    # a copy of every record and into a wrapper snapshot,
    # and recompute. The ring set must be identical, because
    # no function here ever consults a counter.
    poisoned = []
    for job in jobs or []:
        if isinstance(job, dict):
            copy = dict(job)
            copy["seen_counter"] = 999999
            copy["message_counter"] = -42
            poisoned.append(copy)
        else:
            poisoned.append(job)
    reproof = post_boot_rings(poisoned, down_since, boot_at, rung_ledger)
    counter_ignored = [r["job_id"] for r in reproof] == \
        [r["job_id"] for r in rings]
    arrived = sum(1 for r in rings
                  if r["reason"] == "arrived_during_downtime")
    expired = sum(1 for r in rings
                  if r["reason"] == "lease_expired_during_downtime")
    return {
        "rings": rings,
        "arrived_count": arrived,
        "lease_expired_count": expired,
        "total_rings": len(rings),
        "sweep_requeued": sorted(set(sweep_requeued or [])),
        "reconciled": reconciled,
        "mismatch": mismatch,
        "counter_ignored": counter_ignored,
    }


def boot_brief_lines(note):
    """Brief lines for a verification note."""
    lines = [
        "watchman boot: %d ring(s) (%d arrived during downtime, "
        "%d lease-expired)" % (
            note["total_rings"], note["arrived_count"],
            note["lease_expired_count"]),
    ]
    for ring in note["rings"]:
        lines.append("ring %s: %s" % (ring["job_id"], ring["reason"]))
    if note["reconciled"]:
        lines.append("boot sweep reconciled: %d requeued, counts agree"
                     % len(note["sweep_requeued"]))
    else:
        lines.append("boot sweep MISMATCH: missing %s, extra %s"
                     % (note["mismatch"]["missing"],
                        note["mismatch"]["extra"]))
    lines.append("stored counter ignored: %s"
                 % ("yes" if note["counter_ignored"] else "NO"))
    return lines
