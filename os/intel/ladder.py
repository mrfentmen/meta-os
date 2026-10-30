"""intel/ladder.py -- the self-repair ladder (OS-095, Milo).

On a stall, the watchdog acts before it reports: nudge the
worker, then restart the worker, then reassign the job to
another agent. Each rung is journaled with its reason, and
Dale is contacted at no rung: this module has no push path,
no announcement path, and no import of intel/push.py. A
ladder record is a journal entry and a brief line, nothing
more.

The division of labor is exact, and it is the OS-034
contract in code. The watchdog judges; it does not touch
a process or a job claim. Nudge is a note to a live
worker. Restart is systemd's job: the ladder records a
restart-request event note (see watchdog.restart_event_note)
and the process restart itself belongs to the unit's
Restart= setting, worked mechanically by the watchman on
its machine (Pax OS-118). Reassign is the overseer's job:
the ladder composes the baton from the job record (title,
deposited progress, files touched) and hands the decision
to the overseer, which moves the claim (the OS-125 baton
pass). The drill's simulated owners apply each rung so the
decision can be proven end to end on fixtures; on a live
machine the ladder never performs the rung itself, so it
can never fight systemd over a restart or steal a claim
from a worker that is still alive.

Rung selection is a pure function of snapshot facts, not
of the alert kind, so a detector change cannot silently
retarget the ladder:

- worker in the caps registry and present: the worker
  lives but the work does not move (WDG-003) -> nudge.
  A nudge is cheap and a restart would be wasteful.
- worker in the caps registry and absent from presence:
  nobody is home to nudge (WDG-002) -> restart. The
  process is dead; only systemd can bring it back.
- claimer outside the caps registry: no registered worker
  holds the job, so there is nobody to nudge or restart
  (WDG-025 walk-on) -> reassign. The job is held by the
  wrong worker, and the baton pass moves it to a
  registered one with its deposited progress intact.

A stall record is a dict with "nick" and "job" (the shape
the WDG detectors yield). A malformed stall (missing nick
or job) yields no action, never a crash: an absent subject
is not a subject to act on. A stall whose job record is
missing from the snapshot also yields no action, because
there is no baton to pass and no claim to reason about.

Idempotency: ladder_tick skips any stall whose dedupe key
(ladder:<job>:<rung>) already appears in the journal, so a
second tick on an unchanged stall journals nothing new.
The ladder never mutates its inputs: the snapshot and the
journal list it is given come back unchanged, and it
returns only the new records. Attempt budgets and the
escalation gate are NOT here: when every rung is spent,
the job parks and Dale hears about it exactly once, and
that is OS-096's job, owed after this one.

Usage: ladder_tick(snapshot, stalls, journal, now) returns
the new journal records; ladder_brief_lines(records)
renders them for the next brief.
"""

__all__ = ["RUNGS", "NUDGE", "RESTART", "REASSIGN", "classify",
           "ladder_action", "ladder_tick", "ladder_brief_lines",
           "baton_for"]

NUDGE = "nudge"
RESTART = "restart"
REASSIGN = "reassign"
RUNGS = (NUDGE, RESTART, REASSIGN)

_REASONS = {
    NUDGE: "worker alive, work stuck",
    RESTART: "worker dead, systemd restarts the process",
    REASSIGN: "job held by a worker outside the caps registry",
}


def _caps(snapshot):
    """Caps registry as a dict; a missing or malformed registry
    reads as empty, so every claimer counts as outside it."""
    caps = snapshot.get("caps") if isinstance(snapshot, dict) else None
    return caps if isinstance(caps, dict) else {}


def _presence(snapshot):
    """Presence list; a missing or malformed list reads as empty,
    so every worker counts as absent."""
    presence = (snapshot.get("presence")
                if isinstance(snapshot, dict) else None)
    return presence if isinstance(presence, list) else []


