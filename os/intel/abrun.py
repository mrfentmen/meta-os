"""intel/abrun.py -- measured A/B run + image-defect attribution (OS-106, Milo).

OS-106 executes the demo's one comparison: the same fixed
job suite run under a bare launch and under a mind image,
with times and acceptance outcomes recorded per job per
version, under watchdog measurement. A stall observed in
either run is then attributed, from its journal evidence,
as either an image defect or a worker failure. The point
is the discipline the spec states: when a stall traces
back to a missing skill, a bad instruction, or a thin
environment brief, it is recorded as an image defect
feeding the revision loop, not blamed on the worker.

This module is the run record and the attribution, not
the harness. The OS-105 A/B eval harness (Buffy) has
not landed, so the comparison here runs on fixture
versions and fixture job runs in the OS-105 shape: a
fixed suite, two versions, completion time and
acceptance result per job per version, side by side.
No live agent runs here, no process is started, no
bus post is made, and there is no push path, so a
run recorded here can never ring a phone on its own.
The revision note it produces is a proposal only:
nothing auto-applies, and the revision loop tooling
is Pax OS-109, which has not landed either.

Shapes, all plain dicts so fixtures stay readable:

- image version: {"name", "version", "skills": [...],
  "instructions": [...], "brief": "full", "thin", or
  "absent"}. A bare launch carries no skills, no
  instructions, and a thin brief. A mind image
  carries the skills, instructions, and full brief
  its version claims.
- job run: {"job", "seconds", "outcome": "pass" or
  "fail", "stalls": [...]}. Seconds is a number or
  None when the run never finished.
- stall: {"job", "reason", "journal": [lines],
  plus exactly the evidence the attribution needs:
  "missing_skill" naming a skill the worker needed,
  "bad_instruction" naming an instruction the worker
  followed, "thin_brief" True when the worker stalled
  for want of context, or "worker_cause" naming what
  the worker itself did (died, crashed, timed out
  with no image link)}.

Attribution, as a pure function of the stall and the
image version it ran under, checked in this order:

- missing skill: the stall names a skill, and that
  skill is absent from the image's skills layer.
  The journal evidence must name the skill; a claim
  that the image lacks a skill it actually carries
  is not a defect, and falls through.
- bad instruction: the stall names an instruction,
  and that instruction is present in the image's
  instructions layer. An instruction the image does
  not carry cannot be its defect.
- thin brief: the stall says the worker wanted
  context, and the image's brief is "thin" or
  "absent". A full brief is not a thin-brief defect.
- worker failure: the stall names a worker cause.
  A worker that died under a complete image is a
  worker failure, never an image defect.
- anything else is unattributed: evidence naming
  neither an image layer nor a worker cause proves
  neither, and the module says so instead of
  guessing.

The comparison never mutates its inputs. A run
missing for a job reads as outcome "missing" with
no seconds, never as a pass and never as a crash.
Malformed versions, runs, and stalls are skipped
silently, because a bad fixture must not invent a
result or break the run.
"""

import copy

__all__ = ["attribute_stall", "run_comparison",
           "revision_note", "measurement_records"]


def _text(value):
    """A string value, or None when it is not one."""
    if isinstance(value, str) and value:
        return value
    return None


