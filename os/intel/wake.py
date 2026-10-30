"""intel/wake.py -- Muse wake adapter (OS-119, Milo).

When the bell rings for a sleeping Muse instance (the
Hana and Rowan class of runtime), the adapter starts
the agent's session through its runtime's session
mechanism with the job already in its hands: spec,
mind image via the OS-102 loader, and acceptance
checks. The agent's first act is the job, never a
poll: its first bus action is the claim or the first
progress note on that job, not a status check.

This module is the decision and the bundle, not the
hands. It judges whether a sleeping fixture agent
should wake for a posted job, composes the bundle
that session starts with, and journals one wake
record per wake. It never starts a real session,
never touches a process, never posts to the bus,
and has no push path, so a wake judged here can
never ring a phone on its own. The mechanical half
is not here: the resident watchman that actually
rings is Pax OS-118, the session mechanism it calls
into is the Muse runtime's own, and the mind image
loader is OS-102, which has not landed. A bundle
whose job carries no mind image reference says so
plainly instead of inventing one.

Wake rule, as a pure function of the job and the
agent record:

- the agent is asleep (asleep True) and its runtime
  is muse. A runtime that is not muse is not this
  adapter's business, and an awake agent needs no
  wake: both yield no wake.
- the job is addressed to that agent, and only that
  agent. A job addressed to a different agent does
  not wake this one, whatever else matches.
- the job has an id. An anonymous job cannot be
  claimed, so it cannot wake anyone.
- anything else (a non-record, a missing nick, a
  missing address, a malformed bundle field) yields
  no wake and no crash. Missing evidence is never
  read as permission to wake a stranger.

Bundle contents: the job id, the agent nick, the
machine, the goal (the job goal key, else the Goal
line of a spec text), the spec text when the job
carries one, the acceptance checks, the files, and
the mind image reference when the job carries one.
When the job carries no mind image reference, the
bundle carries mind_image None plus a note naming
the OS-102 loader as pending, so the gap is visible
in the bundle itself rather than hidden by a made
up reference.

Journal and dedupe: wake_tick journals one wake
record per job and agent pair, dedupe
wake:<job>:<agent>. A second tick over the same
pair journals nothing new: a sleeping agent that
already has its bundle is not woken twice. A wake
record is open until the agent's session starts;
the drill's fake runtime applies the start, and the
start is what turns a wake record into a claim.
The tick never mutates its jobs, agents, or journal:
it returns new records only, and the caller appends
them.

First act rule: the bundle is the session's first
input, so the session's first bus action is the
claim of the bundled job or progress on it. A
session that starts by asking for status has not
used the bundle, and the drill fails such a start
on purpose: the fake runtime records its first bus
action, and the drill asserts it is claim or
progress, never status.
"""

import copy


