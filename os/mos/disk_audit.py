"""OS-128: disk-state audit test, first light.

The recovery law (plan/META_OS.md, "Recovery") says state lives
on disk, never in a session: whatever recovery needs must be
readable from the store by a process that has never met the
agent that wrote it. This module is the cold reader that
proves it. Given job records plus the two on-disk stores it
walks every job and reconstructs its complete state from
disk alone, with no bus, no Redis, and no live session:

- spec: title plus spec text, the job's own definition.
- goal: the goal key, else the Goal: line of the spec text
  (the DSP spec standard, same rule intel/baton.py uses).
- progress: progress_notes, else the latest note alone.
- remaining files: the job's files minus completed_files.
- acceptance: the accept field carried on the record.
- artifacts: every artifact:<job>/<name>@v<version> reference
  on the record checked against the OS-083 store manifest
  and read back from the store, so a reference to a missing
  manifest entry, a wrong version, or unreadable bytes is a
  leak, not a link.
- settled decisions: every memory key the record names under
  "decisions" checked against the OS-078 shared journal and
  the claiming agent's own journal. A key in neither is a
  leak: the decision lives only in a dead session's memory.

The audit passes only when the leak list is empty, per the
OS-128 acceptance rule. A leak names its layer (spec, baton,
claim, artifacts, memory, memory-journal, record) so the fix
task lands in the owning lane before the image freeze. A
corrupt memory journal is a loud failure, never a skipped
memory: mos/memory.py raises on a bad journal line, and the
audit files that as a memory-journal leak instead of reading
around it.

Job records arrive as dicts in the jobs.py show shape
(title, status, spec, files, note, progress_notes,
completed_files, accept, claim, artifacts, decisions).
Exporting live queue hashes to that shape on disk is owed
wiring beside OS-094; this module audits the shape, it does
not invent a second queue. An empty store is a real state,
not a failure: a job with no artifacts and no named decisions
passes those checks vacuously, and a missing memory or
artifact root reads as empty, not as an error.

What this batch does NOT claim (stated plainly, as every
first-light batch in this repo does): no kill-every-process
run has happened on a booted test image, so the audit has
not yet graded a real mid-work machine; the live jobs.py
export to disk is not wired yet; and a leak list found on a
real image still needs its owning-lane fix task, which this
batch does not file. No bus post, no live Redis, no network:
the audit reads local files only.
"""

import argparse
import json
import os
import re
import sys

from mos import artifact_store, memory

ARTIFACT_REF_RE = re.compile(r"^artifact:([^/]+)/(.+)@v(\d+)$")


class DiskAuditError(ValueError):
    """Unreadable audit input: not a job record, not JSON, not a list."""