def _job_by_id(snapshot, job_id):
    """Job record for job_id, or None when the snapshot carries
    no such job."""
    jobs = snapshot.get("jobs") if isinstance(snapshot, dict) else None
    if not isinstance(jobs, list):
        return None
    for job in jobs:
        if isinstance(job, dict) and job.get("id") == job_id:
            return job
    return None


def classify(snapshot, stall):
    """Return (rung, reason) for one stall, or (None, reason)
    when the stall cannot be acted on.

    The decision reads only caps membership and presence
    membership, so it is identical for a detector alert and
    for a walk-on tracking record carrying the same nick.
    """
    if not isinstance(stall, dict):
        return None, "stall is not a record"
    nick = stall.get("nick")
    job_id = stall.get("job")
    if not nick or not job_id:
        return None, "stall names no worker or no job"
    if _job_by_id(snapshot, job_id) is None:
        return None, "job not in snapshot"
    if nick not in _caps(snapshot):
        return REASSIGN, _REASONS[REASSIGN]
    if nick not in _presence(snapshot):
        return RESTART, _REASONS[RESTART]
    return NUDGE, _REASONS[NUDGE]


def baton_for(snapshot, job_id):
    """Baton state for a reassign: the job's title, its
    deposited progress timestamp, and its files list, copied
    exactly. Nothing is invented: a missing field reads as
    None (title, progress) or an empty list (files), and the
    next worker resumes from the deposited progress, never
    from a restated whole job."""
    job = _job_by_id(snapshot, job_id)
    if job is None:
        return None
    files = job.get("files")
    return {
        "title": job.get("title"),
        "last_progress_at": job.get("last_progress_at"),
        "files": list(files) if isinstance(files, list) else [],
    }


def ladder_action(snapshot, stall, now):
    """One journal record for one stall, or None when the
    stall cannot be acted on. The record id doubles as the
    dedupe key, so the journal and the dedupe check can
    never disagree about what was already done."""
    rung, reason = classify(snapshot, stall)
    if rung is None:
        return None
    record = {
        "id": "ladder:%s:%s" % (stall.get("job"), rung),
        "kind": "ladder-action",
        "job": stall.get("job"),
        "worker": stall.get("nick"),
        "rung": rung,
        "reason": reason,
        "dedupe_key": "ladder:%s:%s" % (stall.get("job"), rung),
        "created_at": now,
    }
    if rung == REASSIGN:
        record["baton"] = baton_for(snapshot, stall.get("job"))
    return record


def ladder_tick(snapshot, stalls, journal, now):
    """New journal records for this tick's stalls, skipping
    any rung already journaled. Pure: neither the snapshot
    nor the journal is mutated, and the return holds only
    ladder-action records, never a push or an announcement."""
    journal = journal if isinstance(journal, list) else []
    stalls = stalls if isinstance(stalls, list) else []
    seen = set()
    for entry in journal:
        if isinstance(entry, dict):
            if entry.get("dedupe_key"):
                seen.add(entry.get("dedupe_key"))
            if entry.get("id"):
                seen.add(entry.get("id"))
    new_records = []
    for stall in stalls:
        record = ladder_action(snapshot, stall, now)
        if record is None:
            continue
        if record["dedupe_key"] in seen or record["id"] in seen:
            continue
        seen.add(record["dedupe_key"])
        new_records.append(record)
    return new_records


def ladder_brief_lines(records):
    """One frozen line per ladder record for the next brief:
    rung, job, worker, reason. A record with no rung renders
    nothing, so a malformed journal entry can never print a
    half line into the brief."""
    lines = []
    records = records if isinstance(records, list) else []
    for record in records:
        if not isinstance(record, dict):
            continue
        rung = record.get("rung")
        if rung not in RUNGS:
            continue
        lines.append("Ladder: %s job %s (%s): %s"
                     % (rung, record.get("job"),
                        record.get("worker"), record.get("reason")))
    return lines
