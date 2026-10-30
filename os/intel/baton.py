"""intel/baton.py -- the baton pass (OS-125, Milo).

When the self-repair ladder reaches reassign, the job
does not restart from zero. The watchman composes a
continuation prompt from the job record -- goal, the
progress the worker deposited as it went, files touched,
what remains, acceptance checks -- and hands it to the
next agent program, which picks up exactly where the
previous worker left off. Workers deposit progress as
they go, or there is no baton to pass: a job with no
deposited progress yields a prompt that says so plainly,
and claims no work done.

The division of labor is exact, and it is the OS-034
contract in code. This module composes the baton; it
never moves a claim. The overseer moves the claim (the
mechanical half belongs to the watchman on its machine,
Pax OS-118), and the drill's simulated overseer move
proves the handoff on fixtures. This module has no push
path, no announcement path, and no network, so a baton
pass can never contact Dale: reassign is crew work, not
a blocked push (that is OS-096's gate, and it is a
separate decision).

What the baton carries, all copied from the job record,
nothing invented:

- goal: the job's "goal" field, else the Goal line of
  its spec text (the DSP spec standard puts goal first),
  else None, stated as not stated.
- deposited progress: the "progress_notes" list when the
  record carries one, else the latest "note" alone when
  present, else nothing, stated as no progress deposited.
  The "last_progress_at" timestamp rides along unchanged.
- files: the job's "files" list, or its comma-separated
  files string (the jobs.py Redis representation), split
  and deduped in order. "completed_files" names the files
  already changed; "remaining_files" is files minus
  completed, in order. A file in completed never appears
  in remaining, so a next worker following the baton
  cannot repeat a file change by following it.
- what remains: the "remaining" or "remaining_steps"
  list when present, else "steps" minus "completed_steps"
  when both are present, else None, stated as not stated.
- acceptance checks: the "acceptance_checks" list, else
  the "accept" string split on lines (the jobs.py
  --accept field), else the "acceptance" list or string,
  else nothing, stated as no checks recorded.

A malformed job record (not a dict, or no id) yields no
baton, never a crash: an absent subject is not a subject
to hand over. A job record without a title still yields a
baton, named by its id. The baton and its prompt are
copies: composing never mutates the job record, and a
second pass over the same job journals nothing new
(dedupe baton:<job>).

In-window proof is same-program: the drill composes the
baton and a simulated next worker completes the job in
one process. The cross-program pass (for example Muse
to Freebuff, both pre-installed in the image) is the
named stretch line: it is not claimed here, because no
second agent program runs in this drill, and claiming it
would be inventing a run that never happened.

Usage: compose_baton(job) returns the baton dict (with
its "prompt" text) or None; baton_pass_tick(snapshot,
job_id, to_worker, journal, now) returns the new journal
records; baton_brief_lines(records) renders them for the
next brief.
"""

__all__ = ["compose_baton", "baton_pass_tick", "baton_brief_lines",
           "remaining_files", "remaining_steps", "acceptance_checks"]