def _text(value):
    """A stripped string, else None: empty text is not a value."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _str_list(value):
    """A list of non-empty strings, else []: never guesses a shape."""
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    if isinstance(value, str) and value:
        return [value]
    return []


def _goal(record):
    """Goal key, else the Goal: line of spec text, else None."""
    goal = _text(record.get("goal"))
    if goal is not None:
        return goal
    spec = record.get("spec")
    if isinstance(spec, str):
        for line in spec.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("goal:"):
                return _text(stripped[len("goal:"):])
    return None


def _progress_notes(record):
    """Deposited progress: progress_notes, else the latest note."""
    notes = _str_list(record.get("progress_notes"))
    if notes:
        return notes
    note = _text(record.get("note"))
    return [note] if note is not None else []


def _remaining_files(record):
    """Files still to touch: files minus completed_files, in order."""
    files = _str_list(record.get("files"))
    completed = set(_str_list(record.get("completed_files")))
    return [path for path in files if path not in completed]


def _parse_artifact_ref(ref):
    """(job_id, name, version) for an OS-083 reference, else None."""
    match = ARTIFACT_REF_RE.match(ref)
    if match is None:
        return None
    return match.group(1), match.group(2), int(match.group(3))


def _read_shared_keys(memory_root, leaks):
    """Latest shared decisions, or {} with a journal leak filed."""
    if not os.path.isdir(memory_root):
        return {}
    try:
        return memory.list_shared_keys(memory_root)
    except memory.MemoryError as exc:
        leaks.append({
            "job": None,
            "layer": "memory-journal",
            "detail": "shared journal unreadable: %s" % exc,
        })
        return {}


def _read_agent_keys(memory_root, agent, leaks, journal_leaked):
    """Latest own decisions for one agent, or {} with a leak filed."""
    if not os.path.isdir(memory_root):
        return {}
    try:
        return memory.list_keys(memory_root, agent)
    except memory.MemoryError as exc:
        if agent not in journal_leaked:
            journal_leaked.add(agent)
            leaks.append({
                "job": None,
                "layer": "memory-journal",
                "detail": "journal for %s unreadable: %s" % (agent, exc),
            })
        return {}
    except ValueError:
        return {}


def _verify_artifacts(artifact_root, record, job_id, leaks):
    """Artifact references checked against the store; verified list."""
    verified = []
    for ref in _str_list(record.get("artifacts")):
        parsed = _parse_artifact_ref(ref)
        if parsed is None:
            leaks.append({
                "job": job_id,
                "layer": "artifacts",
                "detail": "unparseable artifact reference: %s" % ref,
            })
            continue
        ref_job, name, version = parsed
        try:
            entries = {
                entry["name"]: entry
                for entry in artifact_store.list_artifacts(artifact_root, ref_job)
            }
        except artifact_store.ArtifactStoreError as exc:
            leaks.append({
                "job": job_id,
                "layer": "artifacts",
                "detail": "store unreadable for %s: %s" % (ref, exc),
            })
            continue
        entry = entries.get(name)
        if entry is None:
            leaks.append({
                "job": job_id,
                "layer": "artifacts",
                "detail": "no manifest entry for %s" % ref,
            })
            continue
        if entry.get("version") != version:
            leaks.append({
                "job": job_id,
                "layer": "artifacts",
                "detail": "manifest holds v%s, record references %s"
                % (entry.get("version"), ref),
            })
            continue
        try:
            artifact_store.read(artifact_root, ref_job, name, version)
        except artifact_store.ArtifactStoreError as exc:
            leaks.append({
                "job": job_id,
                "layer": "artifacts",
                "detail": "artifact bytes unreadable for %s: %s" % (ref, exc),
            })
            continue
        verified.append(ref)
    return verified


def audit(memory_root, artifact_root, job_records):
    """Audit job records against the on-disk stores.

    Returns {"jobs": [...], "decisions": [...], "leaks": [...],
    "passed": bool}. "jobs" carries one reconstructed record
    per input job; "decisions" is the sorted list of shared
    decision keys the cold reader could see; "leaks" is empty
    exactly when every job's state is fully reconstructable.
    """
    if not isinstance(job_records, list):
        raise DiskAuditError("job records must be a list")
    leaks = []
    shared = _read_shared_keys(memory_root, leaks)
    journal_leaked = set()
    agent_cache = {}
    jobs_out = []
    for record in job_records:
        if not isinstance(record, dict):
            leaks.append({
                "job": None,
                "layer": "record",
                "detail": "job record is not an object",
            })
            continue
        job_id = _text(record.get("id")) or _text(record.get("job_id"))
        if job_id is None:
            leaks.append({
                "job": None,
                "layer": "record",
                "detail": "job record carries no id",
            })
            continue
        spec = _text(record.get("spec"))
        title = _text(record.get("title"))
        if title is None or spec is None:
            leaks.append({
                "job": job_id,
                "layer": "spec",
                "detail": "cold reader cannot tell what this job is",
            })
        status = _text(record.get("status"))
        goal = _goal(record)
        if status == "claimed" and goal is None:
            leaks.append({
                "job": job_id,
                "layer": "baton",
                "detail": "claimed job has no goal for the next worker",
            })
        claimer = _text(record.get("claim"))
        if status == "claimed" and claimer is None:
            leaks.append({
                "job": job_id,
                "layer": "claim",
                "detail": "claimed job names no holder or lease",
            })
        verified = _verify_artifacts(artifact_root, record, job_id, leaks)
        decisions_ok = []
        for key in _str_list(record.get("decisions")):
            found = key in shared
            if not found and claimer is not None:
                if claimer not in agent_cache:
                    agent_cache[claimer] = _read_agent_keys(
                        memory_root, claimer, leaks, journal_leaked)
                found = key in agent_cache[claimer]
            if found:
                decisions_ok.append(key)
            else:
                leaks.append({
                    "job": job_id,
                    "layer": "memory",
                    "detail": "decision %s in no journal the reader can see" % key,
                })
        jobs_out.append({
            "id": job_id,
            "status": status,
            "title": title,
            "spec": spec,
            "goal": goal,
            "progress_notes": _progress_notes(record),
            "remaining_files": _remaining_files(record),
            "accept": record.get("accept"),
            "artifacts": verified,
            "decisions": decisions_ok,
        })
    return {
        "jobs": jobs_out,
        "decisions": sorted(shared),
        "leaks": leaks,
        "passed": not leaks,
    }


def main(argv=None):
    """CLI: audit a jobs JSON file against two store roots.

    Exit 0 when the leak list is empty, 1 when leaks are
    found, 2 when the input itself cannot be read.
    """
    parser = argparse.ArgumentParser(
        description="OS-128 disk-state audit: reconstruct jobs from disk.")
    parser.add_argument("--jobs", required=True,
                        help="JSON file holding a list of job records")
    parser.add_argument("--memory-root", required=True,
                        help="OS-078 memory store root")
    parser.add_argument("--artifact-root", required=True,
                        help="OS-083 artifact store root")
    args = parser.parse_args(argv)
    try:
        with open(args.jobs, encoding="utf-8") as handle:
            job_records = json.load(handle)
    except (OSError, ValueError) as exc:
        print("RELAY_ERROR: cannot read jobs file: %s" % exc, file=sys.stderr)
        return 2
    try:
        result = audit(args.memory_root, args.artifact_root, job_records)
    except DiskAuditError as exc:
        print("RELAY_ERROR: %s" % exc, file=sys.stderr)
        return 2
    for job in result["jobs"]:
        print("%s %s goal=%s progress=%d remaining=%d artifacts=%d" % (
            job["id"],
            job["status"] or "unknown",
            job["goal"] or "-",
            len(job["progress_notes"]),
            len(job["remaining_files"]),
            len(job["artifacts"]),
        ))
    print("decisions visible: %d" % len(result["decisions"]))
    if result["passed"]:
        print("PASS: no leaks, every job reconstructable from disk")
        return 0
    for leak in result["leaks"]:
        print("LEAK %s %s: %s" % (
            leak["job"] or "-", leak["layer"], leak["detail"]))
    print("FAIL: %d leak(s)" % len(result["leaks"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