def _string_list(value):
    """A list of strings, ignoring anything else."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _image_layers(image):
    """The skills, instructions, and brief of a version, or empties."""
    if not isinstance(image, dict):
        return [], [], "absent"
    skills = _string_list(image.get("skills"))
    instructions = _string_list(image.get("instructions"))
    brief = image.get("brief")
    if brief not in ("full", "thin", "absent"):
        brief = "absent"
    return skills, instructions, brief


def _journal_evidence(stall, needle):
    """Journal lines naming the needle, or the needle itself."""
    journal = _string_list(stall.get("journal"))
    hits = [line for line in journal if needle in line]
    if hits:
        return hits
    return [needle]


def attribute_stall(stall, image):
    """Attribute one stall: (kind, detail, evidence).

    Kind is "image-defect" with detail one of
    "missing-skill", "bad-instruction", "thin-brief";
    "worker-failure" with detail the worker cause; or
    "unattributed" with detail None. Evidence is the
    list of journal lines (or field values) the
    attribution rests on, so a reader can check it
    without re-running anything.
    """
    if not isinstance(stall, dict):
        return ("unattributed", None, [])
    skills, instructions, brief = _image_layers(image)
    skill = _text(stall.get("missing_skill"))
    if skill is not None and skill not in skills:
        return ("image-defect", "missing-skill",
                _journal_evidence(stall, skill))
    instruction = _text(stall.get("bad_instruction"))
    if instruction is not None and instruction in instructions:
        return ("image-defect", "bad-instruction",
                _journal_evidence(stall, instruction))
    if stall.get("thin_brief") is True and brief in ("thin", "absent"):
        journal = _string_list(stall.get("journal"))
        evidence = journal if journal else ["worker stalled for context"]
        return ("image-defect", "thin-brief", evidence)
    cause = _text(stall.get("worker_cause"))
    if cause is not None:
        journal = _string_list(stall.get("journal"))
        evidence = journal if journal else [cause]
        return ("worker-failure", cause, evidence)
    journal = _string_list(stall.get("journal"))
    reason = _text(stall.get("reason"))
    evidence = journal if journal else ([reason] if reason else [])
    return ("unattributed", None, evidence)


def _clean_run(run):
    """A run record in canonical shape, or None if unusable."""
    if not isinstance(run, dict):
        return None
    outcome = run.get("outcome")
    if outcome not in ("pass", "fail"):
        outcome = "missing"
    seconds = run.get("seconds")
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        seconds = None
    stalls = run.get("stalls")
    if not isinstance(stalls, list):
        stalls = []
    return {"outcome": outcome, "seconds": seconds,
            "stalls": [s for s in stalls if isinstance(s, dict)]}


def run_comparison(job_ids, runs_by_version, images_by_version):
    """Run the comparison: same jobs, every version, side by side.

    job_ids is the fixed suite, in order.
    runs_by_version maps a version name to a dict of
    job id to job run. images_by_version maps a
    version name to its image version record, for
    attribution; a version with no image record is
    attributed against an empty image, never skipped.

    Returns {"jobs", "versions", "table", "totals",
    "defects", "measurements"}. The table holds one
    row per job with one entry per version. Totals
    count jobs, passes, fails, seconds, and stalls
    per version. Defects hold every stall attributed
    as an image defect, with the job, the version,
    the kind, and the evidence. Measurements hold
    one watchdog-style observation per job per
    version: job, version, seconds, outcome, stall
    count, and defect kinds.
    """
    jobs = [job for job in job_ids if isinstance(job, str)] \
        if isinstance(job_ids, list) else []
    versions = []
    if isinstance(runs_by_version, dict):
        versions = [name for name in runs_by_version
                    if isinstance(name, str)]
    images = images_by_version if isinstance(images_by_version, dict) \
        else {}
    table = []
    totals = {}
    defects = []
    measurements = []
    for version in versions:
        totals[version] = {"jobs": 0, "passed": 0, "failed": 0,
                           "seconds": 0, "stalls": 0}
    for job in jobs:
        row = {"job": job, "versions": {}}
        for version in versions:
            runs = runs_by_version.get(version)
            raw = runs.get(job) if isinstance(runs, dict) else None
            run = _clean_run(raw)
            if run is None:
                run = {"outcome": "missing", "seconds": None,
                       "stalls": []}
            image = images.get(version)
            kinds = []
            for stall in run["stalls"]:
                kind, detail, evidence = attribute_stall(stall, image)
                if kind == "image-defect":
                    defects.append({"job": job, "version": version,
                                    "kind": detail, "evidence": evidence})
                    kinds.append(detail)
            row["versions"][version] = {
                "outcome": run["outcome"], "seconds": run["seconds"],
                "stalls": len(run["stalls"]), "defect_kinds": kinds}
            total = totals[version]
            total["jobs"] += 1
            if run["outcome"] == "pass":
                total["passed"] += 1
            elif run["outcome"] == "fail":
                total["failed"] += 1
            if run["seconds"] is not None:
                total["seconds"] += run["seconds"]
            total["stalls"] += len(run["stalls"])
            measurements.append({"job": job, "version": version,
                                 "seconds": run["seconds"],
                                 "outcome": run["outcome"],
                                 "stalls": len(run["stalls"]),
                                 "defect_kinds": kinds})
        table.append(row)
    return {"jobs": jobs, "versions": versions, "table": table,
            "totals": totals, "defects": defects,
            "measurements": measurements}


def measurement_records(comparison):
    """The watchdog measurement lines for a comparison result."""
    if not isinstance(comparison, dict):
        return []
    records = comparison.get("measurements")
    if not isinstance(records, list):
        return []
    lines = []
    for record in records:
        if not isinstance(record, dict):
            continue
        lines.append("job %s under %s: %s in %s seconds, %s stalls, "
                     "defects %s" % (
                         record.get("job"), record.get("version"),
                         record.get("outcome"), record.get("seconds"),
                         record.get("stalls"),
                         ",".join(record.get("defect_kinds") or [])
                         or "none"))
    return lines


def revision_note(defects):
    """A proposed next-version change per defect, deduped.

    Each entry names the layer to change and the
    evidence it rests on. This is a proposal for
    the revision loop (Pax OS-109), not an applied
    change: nothing here edits an image version.
    """
    if not isinstance(defects, list):
        return {"next_version_changes": [], "note": "no defects given"}
    seen = set()
    changes = []
    for defect in defects:
        if not isinstance(defect, dict):
            continue
        kind = defect.get("kind")
        evidence = defect.get("evidence")
        subject = evidence[0] if isinstance(evidence, list) \
            and evidence and isinstance(evidence[0], str) else None
        key = (kind, subject)
        if key in seen:
            continue
        seen.add(key)
        if kind == "missing-skill" and subject:
            changes.append("add skill %s to the skills layer "
                           "(evidence: %s)" % (subject, subject))
        elif kind == "bad-instruction" and subject:
            changes.append("remove or replace instruction %s "
                           "(evidence: %s)" % (subject, subject))
        elif kind == "thin-brief":
            changes.append("thicken the environment brief layer "
                           "for job %s (evidence: %s)"
                           % (defect.get("job"),
                              subject or "stall for context"))
        else:
            continue
    return {"next_version_changes": changes,
            "note": "proposal only; nothing auto-applies"}
