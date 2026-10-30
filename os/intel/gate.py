"""intel/gate.py -- attempt budgets + the escalation gate (OS-096, Milo).

When every repair rung is spent, the loop stops: a job that
has burned its attempt budget parks visibly, and the one
thing the crew cannot settle itself -- a blocker that is
genuinely Dale's call (money, permission, direction) --
parks the same way. Each park fires exactly one blocked
push (OS-097): the payload is built here, never sent.
Sending belongs to the Web Push worker (muse-relay-push,
outside this repo), so this module has no network, no bus
post, and no secret, and nothing in it can ring a phone on
its own. A second tick over an already parked job journals
nothing new: no loop, no duplicate push, ever.

The division of labor is exact, and it is the OS-095
ladder's other half. The ladder acts while attempts
remain; the gate ends the job's repair life when the
budget is spent or when the blocker is Dale's call. The
gate never mutates a snapshot, a job record, or a claim:
it returns only new journal records, and the parked shape
it hands the push builder is a copy of the job record
with status "blocked" and the question as its note, so
intel/push.py build_blocked_push accepts it unchanged
and the question it carries is quoted verbatim.

What counts as Dale's call is an explicit field, not a
guess from free text: a job record carries blocker_kind,
and only "money", "permission", or "direction" park on
the blocker alone. Any other kind -- a dependency, a
collision, an unknown kind, a missing kind -- is crew
work: the gate stays quiet and the ladder keeps working.
A blocker_kind is never inferred from the note, because
an inferred kind could park a job the crew could have
settled, and a missed kind could retry one it could not.

Attempt figures are read the same way the WDG-008
detector reads them: attempts and max_attempts on the job
record, as ints or integer-valued strings (the Redis
representation). A job with no usable max_attempts is
unbudgeted: it never parks on attempts, because an absent
budget is not a zero budget. Malformed figures (a
non-numeric string, a negative count, a max of zero) are
unbudgeted too, never guessed. A done job never parks,
however its figures read: a closed job is not a job to
repair. A job record without an id is skipped, never
crashed on: an absent subject is not a subject to act on.

Dedupe: gate_tick skips any job whose park record
(dedupe_key park:<job>) already appears in the journal,
so a parked job stays parked and its escalation stays
singular across ticks. The escalation record carries the
built blocked-push payload (validated by
intel/push.py validate_push) and the parked record
carries the question, so the next brief can show both
without re-deriving either.

Usage: gate_tick(snapshot, journal, now) returns the new
journal records; gate_brief_lines(records) renders them
for the next brief.
"""

from intel import push as push_module

__all__ = ["DALE_CALL_KINDS", "attempts_left", "budget_exhausted",
           "is_dale_call", "question_for", "gate_tick",
           "gate_brief_lines"]

DALE_CALL_KINDS = ("money", "permission", "direction")


def _as_int(value):
    """An int for an int or an integer-valued string, else None.

    Booleans are not ints here (True would read as 1 attempt),
    floats are not ints (2.5 attempts is not a count), and a
    non-numeric string is malformed, not zero.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None


def _title(job):
    title = job.get("title") if isinstance(job, dict) else None
    if isinstance(title, str) and title.strip():
        return title.strip()
    jid = job.get("id") if isinstance(job, dict) else None
    return "job %s" % jid if jid else "job"


def attempts_left(job):
    """Attempts remaining for a job record, or None when the
    job is unbudgeted or its figures are malformed."""
    if not isinstance(job, dict):
        return None
    attempts = _as_int(job.get("attempts"))
    maximum = _as_int(job.get("max_attempts"))
    if attempts is None or maximum is None:
        return None
    if attempts < 0 or maximum <= 0:
        return None
    return maximum - attempts


def budget_exhausted(job):
    """True only when a well-formed budget reads spent."""
    left = attempts_left(job)
    return left is not None and left <= 0


def is_dale_call(job):
    """True only for an explicit Dale-call blocker kind."""
    if not isinstance(job, dict):
        return False
    return job.get("blocker_kind") in DALE_CALL_KINDS


def question_for(job, reason):
    """The exact question the blocked push carries.

    A Dale-call blocker with a stored note quotes that note
    verbatim (the BRF-005 verbatim rule). Without a note,
    the question names the kind from the record. An
    exhausted budget states the budget fact and asks what
    the crew should do next. Nothing here invents a reason
    the record does not carry.
    """
    if is_dale_call(job) and isinstance(job, dict):
        note = job.get("note")
        if isinstance(note, str) and note.strip():
            return note.strip()
        return "%s is blocked on %s; Dale's call is needed." % (
            _title(job), job.get("blocker_kind"))
    attempts = _as_int(job.get("attempts")) if isinstance(job, dict) else None
    maximum = _as_int(job.get("max_attempts")) if isinstance(job, dict) else None
    return ("%s burned its attempt budget (%s/%s attempts) and "
            "is parked. What should the crew do next?") % (
                _title(job), attempts, maximum)


def _parked_jobs(journal):
    """Job ids with a park record already in the journal."""
    parked = set()
    if not isinstance(journal, list):
        return parked
    for record in journal:
        if isinstance(record, dict) and record.get("dedupe_key", "").startswith("park:"):
            parked.add(record.get("dedupe_key")[len("park:"):])
    return parked


def gate_tick(snapshot, journal, now):
    """Park and escalate exactly once per job that qualifies.

    snapshot carries "jobs" (job records); journal is the
    existing journal list (records with dedupe_key). A job
    qualifies when its attempt budget is spent or its
    blocker kind is Dale's call. Each qualifying job yields
    two records: a parked record and an escalation record
    carrying the built blocked-push payload. Jobs already
    parked, done jobs, malformed records, and crew-fixable
    blockers yield nothing. Inputs are never mutated.
    """
    jobs = snapshot.get("jobs") if isinstance(snapshot, dict) else None
    if not isinstance(jobs, list):
        return []
    parked = _parked_jobs(journal)
    records = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_id = job.get("id")
        if not job_id:
            continue
        if job_id in parked:
            continue
        if job.get("status") == "done":
            continue
        if budget_exhausted(job):
            attempts = _as_int(job.get("attempts"))
            maximum = _as_int(job.get("max_attempts"))
            reason = "attempt budget exhausted (%s/%s attempts)" % (
                attempts, maximum)
        elif is_dale_call(job):
            reason = "blocked on %s (Dale's call)" % job.get("blocker_kind")
        else:
            continue
        question = question_for(job, reason)
        parked_job = dict(job)
        parked_job["status"] = "blocked"
        parked_job["note"] = question
        payload = push_module.build_blocked_push(parked_job)
        if payload is None:
            continue
        records.append({"kind": "parked", "job": job_id,
                        "reason": reason, "question": question,
                        "parked_at": now,
                        "dedupe_key": "park:%s" % job_id})
        records.append({"kind": "escalation", "job": job_id,
                        "reason": reason, "question": question,
                        "push": payload, "escalated_at": now,
                        "dedupe_key": "escalate:%s" % job_id})
        parked.add(job_id)
    return records


def gate_brief_lines(records):
    """Brief lines for gate records; other records ignored."""
    lines = []
    if not isinstance(records, list):
        return lines
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("kind") == "parked":
            lines.append("Parked job %s: %s." % (
                record.get("job"), record.get("reason")))
        elif record.get("kind") == "escalation":
            lines.append("Escalated job %s: one blocked push queued." % (
                record.get("job"),))
    return lines
