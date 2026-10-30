"""The two pushes — OS-097 (Hana lane).

A job's close fires at most one push, and a job's park fires at
most one push. There is no third push type.

    done:    the overseer closed a job on passed acceptance
             checks — "All done" plus the plain-English summary
             of what was built and what was verified.
    blocked: a parked job — the exact question it is waiting
             on, in plain English, quoted verbatim.

Pure functions: no network, no Redis, no Spark, no bus post,
no secret. These builders shape the push payload only. They do
not send it — the Web Push worker (muse-relay-push, outside
this repo) is the sender, and the call sites that fire a push
from a real overseer close (mos/overseer.py verify_done) and
from a real escalation-gate park (Milo OS-096) are not wired
yet, so nothing here can ring a phone on its own.

Inputs use the records the repo already produces:

    job (jobs.py / mos/overseer.py shape):
        {"id": str, "title": str, "status": str,
         "verified": "1" once mos/overseer.py verify_done
         stamps it, "note": str (the blocked reason jobs.py
         cmd_blocked stores)}
    verification (mos/acceptance.py verify() shape):
        {"ok": bool,
         "checks": [{"check": str, "ok": bool}, ...],
         "artifacts": [file path, ...]}

Gates, enforced here rather than trusted to the caller:

- A done push needs all three: job status "done", the
  overseer verified stamp, and a verification whose every
  check passed. A job closed without passing its checks gets
  no done push — a failed check, a missing stamp, or a
  missing verification each yields None, never a push.
- A blocked push needs job status "blocked" and a question.
  The question is the caller's question when one is given,
  else the job's stored note. With neither, there is no
  push: a push with no question would have to invent one.
- Exactly one: PushLedger remembers (job id, push type)
  pairs already emitted. decide_push with a ledger returns
  None for a repeat, so a second close or a second park
  for the same job cannot ring twice.
- No third type: build_push raises ValueError for any kind
  outside ("done", "blocked"), and validate_push rejects
  any push whose type is not one of those two.

Honesty rules, same as the brief engine: a summary names
only the artifacts and checks in the record it was given.
With no artifacts recorded it says so instead of naming a
file; with no checks recorded it says no acceptance
criteria were recorded instead of claiming a check passed.
The blocked question is quoted verbatim, never paraphrased
away — the BRF-005 verbatim rule applied to pushes.
"""

PUSH_TYPES = ("done", "blocked")


def _job_id(job):
    if not isinstance(job, dict):
        return ""
    return job.get("id") or ""


def _job_title(job):
    if not isinstance(job, dict):
        return ""
    title = job.get("title") or ""
    if title:
        return title
    jid = _job_id(job)
    return f"job {jid}" if jid else ""


def _verified_stamp(job):
    """True only for the stamp mos/overseer.py verify_done sets."""
    if not isinstance(job, dict):
        return False
    return job.get("verified") in ("1", 1, True)


def _checks_passed(verification):
    """(ok, passed check names) for an acceptance verify() record."""
    if not isinstance(verification, dict):
        return False, []
    if not verification.get("ok"):
        return False, []
    checks = verification.get("checks") or []
    if not isinstance(checks, list):
        return False, []
    for check in checks:
        if not isinstance(check, dict) or not check.get("ok"):
            return False, []
    return True, [c.get("check", "") for c in checks if c.get("check")]


def build_done_push(job, verification):
    """Build the done push for a verified-closed job, or None.

    Returns None when the job is not a verified close: status
    other than "done", no overseer verified stamp, no
    verification record, or any failed check.
    """
    jid = _job_id(job)
    if not jid:
        return None
    if not isinstance(job, dict) or job.get("status") != "done":
        return None
    if not _verified_stamp(job):
        return None
    ok, passed = _checks_passed(verification)
    if not ok:
        return None
    artifacts = []
    if isinstance(verification, dict):
        raw = verification.get("artifacts")
        if raw is None:
            raw = verification.get("files")
        if isinstance(raw, list):
            artifacts = [str(a) for a in raw if a]
    title = _job_title(job)
    lines = [f"All done: {title}."]
    if artifacts:
        lines.append(f"Built: {', '.join(artifacts)}.")
    else:
        lines.append("Built: not reported in the artifact record.")
    if passed:
        lines.append(f"Verified: {', '.join(passed)}.")
    else:
        lines.append("Verified: no acceptance criteria were recorded.")
    return {"type": "done", "job_id": jid, "title": title,
            "body": " ".join(lines), "checks": passed,
            "artifacts": artifacts}


def build_blocked_push(job, question=None):
    """Build the blocked push for a parked job, or None.

    The question is the caller's question when one is given,
    else the job's stored note (jobs.py cmd_blocked). With
    neither, or with a job that is not status "blocked",
    returns None — no question is ever invented.
    """
    jid = _job_id(job)
    if not jid:
        return None
    if not isinstance(job, dict) or job.get("status") != "blocked":
        return None
    if question is None and isinstance(job, dict):
        question = job.get("note")
    if not isinstance(question, str) or not question.strip():
        return None
    question = question.strip()
    title = _job_title(job)
    body = f"{title} is blocked. Question: {question}"
    return {"type": "blocked", "job_id": jid, "title": title,
            "body": body, "question": question}


def build_push(kind, job, verification=None, question=None):
    """Build a push of the given kind, or None when gated out.

    Raises ValueError for any kind outside PUSH_TYPES: no
    third push type exists, and a typo must fail loudly
    rather than silently become a new kind of ring.
    """
    if kind not in PUSH_TYPES:
        raise ValueError(f"unknown push type {kind!r}: "
                         f"only {list(PUSH_TYPES)} exist")
    if kind == "done":
        return build_done_push(job, verification)
    return build_blocked_push(job, question)


def validate_push(push):
    """True only for a well-formed push of a known type."""
    if not isinstance(push, dict):
        return False
    if push.get("type") not in PUSH_TYPES:
        return False
    if not push.get("job_id"):
        return False
    body = push.get("body")
    return isinstance(body, str) and bool(body.strip())


class PushLedger:
    """Exactly-one record: (job id, push type) pairs emitted.

    mark() returns True the first time a pair is seen and
    False for every repeat, so decide_push with a ledger
    never yields a second push for the same job and kind.
    """

    def __init__(self):
        self._seen = set()

    def has(self, job_id, kind):
        return (job_id, kind) in self._seen

    def mark(self, job_id, kind):
        pair = (job_id, kind)
        if pair in self._seen:
            return False
        self._seen.add(pair)
        return True


def decide_push(job, verification=None, question=None, ledger=None):
    """Build the one push a job's state earns, or None.

    A done job earns a done push (gated by build_done_push);
    a blocked job earns a blocked push (gated by
    build_blocked_push); any other status earns nothing.
    With a ledger, a repeat for the same job and kind
    returns None instead of a second push.
    """
    if not isinstance(job, dict):
        return None
    status = job.get("status")
    if status == "done":
        push = build_done_push(job, verification)
    elif status == "blocked":
        push = build_blocked_push(job, question)
    else:
        return None
    if push is None:
        return None
    if ledger is not None and not ledger.mark(push["job_id"],
                                              push["type"]):
        return None
    return push