def _text(value):
    """A stripped non-empty string, else None."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _str_list(value):
    """A list of non-empty strings from a list or a
    comma-separated string, deduped in order. Anything else
    reads as an empty list, never a crash."""
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return list(dict.fromkeys(part for part in parts if part))
    if isinstance(value, list):
        parts = [part.strip() for part in value
                 if isinstance(part, str) and part.strip()]
        return list(dict.fromkeys(parts))
    return []


def _lines(value):
    """Acceptance lines from a list or a newline-separated
    string, deduped in order, empties dropped."""
    if isinstance(value, str):
        parts = [line.strip() for line in value.splitlines()]
        return list(dict.fromkeys(line for line in parts if line))
    if isinstance(value, list):
        parts = [line.strip() for line in value
                 if isinstance(line, str) and line.strip()]
        return list(dict.fromkeys(parts))
    return []


def _spec_goal(job):
    """The Goal line of a spec text, or the goal key of a
    spec dict, else None. Spec text follows the DSP spec
    standard: goal first, then context, files, steps."""
    spec = job.get("spec")
    if isinstance(spec, dict):
        return _text(spec.get("goal"))
    if isinstance(spec, str):
        for line in spec.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("goal:"):
                return _text(stripped[len("goal:"):])
    return None


def _goal(job):
    goal = _text(job.get("goal"))
    if goal is not None:
        return goal
    return _spec_goal(job)


def _progress(job):
    """Deposited progress notes: the progress_notes list
    when present, else the latest note alone, else []."""
    notes = _str_list(job.get("progress_notes"))
    if notes:
        return notes
    note = _text(job.get("note"))
    return [note] if note is not None else []


def remaining_files(job):
    """Files still to touch: the job's files minus its
    completed files, in order. With no completed record,
    every file remains, and the prompt says no completed
    file record exists, so the next worker verifies rather
    than assumes."""
    if not isinstance(job, dict):
        return []
    files = _str_list(job.get("files"))
    completed = set(_str_list(job.get("completed_files")))
    return [path for path in files if path not in completed]


def remaining_steps(job):
    """Steps still to do: the remaining list when present,
    else steps minus completed_steps, else None."""
    if not isinstance(job, dict):
        return None
    remaining = _str_list(job.get("remaining"))
    if remaining:
        return remaining
    remaining = _str_list(job.get("remaining_steps"))
    if remaining:
        return remaining
    steps = _str_list(job.get("steps"))
    if not steps:
        return None
    completed = set(_str_list(job.get("completed_steps")))
    rest = [step for step in steps if step not in completed]
    return rest if rest else None


def acceptance_checks(job):
    """Acceptance checks as a line list, from
    acceptance_checks, accept, or acceptance, in that order.
    The first non-empty source wins; sources are never
    merged, because a merged list could double a check."""
    if not isinstance(job, dict):
        return []
    for field in ("acceptance_checks", "accept", "acceptance"):
        checks = _lines(job.get(field))
        if checks:
            return checks
    return []


def _section(label, lines, empty_text):
    if lines:
        return "%s:\n  - %s" % (label, "\n  - ".join(lines))
    return "%s: %s" % (label, empty_text)


def compose_baton(job):
    """The full baton for one job record, or None when the
    record cannot be handed over. The prompt names what
    remains instead of restating the whole job: the next
    worker's first act is the remaining work, not a redo."""
    if not isinstance(job, dict):
        return None
    job_id = job.get("id")
    if not job_id:
        return None
    title = _text(job.get("title")) or ("job %s" % job_id)
    goal = _goal(job)
    progress = _progress(job)
    files = _str_list(job.get("files"))
    completed = _str_list(job.get("completed_files"))
    remaining = remaining_files(job)
    steps = remaining_steps(job)
    checks = acceptance_checks(job)
    from_worker = _text(job.get("claim")) or _text(job.get("created_by"))
    prompt_lines = [
        "Continuation for job %s: %s" % (job_id, title),
        "You are picking up work already in progress. Do not "
        "restart it and do not redo completed work.",
        "Goal: %s" % (goal if goal is not None
                       else "not stated in the job record"),
        _section("Done so far", progress,
                 "no progress notes deposited"),
        _section("Files already changed (do not rewrite unless "
                 "a check fails)", completed,
                 "no completed-file record"),
        _section("Files still to touch", remaining,
                 "none listed"),
        _section("What remains", steps,
                 "not stated in the job record; work from the "
                 "deposited progress and the acceptance checks"),
        _section("Acceptance checks (all must pass before you "
                 "report done)", checks,
                 "none recorded"),
    ]
    if from_worker is not None:
        prompt_lines.append("Previous worker: %s" % from_worker)
    prompt_lines.append(
        "Last deposited progress at: %s"
        % (job.get("last_progress_at")
           if job.get("last_progress_at") is not None
           else "not recorded"))
    return {
        "job": job_id,
        "title": title,
        "goal": goal,
        "progress_notes": progress,
        "last_progress_at": job.get("last_progress_at"),
        "files": files,
        "completed_files": completed,
        "remaining_files": remaining,
        "remaining_steps": steps,
        "acceptance_checks": checks,
        "from_worker": from_worker,
        "prompt": "\n".join(prompt_lines),
    }


def _job_by_id(snapshot, job_id):
    jobs = snapshot.get("jobs") if isinstance(snapshot, dict) else None
    if not isinstance(jobs, list):
        return None
    for job in jobs:
        if isinstance(job, dict) and job.get("id") == job_id:
            return job
    return None


def baton_pass_tick(snapshot, job_id, to_worker, journal, now):
    """One journal record for a baton pass, or [] when the
    job cannot be handed over or the pass is already
    journaled. The record carries the baton, never a push:
    the overseer moves the claim from this record, and this
    module never moves it itself."""
    if not job_id or not to_worker:
        return []
    job = _job_by_id(snapshot, job_id)
    if job is None:
        return []
    baton = compose_baton(job)
    if baton is None:
        return []
    dedupe = "baton:%s" % job_id
    journal = journal if isinstance(journal, list) else []
    for entry in journal:
        if isinstance(entry, dict) and entry.get("dedupe_key") == dedupe:
            return []
    return [{
        "kind": "baton-pass",
        "job": job_id,
        "from_worker": baton["from_worker"],
        "to_worker": to_worker,
        "baton": baton,
        "passed_at": now,
        "dedupe_key": dedupe,
    }]


def baton_brief_lines(records):
    """One frozen line per baton-pass record for the next
    brief: job, previous worker, next worker, remaining
    file count. Other records render nothing."""
    lines = []
    records = records if isinstance(records, list) else []
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "baton-pass":
            continue
        baton = record.get("baton")
        remaining = baton.get("remaining_files") if isinstance(
            baton, dict) else None
        count = len(remaining) if isinstance(remaining, list) else 0
        lines.append("Baton passed job %s from %s to %s: "
                     "%d file(s) still to touch."
                     % (record.get("job"), record.get("from_worker"),
                        record.get("to_worker"), count))
    return lines