def _text(value):
    """A stripped non-empty string, else None."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _str_list(value):
    """A list of non-empty strings from a list or a
    comma-separated string, deduped in order. Anything
    else reads as an empty list, never a crash."""
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return list(dict.fromkeys(part for part in parts if part))
    if isinstance(value, list):
        parts = [part.strip() for part in value
                 if isinstance(part, str) and part.strip()]
        return list(dict.fromkeys(parts))
    return []


def _lines(value):
    """Acceptance lines from a list or a newline
    separated string, deduped in order, empties
    dropped."""
    if isinstance(value, str):
        parts = [line.strip() for line in value.splitlines()]
        return list(dict.fromkeys(line for line in parts if line))
    if isinstance(value, list):
        parts = [line.strip() for line in value
                 if isinstance(line, str) and line.strip()]
        return list(dict.fromkeys(parts))
    return []


def _spec_goal(job):
    """The Goal line of a spec text, or the goal key
    of a spec dict, else None."""
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


def _spec_text(job):
    """The spec as text, or None when the job carries
    no spec text. A spec dict renders as its goal
    line only, so the bundle never invents spec text
    the job did not carry."""
    spec = job.get("spec")
    if isinstance(spec, str):
        return _text(spec)
    if isinstance(spec, dict):
        goal = _text(spec.get("goal"))
        return "Goal: %s" % goal if goal is not None else None
    return None


def _acceptance(job):
    """Acceptance checks as a line list, from
    acceptance_checks, accept, or acceptance, in that
    order. The first non-empty source wins; sources
    are never merged, because a merged list could
    double a check."""
    if not isinstance(job, dict):
        return []
    for field in ("acceptance_checks", "accept", "acceptance"):
        checks = _lines(job.get(field))
        if checks:
            return checks
    return []


def _addressed_to(job):
    """Who the job is addressed to, from addressed_to,
    then to, else None."""
    if not isinstance(job, dict):
        return None
    for field in ("addressed_to", "to"):
        value = _text(job.get(field))
        if value is not None:
            return value
    return None


def _agent_nick(agent):
    """The agent nick, from nick, then name, else
    None."""
    if not isinstance(agent, dict):
        return None
    for field in ("nick", "name"):
        value = _text(agent.get(field))
        if value is not None:
            return value
    return None


def is_sleeping_muse(agent):
    """True only for a record that is asleep and
    whose runtime is muse. Anything else is not this
    adapter's wake: awake agents, other runtimes, and
    malformed records all read False."""
    if not isinstance(agent, dict):
        return False
    if agent.get("asleep") is not True:
        return False
    runtime = _text(agent.get("runtime"))
    return runtime is not None and runtime.lower() == "muse"


def should_wake(job, agent):
    """True only when the sleeping Muse agent is the
    job's addressee and the job has an id. Every
    other combination reads False, never a crash."""
    if not isinstance(job, dict) or not isinstance(agent, dict):
        return False
    if not is_sleeping_muse(agent):
        return False
    job_id = _text(job.get("id"))
    if job_id is None:
        return False
    nick = _agent_nick(agent)
    if nick is None:
        return False
    return _addressed_to(job) == nick


def compose_bundle(job, agent):
    """The bundle a woken session starts with, or
    None when the pair should not wake. The bundle
    carries the job, not a restatement of it: goal,
    spec text, acceptance checks, files, and the mind
    image reference when the job carries one. When
    the job carries no mind image reference, the
    bundle says the OS-102 loader is pending instead
    of inventing a reference."""
    if not should_wake(job, agent):
        return None
    mind_image = None
    for field in ("mind_image", "mind_image_ref"):
        value = _text(job.get(field))
        if value is not None:
            mind_image = value
            break
    bundle = {
        "job_id": _text(job.get("id")),
        "agent": _agent_nick(agent),
        "machine": _text(agent.get("machine")),
        "goal": _goal(job),
        "spec": _spec_text(job),
        "acceptance_checks": _acceptance(job),
        "files": _str_list(job.get("files")),
        "mind_image": mind_image,
    }
    if mind_image is None:
        bundle["mind_image_note"] = (
            "mind image loader pending (OS-102, not landed); "
            "bundle carries the job without a mind image "
            "rather than inventing one"
        )
    return bundle


def dedupe_key(job_id, agent_nick):
    """The journal dedupe key for one wake."""
    return "wake:%s:%s" % (job_id, agent_nick)


def wake_tick(jobs, agents, journal, now=0):
    """One wake tick: one new wake record per
    sleeping Muse agent addressed by a posted job,
    unless that pair already has a wake record in
    the journal. Returns the new records only; the
    caller appends them. Inputs are never mutated,
    and malformed jobs, agents, or journal entries
    yield no records and no crash."""
    if not isinstance(jobs, list):
        jobs = []
    if not isinstance(agents, list):
        agents = []
    seen = set()
    if isinstance(journal, list):
        for record in journal:
            if isinstance(record, dict):
                key = _text(record.get("dedupe_key"))
                if key is not None:
                    seen.add(key)
    new_records = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            if not should_wake(job, agent):
                continue
            key = dedupe_key(_text(job.get("id")),
                             _agent_nick(agent))
            if key in seen:
                continue
            seen.add(key)
            new_records.append({
                "kind": "wake",
                "dedupe_key": key,
                "job": _text(job.get("id")),
                "agent": _agent_nick(agent),
                "machine": _text(agent.get("machine")),
                "bundle": copy.deepcopy(compose_bundle(job, agent)),
                "created_at": now,
            })
    return new_records


def brief_lines(records):
    """One brief line per wake record, in record
    order. Other record kinds render nothing, so a
    mixed journal briefs only its wakes."""
    lines = []
    if not isinstance(records, list):
        return lines
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("kind") != "wake":
            continue
        lines.append("Wake: %s woken for job %s on %s" % (
            _text(record.get("agent")) or "?",
            _text(record.get("job")) or "?",
            _text(record.get("machine")) or "?",
        ))
    return lines
