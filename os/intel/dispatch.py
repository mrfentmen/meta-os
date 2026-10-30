"""intel/dispatch.py — plain-English goal -> structured job specs.

Turns a goal into a plan of job specs (files owned, dependencies,
attempt budgets, machine-checkable acceptance), records the plan
through intel.store.put_dispatch, and — only after the human
approval gate — signs each job with the existing jobs.py HMAC
signing and posts it to the existing queue. Dispatch never
auto-posts: every plan passes the approval gate first (hard rule,
MASTER_PLAN).

DSP-002 (this task): the plan parser. parse_plan(text) validates a
Spark-produced plan JSON strictly against the DSP-001 output schema
and returns the normalized plan dict, or raises PlanError with a
specific message naming the broken field. Schema checks here are
shape only: field presence, types, non-empty files per job, at least
one parseable accept line per job (via mos/acceptance.parse_accept),
unique plan-local keys, and no unknown fields.

DSP-003 (this task): the file-overlap guard.
check_file_overlap(plan) takes a parse_plan output and raises
PlanError when two jobs in the plan own the same path, unless the
overlap is shared-sequential: for every consecutive pair of owners
of a path, in plan order, the later job must list the earlier job
in its deps AND its spec must mark the path shared-sequential, by
containing the token "shared-sequential" together with the path
itself (matched case-insensitively, e.g. "shared-sequential:
intel/ingest.py"). A chain of three or more owners of one path is
allowed when every consecutive pair meets both conditions; ordering
past the immediate predecessor is transitive through the chain, so
no direct dep on a non-adjacent owner is required. The guard never
posts, never claims, and never touches the bus. It is deliberately
separate from parse_plan: the parser stays shape-only (DSP-002
tests pin that an overlap passes the parser), and callers compose
the two, e.g. check_file_overlap(parse_plan(text)).

DSP-004 (this task): the dependency graph check.
check_dep_graph(plan) takes a parse_plan output and returns the
posting order: a list of job keys in which every job appears after
all of its deps, computed by depth-first traversal in plan order
(ties keep plan order, so the order is deterministic). It raises
PlanError when a dep names a key that is not a job in the plan, or
when the deps form a cycle — the cycle error names the full cycle,
e.g. "dependency cycle: a -> b -> a", including a self-dep
("a -> a"). The check never posts, never claims, and never touches
the bus. It is separate from parse_plan for the same reason as the
overlap guard: the parser stays shape-only (DSP-002 tests pin that
an unknown dep key passes the parser), and callers compose the
checks, e.g. check_dep_graph(check_file_overlap(parse_plan(text))).
The returned order is what DSP-008 posts in: deps resolve to real
job ids only because the poster walks this order.

DSP-005 (this task): attempt-budget clamping.
clamp_attempt_budgets(plan) takes a parse_plan output and returns
a (new_plan, clamps) pair: every job's max_attempts is clamped
into 1..5 (default 3, per-job overrides honored inside the range),
and clamps lists one {key, requested, clamped} entry per job whose
value actually changed, in plan order. The parser itself stays
shape-only: an out-of-range integer still parses unclamped
(DSP-002 tests pin that), and callers compose the two, e.g.
clamp_attempt_budgets(parse_plan(text)). plan_summary(plan,
clamps) renders the plan for a human: the summary line, one line
per job, and one line per clamp, so a clamp is always reported,
never silent. Neither function posts, claims, or touches the bus.

DSP-006 (this task): the dispatch dry-run.
dry_run_plan(text) runs the whole read-only pipeline over a
Spark-produced plan JSON string — parse, overlap guard, dep graph,
budget clamp — and returns the full rendered plan from
render_plan_detail: the summary line, the posting order, and one
block per job (title, files, deps, attempt budget, accept lines),
plus one line per clamp. The dry-run takes the plan as input
(--plan file on the CLI): it does not call Spark itself, because
the live goal -> plan Spark step is DSP-015's demo-goal work and
no plan may be invented here. A plan that fails any check raises
PlanError and prints nothing, so a dry-run never shows a plan
that would not survive the real gates. It posts nothing, claims
nothing, writes no dispatch record, and touches no job state:
jobs list before and after a dry-run is identical, by
construction (this module never imports jobs, store, or the bus).

Deliberately NOT in the parser, because a later task owns it:
  DSP-026 spec content standard (goal/context/files/steps/
    out-of-scope parts): the parser requires a non-empty spec
    string only, not its internal structure. (DSP-013, the
    plan-size guardrail, has landed since: it lives in
    plan_size_warnings plus the approval and poster gates
    below, not in the parser, so the parser stays shape-only
    for size exactly as before.)
Deliberately NOT in the parser, because later tasks own them:
DSP-026 is also not a parser gate, by design: the spec content
standard (goal/context/files/steps/out-of-scope parts) is scored
by score_spec_parts / score_plan_specs below, in the same
separate-guard pattern as DSP-028 — the parser requires a
non-empty spec string only, not its internal structure, so
short guard-fixture specs (contradiction cases, overlap cases)
still parse while golden runs are scored against the standard.
Parsing, overlap guard, dep graph, and budget clamping are
DSP-002/003/004/005; the poster is DSP-008. The parser never
posts, never claims, never announces, and never touches the bus.

DSP-007 (this task): the plan approval gate.
request_approval(plan, approve=False, confirm=None) is the single
place a plan becomes postable, and it never approves on its own:
approve=True means the caller already holds a human approval —
the CLI --approve flag, or the dashboard approve action after
the signed-in human confirms (DSP-037 payload, DSH-011 button
label "Post N jobs") — and confirm is an interactive prompt
function (input) whose answer must be exactly y/yes. Anything
else — no flag, no prompt, an answer other than y/yes, an
EOFError from the prompt, a non-interactive stdin — is a denial.
The gate itself never posts, never claims, and never touches
job state: it returns True/False and the caller (DSP-008's
poster) acts only on True. Until the poster lands, the CLI
refuses posting even after approval, loudly, with DSP-008
named — approval passed is never reported as posted. The
dashboard path has no other route in: a preview render, a
timer, or a default never counts as approval.

DSP-028 (this task): the secret guard. check_no_secrets(text)
scans a goal text or a plan JSON text for credential-shaped
strings (the same shapes BRF-014 redacts in briefs) and raises
PlanError with a "secret warning" naming the shape found, never
the value itself. It is deliberately separate from parse_plan,
like the overlap and dep-graph guards: the parser stays
shape-only, and callers compose the guard at both ends of the
Spark call — on the goal text before it is sent, and on the
plan text at parse time — so a fake key in either place is
refused and nothing is posted, claimed, or announced. The
prompt ban is the other half: intel/prompts/dispatch.md hard
rule 2 already tells Spark to refuse a goal carrying a secret;
this guard is the machine enforcement when Spark does not.

DSP-008 (this task): the plan poster. post_plan(plan, order)
walks the DSP-004 posting order and posts each job through
jobs.py main() — title, spec, accept lines, files, rewritten
deps, and attempt budget — mapping each plan key to the real
job id jobs.py returns, so a dependent's deps are the real
ids of jobs already posted, never plan keys. On full success
it stores one dispatch record via intel.store.put_dispatch
under muse-bus:intel:dispatch:<id> (the plan summary, the
posting order, and the key -> id mapping with each job's
files, real deps, and budget) and returns that record. On a
failed post it raises PostError naming the failed key and
the jobs already posted — those stay posted, there is no
unpost, and no record is stored claiming a full plan. The
poster announces nothing by default: the only bus lines
are the JOB: lines jobs.py itself writes. DSP-010: when
the caller passes announce, a callable taking one line,
the poster calls it with
format_dispatch_announcement(record) after the record
is stored; a callable that raises is logged as a WARNING
to stderr and never fails a post that already succeeded.
With no announce callable the poster stays silent.

DSP-009 (this task): signing and the crew-mode rule.
post_plan accepts secret_file and crew_mode. When a
secret_file is given, every job is posted with
--secret-file so jobs.py signs it with the crew keyring's
HMAC (v2, bound to the job id), and the dispatch record
carries signed=True; every posted job then verifies OK via
jobs.py verify against the same keyring. When no
secret_file is given and crew_mode is off, the poster
still posts but prints a loud WARNING to stderr that the
plan posts unsigned (a crew verifying signatures sees
those jobs as UNSIGNED) and the record carries
signed=False. When crew_mode is on and no secret_file is
given, the poster refuses before posting anything:
PostError naming crew mode, with zero jobs posted and no
record stored. A bad keyring is not a silent unsigned
post: jobs.py returns nonzero, so the poster fails at
that job under the DSP-008 partial-failure contract.
The jobs and store imports are lazy, inside the poster, so
the pure pipeline above stays importable with no queue and
no bus, exactly as its docstrings promise.

DSP-013 (this task): the plan-size guardrail.
plan_size_warnings(plan) is pure and shape-only like the other
guards: it returns one warning string per breached limit, and
an empty list when the plan is inside both limits. The limits
are MAX_PLAN_JOBS (12 jobs) and MAX_PLAN_FILES (40 distinct
files across the plan's jobs). A warning names the count, the
limit, the second confirmation the plan now needs, and a split
suggestion: break the plan into smaller plans inside the
limits, posted in dependency order, each approved separately.
The guard is deliberately NOT in parse_plan: the parser stays
shape-only (DSP-002 tests pin that a 13-job plan parses), and
callers compose the guard where a human looks at the plan:
dry_run_plan appends the warnings to the rendered detail, so
a dry-run shows the guard message, and request_approval plus
post_plan enforce the second confirmation, so a large plan
posts only when the human confirms twice. The guard never
posts, never claims, and never touches the bus on its own.

DSP-011 (this task): dispatch undo. undo_dispatch(dispatch_id)
reads the dispatch record stored by post_plan and walks its
jobs in posting order, reading each job's current state
fresh from the queue. An open job is cancelled through
jobs.py cancel (status "cancelled", never claimable again);
a claimed job is work in progress and is left untouched and
reported with its claim nick; a done, blocked, failed-final,
or already cancelled job is left untouched and reported with
its status; a job id that no longer exists is reported as
missing. The report is returned and stored on the dispatch
record under "undo" with "undone_at", so a second undo of
the same dispatch cancels nothing new and reports the
cancelled jobs as untouched. The undo announces nothing and
touches no job outside the plan's record.

DSP-014 (this task): dispatch spend and latency logging.
Every successful post_plan run appends one entry to the
FND-007 spend ledger via intel.store.record_spend, with
lane_feature "dispatch", the dispatch record id, the number
of jobs posted, and the wall time the post took in
milliseconds. Posting itself makes no Spark call, so the
entry carries no token counts and no cost: tokens_in,
tokens_out, and est_cost are None, and the running spend
total is unchanged by it. The same latency is stored on
the dispatch record itself as latency_ms, so
dispatch --show can report it without reading the ledger.
The ledger is observability only, exactly as in the Spark
client: a failed ledger write is logged to stderr and never
fails a post that already succeeded. Refused posts (size
guardrail, crew mode) and failed posts write no entry,
because no plan was posted and no dispatch record exists.

DSP-015 (this task): the demo goal script, in
hackathon/demo_goal.py with its plan in
hackathon/demo_goal_plan.json (the DEMO.md goal, the G5 golden
plan). The script dry-runs that plan 5 times through
validated_plan and checks every run yields the same job count
(5), the same file ownership per job, and the same posting
order (module -> panel -> tests -> docs -> review), plus the
G5 shape, the DSP-026 spec standard, and the DSP-027
acceptance standard, and writes the result to
hackathon/demo_goal_stability.md. The plan is the
hand-authored demo draft, not Spark output: live Spark
transport is blocked (GOV-001), so the script proves the
deterministic dry-run pipeline stable, not a live Spark call
stable, and its report says so. It posts, claims, and
announces nothing.

DSP-016 (this task): the plan diff view.
show_dispatch(dispatch_id) reads the dispatch record stored
by post_plan and walks its jobs in posting order, reading
each job's current state fresh from the queue, and returns
the plan as posted (key, job id, title, files, deps, attempt
budget) next to its current state (open, claimed, done,
blocked, cancelled, failed-final, or missing when the job id
is no longer in the queue), with the claim nick for claimed
jobs and a per-status count. It is read-only: it never
posts, claims, cancels, or writes the dispatch record, so
showing twice reports the same plan and only the job states
can move between shows. render_dispatch_show turns the
report into the plain lines the CLI prints, with plan-local
dep ids translated back to plan keys. An unknown dispatch
id raises ShowError before anything is read.

DSP-017 (this task): the Spark dispatch failure fallback.
plan_from_spark(goal, complete) asks a Spark completion callable
for a plan, twice at most: the first malformed JSON answer gets
one retry, and a second malformed answer in a row falls back to
fallback_plan(goal) — a single job carrying the raw goal as its
spec, clearly marked FALLBACK in its summary, title, and spec.
Only malformed JSON triggers the retry and the fallback: a
structured plan that fails a guard (overlap, cycle, secret) is
refused as PlanError on the first attempt, because retrying
the same Spark call cannot fix a guard failure and falling
back would throw away a structured plan for a fixable fault.
INT-008 extends the fallback to a Spark transport error from
complete: when the endpoint is down, complete raises instead
of answering, and the drill's acceptance (dispatch falls back
when Spark is down) requires the same FALLBACK job rather than
a propagated error. A transport error is not a structured-plan
fault, so nothing structured is thrown away, and the fallback
still needs DSP-007 approval before it can post. The fallback job deliberately carries no files and no
accept lines: Spark supplied nothing usable to derive them
from, and inventing files or checks would break the lane's
no-invention rule. It still posts through the normal
DSP-008 poster (which needs no files or accept lines to
post) and only after the DSP-007 human approval gate, so
the FALLBACK marking is what the approver sees before
anything reaches the queue. Nothing malformed is ever
posted: the malformed answers are discarded, and the loud
FALLBACK warning goes to stderr as well as into the
returned result. No live Spark call is made here — complete
is caller-supplied (the resident-agent or HTTP transport
from intel/spark_client.py once GOV-001 names the
endpoint/key); tests inject a callable, never a fake
transport in the product.

DSP-019 (this task): verifying a dispatched job is claimable by
the mos worker loop unchanged. No worker code changes and no new
dispatch function: tests/test_intel_dispatch_worker.py posts a
validated two-job plan through post_plan, delivers each JOB
announcement through the same DM dead-drop overseer.dispatch
uses, and runs the shipped mos.worker.Worker.run_once over it,
then verifies each finished job with mos.overseer.verify_done.
The chain proves the plan's real dep ids, files, and attempt
budgets survive claim and completion, that a dependent job waits
until its dep is done and its own DM arrives, and that a posted
job with no DM is never claimed by the loop. The worker loop is
unchanged by this task: the batch touches only this docstring
and the new test file.

DSP-010 (this task): the plan announcement line.
format_dispatch_announcement(record) is pure: it takes a
dispatch record stored by post_plan and returns exactly one
frozen-format line, "DISPATCH:<id> -> <n> jobs", where <id>
is the record id verbatim and <n> is the number of jobs
actually posted (len(record["jobs"])), or None when the
record cannot carry a line (not a dict, no id, an id with
whitespace, or no jobs list). The line carries no job
titles, file lists, or specs, exactly as the FND-020
freeze requires, so it can never smuggle a second message
or a secret onto the bus. This module posts nothing
itself: post_plan takes an optional announce callable and
calls it with the line only after the record is stored,
and with no callable it announces nothing, mirroring the
WDG-015 gate. The caller decides whether, and where, a
line goes; bus posting itself stays held under GOV-002
until Dale approves posting, and the CLI only prints the
line with --announce, it never pushes it to the bus.

Status: DSP-002, DSP-003, DSP-004, DSP-005, DSP-006, DSP-007,
DSP-008, DSP-009, DSP-010, DSP-011, DSP-013, DSP-014,
DSP-015, DSP-016,
DSP-017, DSP-018 (prompt hints only, no code check),
DSP-019 (integration test only, no worker change),
DSP-026 and DSP-027 (scorers only, not parser
gates), and DSP-028 implemented.
"""

import json
import re
import sys
import time

from mos import acceptance

__all__ = ["PlanError", "PostError", "UndoError", "ShowError",
           "parse_plan",
           "check_file_overlap", "check_dep_graph",
           "clamp_attempt_budgets", "plan_summary",
           "plan_paragraph",
           "render_plan_detail", "dry_run_plan", "validated_plan",
           "fallback_plan", "plan_from_spark",
           "approval_prompt", "request_approval",
           "check_no_secrets", "post_plan",
           "format_dispatch_announcement", "undo_dispatch",
           "show_dispatch", "render_dispatch_show",
           "score_accept_lines", "score_plan_accepts",
           "plan_size_warnings", "large_plan_prompt",
           "DEFAULT_MAX_ATTEMPTS", "MIN_MAX_ATTEMPTS",
           "MAX_MAX_ATTEMPTS", "MAX_PLAN_JOBS", "MAX_PLAN_FILES"]

DEFAULT_MAX_ATTEMPTS = 3
MIN_MAX_ATTEMPTS = 1
MAX_MAX_ATTEMPTS = 5
MAX_PLAN_JOBS = 12
MAX_PLAN_FILES = 40

_KEY_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_TOP_FIELDS = {"summary", "jobs"}
_JOB_FIELDS = {"key", "title", "spec", "files", "deps", "max_attempts",
               "accept", "req"}


class PlanError(ValueError):
    """A plan failed strict schema validation; message names the fault."""


def _fail(msg):
    raise PlanError(msg)


def _require_str(obj, field, where):
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"{where}: {field!r} must be a non-empty string")
    return value


def _unknown_fields(obj, allowed, where):
    extra = sorted(set(obj) - allowed)
    if extra:
        _fail(f"{where}: unknown field(s): {', '.join(extra)}")


def parse_plan(text):
    """Parse and strictly validate a dispatch plan JSON string.

    Returns the normalized plan dict:
    {"summary": str, "jobs": [{key, title, spec, files, deps,
    max_attempts, accept, req}, ...]} in the input order. Missing deps
    defaults to []; missing max_attempts defaults to
    DEFAULT_MAX_ATTEMPTS (3); missing req defaults to [].
    A present req must be a list of non-empty strings, normalized
    to lowercase, stripped, and deduped in order (DSP-012: the
    capability names the goal says the worker must have, in the
    same form mos/capabilities.find_for matches). Raises PlanError on the first fault
    found, with the job key (once known) and field in the message.
    """
    if not isinstance(text, str) or not text.strip():
        _fail("plan: empty input, expected a JSON plan object")
    try:
        plan = json.loads(text)
    except json.JSONDecodeError as exc:
        _fail(f"plan: not valid JSON: {exc}")
    if not isinstance(plan, dict):
        _fail("plan: top level must be a JSON object, not "
              f"{type(plan).__name__}")
    _unknown_fields(plan, _TOP_FIELDS, "plan")
    summary = _require_str(plan, "summary", "plan")
    if "jobs" not in plan:
        _fail("plan: missing required field 'jobs'")
    jobs = plan["jobs"]
    if not isinstance(jobs, list) or not jobs:
        _fail("plan: 'jobs' must be a non-empty list")
    seen_keys = set()
    out_jobs = []
    for index, job in enumerate(jobs):
        where = f"plan job {index}"
        if not isinstance(job, dict):
            _fail(f"{where}: job must be a JSON object")
        _unknown_fields(job, _JOB_FIELDS, where)
        key = job.get("key")
        if not isinstance(key, str) or not _KEY_RE.match(key):
            _fail(f"{where}: 'key' must be lowercase/dashes, e.g. "
                  f"'snapshot', got {key!r}")
        where = f"plan job {key!r}"
        if key in seen_keys:
            _fail(f"{where}: duplicate job key")
        seen_keys.add(key)
        title = _require_str(job, "title", where)
        if "\n" in title.strip():
            _fail(f"{where}: 'title' must be a single line")
        spec = _require_str(job, "spec", where)
        files = job.get("files")
        if not isinstance(files, list) or not files:
            _fail(f"{where}: 'files' must be a non-empty list")
        for path in files:
            if not isinstance(path, str) or not path.strip():
                _fail(f"{where}: 'files' entries must be non-empty "
                      f"strings, got {path!r}")
        deps = job.get("deps", [])
        if not isinstance(deps, list):
            _fail(f"{where}: 'deps' must be a list of job keys")
        for dep in deps:
            if not isinstance(dep, str) or not dep.strip():
                _fail(f"{where}: 'deps' entries must be non-empty "
                      f"strings, got {dep!r}")
        max_attempts = job.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
            _fail(f"{where}: 'max_attempts' must be an integer, "
                  f"got {max_attempts!r}")
        accept = job.get("accept")
        if not isinstance(accept, list) or not accept:
            _fail(f"{where}: 'accept' must be a non-empty list of "
                  f"accept lines")
        for line in accept:
            if not isinstance(line, str) or not line.strip():
                _fail(f"{where}: 'accept' entries must be non-empty "
                      f"strings, got {line!r}")
        try:
            checks = acceptance.parse_accept("\n".join(accept))
        except ValueError as exc:
            _fail(f"{where}: unparseable accept line: {exc}")
        if not checks:
            _fail(f"{where}: 'accept' has no parseable checks")
        req = job.get("req", [])
        if not isinstance(req, list):
            _fail(f"{where}: 'req' must be a list of capability "
                  f"names")
        for entry in req:
            if not isinstance(entry, str) or not entry.strip():
                _fail(f"{where}: 'req' entries must be non-empty "
                      f"strings, got {entry!r}")
        req = list(dict.fromkeys(e.strip().lower() for e in req))
        out_jobs.append({
            "key": key,
            "title": title,
            "spec": spec,
            "files": list(files),
            "deps": list(deps),
            "max_attempts": max_attempts,
            "accept": list(accept),
            "req": req,
        })
    return {"summary": summary, "jobs": out_jobs}


def check_file_overlap(plan):
    """Guard a parsed plan against two jobs owning the same path.

    Takes a parse_plan output dict and returns it unchanged when no
    job pair owns a shared path outside the shared-sequential rule.
    Raises PlanError naming the path and both job keys otherwise.

    Shared-sequential rule, per owner pair in plan order: the later
    job must list the earlier job in deps, and the later job's spec
    must contain both the token "shared-sequential" and the shared
    path (case-insensitive). Either condition missing is a hard
    error, and the message says which one is missing, so a plan
    author can fix exactly that fault. Duplicate paths inside one
    job's own files list are not an overlap: one job owning a path
    twice is still one owner.
    """
    jobs = plan.get("jobs", []) if isinstance(plan, dict) else []
    owners = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        key = job.get("key")
        if not isinstance(key, str):
            continue
        for path in dict.fromkeys(job.get("files", [])):
            owners.setdefault(path, []).append(job)
    for path, owners_of_path in owners.items():
        for earlier, later in zip(owners_of_path, owners_of_path[1:]):
            earlier_key = earlier.get("key")
            later_key = later.get("key")
            where = (f"plan job {later_key!r} overlaps "
                     f"plan job {earlier_key!r} on {path!r}")
            if earlier_key not in later.get("deps", []):
                _fail(f"{where}: later job must list the earlier "
                      f"job in 'deps' for a shared-sequential path")
            spec = later.get("spec", "")
            spec_lower = spec.lower() if isinstance(spec, str) else ""
            if ("shared-sequential" not in spec_lower
                    or path.lower() not in spec_lower):
                _fail(f"{where}: later job spec must mark the path "
                      f"shared-sequential, e.g. "
                      f"'shared-sequential: {path}'")
    return plan


def check_dep_graph(plan):
    """Validate a parsed plan's dependency graph; return posting order.

    Takes a parse_plan output dict and returns a list of job keys
    in posting order: every job appears after all of its deps, so a
    poster walking the order can map each dep key to the real job id
    already posted. Traversal is depth-first in plan order with
    deps visited in listed order, so the order is deterministic and
    independent jobs keep their plan order.

    Raises PlanError naming the fault: a dep key that is not a job
    in this plan, or a dependency cycle (message names the full
    cycle, e.g. "dependency cycle: a -> b -> a"). Duplicate dep
    entries on one job are harmless and visited once. The plan is
    not mutated; the returned list is new.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    jobs = plan["jobs"]
    keys = set()
    deps_of = {}
    for job in jobs:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        keys.add(job["key"])
        deps_of[job["key"]] = list(dict.fromkeys(job.get("deps", [])))
    for job in jobs:
        for dep in deps_of[job["key"]]:
            if dep not in keys:
                _fail(f"plan job {job['key']!r}: dep {dep!r} is not "
                      f"a job key in this plan")
    # Depth-first post-order; WHITE unvisited, GRAY on the stack,
    # BLACK done. Hitting a GRAY node closes a cycle: the stack
    # slice from that node, plus the node again, names the cycle.
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {key: WHITE for key in keys}
    order = []
    stack = []

    def visit(key):
        color[key] = GRAY
        stack.append(key)
        for dep in deps_of[key]:
            if color[dep] == GRAY:
                cycle = stack[stack.index(dep):] + [dep]
                _fail("dependency cycle: "
                      + " -> ".join(cycle))
            if color[dep] == WHITE:
                visit(dep)
        stack.pop()
        color[key] = BLACK
        order.append(key)

    for job in jobs:
        if color[job["key"]] == WHITE:
            visit(job["key"])
    return order


def clamp_attempt_budgets(plan):
    """Clamp every job's attempt budget into 1..5; report the clamps.

    Takes a parse_plan output dict and returns a (new_plan, clamps)
    pair. new_plan is a copy of the plan with each job's
    max_attempts clamped to MIN_MAX_ATTEMPTS..MAX_MAX_ATTEMPTS;
    values already in range, including the default
    DEFAULT_MAX_ATTEMPTS, pass through unchanged. clamps is a list
    of {key, requested, clamped} dicts, one per job whose value
    actually changed, in plan order; empty when nothing clamped.
    The input plan is not mutated, so a caller can diff before and
    after. Raises PlanError on a malformed plan shape. The
    function never posts, never claims, and never touches the bus.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    new_jobs = []
    clamps = []
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        requested = job.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
        if (isinstance(requested, bool)
                or not isinstance(requested, int)):
            _fail(f"plan job {job['key']!r}: 'max_attempts' must be "
                  f"an integer, got {requested!r}")
        clamped = min(MAX_MAX_ATTEMPTS,
                      max(MIN_MAX_ATTEMPTS, requested))
        new_job = dict(job)
        new_job["max_attempts"] = clamped
        new_jobs.append(new_job)
        if clamped != requested:
            clamps.append({"key": job["key"], "requested": requested,
                           "clamped": clamped})
    new_plan = dict(plan)
    new_plan["jobs"] = new_jobs
    return new_plan, clamps


# DSP-028: credential shapes, kept in step with the BRF-014
# redaction list in intel/brief.py. Deliberately NOT included:
# plain hex strings, so commit hashes quoted in specs pass.
# Each entry is (label, pattern); the label is what the error
# names, so a refusal never quotes the credential itself.
_SECRET_PATTERNS = [
    ("GitHub token",
     r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}"),
    ("GitHub fine-grained token",
     r"github_pat_[A-Za-z0-9_]{20,}"),
    ("API key",
     r"sk-[A-Za-z0-9]{20,}"),
    ("AWS access key id",
     r"AKIA[0-9A-Z]{16}"),
    ("Bearer token",
     r"Bearer\s+[A-Za-z0-9._\-]{10,}"),
    ("named credential assignment",
     r"(?i)(?:api[_-]?key|access[_-]?token|secret|password)"
     r"\s*[:=]\s*[\"']?[^\s\"',;}]+"),
]


def check_no_secrets(text):
    """Guard a goal text or plan JSON text against secrets.

    Takes a string and returns it unchanged when no
    credential-shaped string is found. Raises PlanError with a
    "secret warning" naming the shape found (never the value)
    otherwise, so the caller refuses the goal or plan before
    anything is sent, posted, or claimed. Call it on the goal
    text before the Spark call and on the plan text at parse
    time, e.g. check_no_secrets(text); plan = parse_plan(text).
    It touches no state: refusing here posts nothing.
    """
    if not isinstance(text, str):
        _fail("secret check: expected text, "
              f"got {type(text).__name__}")
    for label, pattern in _SECRET_PATTERNS:
        if re.search(pattern, text):
            _fail(f"secret warning: plan refused — {label} found "
                  f"in text; remove the credential-shaped string "
                  f"and resubmit. The value itself is never "
                  f"quoted in this message.")
    return text


# DSP-023: file-level create-vs-delete contradiction. A plan that
# creates a file in one job and deletes the same file in another
# (or both in one job) nets to destroying the first job's work,
# even when the overlap guard allows it via shared-sequential
# (create-then-delete is sequential, but still nonsense).
# Narrow by design: only the literal phrases "create file <path>"
# vs "delete file <path>" / "remove file <path>" count, and only
# when <path> is a file the job itself owns. Content edits
# ("add a line to <path>", "remove the old helper from <path>")
# are normal work, not a contradiction, and are not flagged.
# Semantic contradictions with no file-level wording still need
# the human approval gate (DSP-007); this guard never claims
# to catch those.
_CREATE_FILE_RE = re.compile(r"\bcreate\s+(?:the\s+)?(?:new\s+)?"
                             r"file\s+(\S+)")
_DELETE_FILE_RE = re.compile(r"\b(?:delete|remove)\s+(?:the\s+)?"
                             r"file\s+(\S+)")


def _file_op_paths(spec, pattern):
    paths = set()
    if not isinstance(spec, str):
        return paths
    for match in pattern.finditer(spec.lower()):
        paths.add(match.group(1).rstrip(".,;:!?\"'"))
    return paths


def check_no_contradiction(plan):
    """Guard a parsed plan against file-level create-vs-delete.

    Takes a parse_plan output dict and returns it unchanged when
    no file is both created and deleted in the plan. Raises
    PlanError naming the path and both job keys when one job
    creates a file another job deletes (or one job does both),
    so a contradictory plan never reaches approval. The parser
    itself stays shape-only: a contradictory plan still parses,
    and only this guard rejects it. Posts nothing; pure check
    on the parsed plan.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    ops = {}
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        key = job["key"]
        owned = {}
        for path in dict.fromkeys(job.get("files", [])):
            if isinstance(path, str):
                owned[path.lower()] = path
        created = _file_op_paths(job.get("spec", ""), _CREATE_FILE_RE)
        deleted = _file_op_paths(job.get("spec", ""), _DELETE_FILE_RE)
        for path in sorted(created & set(owned)):
            ops.setdefault(owned[path], {})["create"] = key
        for path in sorted(deleted & set(owned)):
            ops.setdefault(owned[path], {})["delete"] = key
    for path, holders in ops.items():
        if "create" in holders and "delete" in holders:
            creator, deleter = holders["create"], holders["delete"]
            if creator == deleter:
                _fail(f"plan job {creator!r} contradicts itself on "
                      f"{path!r}: it both creates and deletes the "
                      f"file; drop one of the two operations")
            _fail(f"plan job {deleter!r} contradicts plan job "
                  f"{creator!r} on {path!r}: one deletes the file "
                  f"the other creates; drop one of the two jobs")
    return plan


# DSP-026 spec-writing standard: every job spec carries these five
# parts, in this order, each with real content (not just the label).
SPEC_PART_LABELS = ("goal", "context", "files", "steps",
                    "out of scope")
_SPEC_PART_RES = [
    re.compile(r"\bgoal\b", re.I),
    re.compile(r"\bcontext\b", re.I),
    re.compile(r"\bfiles\b", re.I),
    re.compile(r"\bsteps\b", re.I),
    re.compile(r"out[ -]of[ -]scope\b", re.I),
]


def score_spec_parts(spec, files=()):
    """Score one job spec against the DSP-026 standard.

    Returns a dict: missing (labels not found, in standard order),
    empty (labels found but with no content before the next label),
    files_part_names_owned (True when the Files part names at least
    one of the job's owned files, False when it names none, None
    when no owned files were given), and passes (True only when
    nothing is missing or empty and the Files part, when owned
    files were given, names one). Labels are matched in order, so
    a spec with the parts shuffled reports the out-of-order part
    as missing from its expected position. Never raises on a
    malformed spec: a non-string spec scores every part missing.
    Pure scoring; posts nothing and never refuses a plan — the
    parser gate stays shape-only by design (see module docstring).
    """
    result = {"missing": [], "empty": [],
              "files_part_names_owned": None, "passes": False}
    if not isinstance(spec, str):
        result["missing"] = list(SPEC_PART_LABELS)
        return result
    lowered = spec.lower()
    positions = []
    cursor = 0
    for label, pattern in zip(SPEC_PART_LABELS, _SPEC_PART_RES):
        match = pattern.search(lowered, cursor)
        if match is None:
            result["missing"].append(label)
            positions.append(None)
        else:
            positions.append(match)
            cursor = match.end()
    found = [p for p in positions if p is not None]
    for index, match in enumerate(positions):
        if match is None:
            continue
        if index + 1 < len(positions):
            later = [p for p in positions[index + 1:] if p is not None]
            end = later[0].start() if later else len(spec)
        else:
            end = len(spec)
        content = spec[match.end():end].strip(" \t\n:;,.—-")
        if not content.strip():
            result["empty"].append(SPEC_PART_LABELS[index])
    files_index = SPEC_PART_LABELS.index("files")
    if positions[files_index] is not None and files:
        later = [p for p in positions[files_index + 1:]
                 if p is not None]
        end = later[0].start() if later else len(spec)
        files_part = spec[positions[files_index].end():end].lower()
        result["files_part_names_owned"] = any(
            str(path).lower() in files_part for path in files)
    result["passes"] = (not result["missing"] and not result["empty"]
                        and result["files_part_names_owned"] is not False)
    return result


def score_plan_specs(plan):
    """Score every job spec in a parsed plan (DSP-026).

    Returns a list of {key, missing, empty, files_part_names_owned,
    passes} in plan order, one entry per job. Raises PlanError on
    a malformed plan, in line with the other plan scorers here.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    scores = []
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        score = score_spec_parts(job.get("spec"),
                                 files=job.get("files", []))
        score["key"] = job["key"]
        scores.append(score)
    return scores


# DSP-027 acceptance-line standard: every job carries at least
# one machine-checkable accept line, in exactly the four
# mos/acceptance.py formats. Which target each kind must name:
# file-exists and contains name a file the job itself owns;
# tests-pass names the test module that checks the job's work
# (a check target, not an owned file, so it need not appear in
# the job's files); command-ok names a command that mentions at
# least one owned file, so the check runs against this job's
# work and not something unrelated. The parser already refuses
# an empty or unparseable accept list; ownership is scorer-only,
# so a plan naming an unowned file still parses and only the
# scorer fails it — the same separate-guard pattern as DSP-026.
_ACCEPT_TEST_PREFIXES = ("tests.", "tests/")


def score_accept_lines(accept, files=()):
    """Score one job's accept lines against the DSP-027 standard.

    Returns a dict: checks (parseable checks found), parseable
    (same count, kept for symmetry with the spec scorer's shape),
    unowned (file paths, or command texts, that name nothing the
    job owns), bad_lines (lines that do not parse, name no test
    module, or are not strings), and passes (True only when at
    least one check parses and nothing is bad or unowned).
    Ownership is checked only when files were given; with no
    files list every parseable line passes on parse alone.
    Never raises on malformed input: a non-list accept list
    scores zero checks and fails. Pure scoring; posts nothing
    and never refuses a plan.
    """
    result = {"checks": 0, "parseable": 0, "unowned": [],
              "bad_lines": [], "passes": False}
    if not isinstance(accept, list):
        return result
    owned = {str(path) for path in files} if files else set()
    for line in accept:
        if not isinstance(line, str) or not line.strip():
            result["bad_lines"].append(line)
            continue
        try:
            checks = acceptance.parse_accept(line)
        except ValueError:
            result["bad_lines"].append(line)
            continue
        if not checks:
            result["bad_lines"].append(line)
            continue
        for kind, arg in checks:
            result["checks"] += 1
            result["parseable"] += 1
            if kind == "file-exists":
                if owned and arg not in owned:
                    result["unowned"].append(arg)
            elif kind == "contains":
                path = arg.partition("::")[0].strip()
                if owned and path not in owned:
                    result["unowned"].append(path)
            elif kind == "tests-pass":
                target = arg.strip()
                if not target.startswith(_ACCEPT_TEST_PREFIXES):
                    result["bad_lines"].append(line)
            elif kind == "command-ok":
                if owned and not any(path in arg for path in owned):
                    result["unowned"].append(arg)
    result["passes"] = (result["checks"] >= 1
                        and not result["bad_lines"]
                        and not result["unowned"])
    return result


def score_plan_accepts(plan):
    """Score every job's accept lines in a parsed plan (DSP-027).

    Returns a list of {key, checks, parseable, unowned,
    bad_lines, passes} in plan order, one entry per job. Raises
    PlanError on a malformed plan, in line with the other plan
    scorers here.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    scores = []
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        score = score_accept_lines(job.get("accept"),
                                   files=job.get("files", []))
        score["key"] = job["key"]
        scores.append(score)
    return scores


def plan_summary(plan, clamps=()):
    """Render a parsed plan as a human-readable summary string.

    First line is the plan's summary, then one line per job in
    plan order ("- key: title (attempts N)"), then one line per
    clamp ("clamped: job 'key': max_attempts 99 -> 5"). With no
    clamps there is no clamp section at all, so a reader can tell
    at a glance whether any budget was adjusted. Used by the
    DSP-006 dry-run; it posts nothing and touches no state.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    lines = [plan.get("summary", "")]
    for job in plan["jobs"]:
        if not isinstance(job, dict):
            _fail("plan: each job must be a parsed job dict")
        lines.append(f"- {job.get('key')}: {job.get('title')} "
                     f"(attempts {job.get('max_attempts')})")
    for clamp in clamps or ():
        lines.append(f"clamped: job {clamp['key']!r}: max_attempts "
                     f"{clamp['requested']} -> {clamp['clamped']}")
    return "\n".join(lines)


def plan_paragraph(plan, order=None):
    """Render a parsed plan as one plain-English paragraph (DSP-025).

    The paragraph is the dashboard form of a plan: the plan's
    summary sentence first, then every job named once, in posting
    order, each with the files it owns in parentheses — "First, ...,
    then ..., and finally ...". A one-job plan reads "It does ...".
    Unlike plan_summary and render_plan_detail this is a single
    paragraph with no newlines, so the dashboard panel can show
    the whole plan without a multi-line block.

    The paragraph never names a likely claimant: a parsed plan
    carries no claimant field, and inventing one would break the
    brief lane's ground rule that a brief never invents a fact.
    The Spark-authored `summary` field is where a likely claimant
    belongs when the goal text names one. Raises PlanError on a
    malformed plan, or when an explicit order does not cover
    exactly the plan's jobs, so a paragraph can never silently
    drop a job. Pure string building; posts nothing.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    by_key = {}
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        by_key[job["key"]] = job
    if order is None:
        order = [job["key"] for job in plan["jobs"]]
    if not isinstance(order, (list, tuple)) or sorted(order) != \
            sorted(by_key):
        _fail("plan: posting order must cover exactly the plan's "
              "jobs")
    summary = str(plan.get("summary", "")).strip()
    if summary and not summary.endswith("."):
        summary += "."
    clauses = []
    for key in order:
        job = by_key[key]
        title = job.get("title", "")
        files = job.get("files", []) or []
        if files:
            clauses.append(f"{title} (in {', '.join(files)})")
        else:
            clauses.append(f"{title}")
    if not clauses:
        return summary
    if len(clauses) == 1:
        body = f"It does {clauses[0]}."
    elif len(clauses) == 2:
        body = f"First, {clauses[0]}, then {clauses[1]}."
    else:
        body = ("First, " + clauses[0] + ", then " +
                ", then ".join(clauses[1:-1]) +
                f", and finally {clauses[-1]}.")
    return f"{summary} {body}" if summary else body


def render_plan_detail(plan, order, clamps=(), warnings=()):
    """Render a parsed plan in full for the DSP-006 dry-run.

    First line is the plan's summary, second line is the posting
    order ("jobs in posting order: base -> api -> panel -> docs"),
    then one block per job in posting order: title and attempt
    budget on the header line, then files, deps ("none" when
    empty), req ("none" when the job names no capability), and
    accept lines, each comma/semicolon joined on its own line. Clamp lines (same shape as plan_summary) close the
    output, so an adjusted budget is visible in the dry-run too.
    Warning lines (DSP-013 plan_size_warnings output, empty by
    default) close the output after the clamp lines, so a large
    plan's guard message is visible in the dry-run too.
    Raises PlanError when the order does not cover exactly the
    plan's jobs, so a dry-run can never render a partial plan.
    Posts nothing; pure string building.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    by_key = {}
    for job in plan["jobs"]:
        if not isinstance(job, dict) or not isinstance(job.get("key"),
                                                       str):
            _fail("plan: each job must be a parsed job dict with a "
                  "'key'")
        by_key[job["key"]] = job
    if not isinstance(order, (list, tuple)) or sorted(order) != \
            sorted(by_key):
        _fail("plan: posting order must cover exactly the plan's "
              "jobs")
    lines = [plan.get("summary", ""),
             "jobs in posting order: " + " -> ".join(order)]
    for key in order:
        job = by_key[key]
        lines.append(f"- {key}: {job.get('title')} "
                     f"(attempts {job.get('max_attempts')})")
        lines.append("  files: " + ", ".join(job.get("files", [])))
        deps = job.get("deps", [])
        lines.append("  deps: " + (", ".join(deps) if deps else "none"))
        req = job.get("req", [])
        lines.append("  req: " + (", ".join(req) if req else "none"))
        lines.append("  accept: " + "; ".join(job.get("accept", [])))
    for clamp in clamps or ():
        lines.append(f"clamped: job {clamp['key']!r}: max_attempts "
                     f"{clamp['requested']} -> {clamp['clamped']}")
    for warning in warnings or ():
        lines.append(warning)
    return "\n".join(lines)


def plan_size_warnings(plan):
    """Return the DSP-013 size warnings for a parsed plan.

    Pure function on the plan dict: no posting, no claiming,
    no bus, no state. Returns a list of warning strings, one
    per breached limit, or an empty list when the plan is
    inside both limits. The limits are MAX_PLAN_JOBS jobs and
    MAX_PLAN_FILES distinct files across the plan's jobs
    (counted by distinct path, so one path owned twice still
    counts once; non-string file entries are ignored, since a
    validated plan carries strings only). Each warning names
    the count and the limit, states that the plan needs a
    second confirmation before posting, and carries the split
    suggestion: break the plan into smaller plans inside the
    limits, posted in dependency order, each approved
    separately. A plan at exactly a limit triggers nothing:
    the guard fires only over the limit. Raises PlanError on
    a malformed plan shape, like the other guards.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    warnings = []
    jobs = plan["jobs"]
    if len(jobs) > MAX_PLAN_JOBS:
        warnings.append(
            f"plan size guardrail: {len(jobs)} jobs exceeds the "
            f"{MAX_PLAN_JOBS}-job limit; this plan needs a second "
            f"confirmation before posting. Split suggestion: break "
            f"it into smaller plans of at most {MAX_PLAN_JOBS} "
            f"jobs each (for example one plan per dependency "
            f"chain), posted in dependency order, and approve "
            f"each part separately")
    files = set()
    for job in jobs:
        if not isinstance(job, dict):
            continue
        for path in job.get("files", []) or []:
            if isinstance(path, str):
                files.add(path)
    if len(files) > MAX_PLAN_FILES:
        warnings.append(
            f"plan size guardrail: {len(files)} files exceeds the "
            f"{MAX_PLAN_FILES}-file limit; this plan needs a "
            f"second confirmation before posting. Split "
            f"suggestion: break it into smaller plans touching "
            f"at most {MAX_PLAN_FILES} files each, posted in "
            f"dependency order, and approve each part separately")
    return warnings


def large_plan_prompt(plan, warnings=None):
    """Build the second-confirmation prompt for a large plan.

    Names the job count and the distinct file count, and says
    plainly that this is a second confirmation, so the human
    answers about this large plan, not in the abstract.
    warnings, when given, is plan_size_warnings output (used
    only to keep the caller from recomputing it; the prompt
    itself is built from the counts). Raises PlanError on a
    malformed plan shape, like the other guards. Pure string
    building; posts nothing.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    files = set()
    for job in plan["jobs"]:
        if isinstance(job, dict):
            for path in job.get("files", []) or []:
                if isinstance(path, str):
                    files.add(path)
    return (f"This plan is large ({len(plan['jobs'])} jobs, "
            f"{len(files)} files) and needs a second "
            f"confirmation. Post it anyway? [y/N] ")


def validated_plan(text):
    """Run the full read-only validation pipeline on a plan JSON.

    parse_plan, check_file_overlap, check_no_contradiction,
    check_dep_graph, then clamp_attempt_budgets, in order.
    Returns a (plan, order, clamps) triple: the clamped plan, its
    posting order, and the clamp reports. Raises PlanError from
    the first failing check. Shared by dry_run_plan and by the
    DSP-007 approval path, so the plan a human approves is
    exactly the plan the gates passed — never a re-parsed
    variant. Posts nothing.
    """
    plan = parse_plan(text)
    check_file_overlap(plan)
    check_no_contradiction(plan)
    order = check_dep_graph(plan)
    plan, clamps = clamp_attempt_budgets(plan)
    return plan, order, clamps


def dry_run_plan(text):
    """Validate a Spark plan JSON and render it for a dry-run.

    Runs validated_plan, then renders the clamped plan with
    render_plan_detail. Returns the detail string. Raises
    PlanError from the first failing check, so a dry-run shows
    either the full valid plan or an error, never a partial plan.
    Posts nothing, claims nothing, writes no record, touches no
    job state: the whole pipeline is pure functions on the text.
    """
    plan, order, clamps = validated_plan(text)
    return render_plan_detail(plan, order, clamps,
                              plan_size_warnings(plan))


FALLBACK_JOB_KEY = "fallback-job"


def fallback_plan(goal):
    """Build the DSP-017 fallback plan for a raw goal.

    Returns a single-job plan dict in parse_plan output shape:
    summary, title, and spec are all marked FALLBACK, and the
    spec carries the raw goal verbatim after the FALLBACK
    marker, so the job is the goal itself, not a paraphrase
    of it. The job carries no files and no accept lines:
    Spark supplied nothing usable to derive them from, and
    this function invents neither — the DSP-007 approval
    gate is where a human decides whether the raw-goal job
    posts as-is. The title is the goal's first non-empty
    line, truncated to 100 characters, so a multi-line goal
    still yields the single-line title the poster needs.
    Raises PlanError on an empty or non-string goal, so a
    fallback is never built for nothing. Posts nothing.
    """
    if not isinstance(goal, str) or not goal.strip():
        _fail("fallback plan: goal must be a non-empty string")
    first_line = ""
    for line in goal.splitlines():
        if line.strip():
            first_line = line.strip()
            break
    if len(first_line) > 100:
        first_line = first_line[:97] + "..."
    return {
        "summary": "FALLBACK plan: Spark returned malformed JSON "
                   "twice, so no structured plan was produced; "
                   "this single job carries the raw goal as its "
                   "spec",
        "jobs": [{
            "key": FALLBACK_JOB_KEY,
            "title": f"FALLBACK: {first_line}",
            "spec": "FALLBACK: Spark returned malformed JSON "
                    "twice, so no structured plan was produced. "
                    "Raw goal, verbatim:\n\n" + goal,
            "files": [],
            "deps": [],
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
            "accept": [],
        }],
    }


def _is_malformed_json(text):
    """True when text is not parseable JSON (DSP-017 classifier).

    Only this failure triggers a retry and, on the second
    consecutive failure, the fallback: a text that parses as
    JSON but fails a plan guard is a structured-plan fault,
    not a malformed answer, and validated_plan reports it.
    A non-string answer counts as malformed — there is no
    JSON text in it to parse.
    """
    if not isinstance(text, str):
        return True
    try:
        json.loads(text)
    except ValueError:
        return True
    return False


def plan_from_spark(goal, complete):
    """Get a plan from Spark, with the DSP-017 fallback.

    complete is a caller-supplied Spark completion callable,
    called as complete(goal) — the caller wraps the DSP-001
    prompt construction around it, so this function stays
    transport-free and testable without a live Spark call.
    First attempt: call complete, and when the answer is
    malformed JSON, call it once more. When the second
    answer is malformed too, return the fallback plan
    instead of raising: {"plan": fallback_plan(goal),
    "order": ["fallback-job"], "clamps": [],
    "fallback": True, "warning": <loud FALLBACK warning>}.
    The warning is also printed to stderr, so an operator
    sees it even without reading the return value. When an
    answer parses as JSON, it goes through validated_plan
    exactly like a dry-run plan: a guard failure there
    raises PlanError on the first attempt, with no retry
    and no fallback. INT-008: a Spark transport error
    raised by complete also returns the fallback plan,
    with a warning that names the endpoint-down failure
    instead of the malformed-JSON failure, because an
    endpoint that answers nothing is not a structured-plan
    fault and the drill requires dispatch to fall back
    when Spark is down. On success
    the result is {"plan", "order", "clamps",
    "fallback": False, "warning": None}. Posts nothing,
    claims nothing, touches no job state: the fallback
    only becomes a job when a caller posts it through
    the DSP-007 gate and the DSP-008 poster.
    """
    if not isinstance(goal, str) or not goal.strip():
        _fail("dispatch from Spark: goal must be a non-empty "
              "string")
    warning = None
    for attempt in (1, 2):
        try:
            text = complete(goal)
        except Exception as exc:
            detail = str(exc)[:200]
            plan = fallback_plan(goal)
            warning = (
                "WARNING: FALLBACK plan — Spark endpoint is down "
                f"({type(exc).__name__}: {detail}), so no "
                "structured plan was produced. This single "
                "FALLBACK job carries the raw goal as its "
                "spec; a human must approve it (DSP-007) "
                "before anything posts, and nothing "
                "malformed was posted.")
            print(warning, file=sys.stderr)
            return {"plan": plan, "order": [FALLBACK_JOB_KEY],
                    "clamps": [], "fallback": True,
                    "warning": warning}
        if _is_malformed_json(text):
            if attempt == 1:
                continue
            plan = fallback_plan(goal)
            warning = (
                "WARNING: FALLBACK plan — Spark returned "
                "malformed JSON twice for this goal, so no "
                "structured plan was produced. This single "
                "FALLBACK job carries the raw goal as its "
                "spec; a human must approve it (DSP-007) "
                "before anything posts, and nothing "
                "malformed was posted.")
            print(warning, file=sys.stderr)
            return {"plan": plan, "order": [FALLBACK_JOB_KEY],
                    "clamps": [], "fallback": True,
                    "warning": warning}
        plan, order, clamps = validated_plan(text)
        return {"plan": plan, "order": order, "clamps": clamps,
                "fallback": False, "warning": None}
    raise AssertionError("plan_from_spark: unreachable")


def approval_prompt(plan):
    """Build the interactive approval prompt for a parsed plan.

    Names the job count ("Post this plan (4 jobs)? [y/N] "),
    so the human answers about this plan, not in the abstract.
    Raises PlanError on a malformed plan shape, like the other
    guards. Pure string building; posts nothing.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    return f"Post this plan ({len(plan['jobs'])} jobs)? [y/N] "


def request_approval(plan, approve=False, confirm=None,
                     confirm_large=False):
    """Decide whether a validated plan may be posted (DSP-007).

    The single gate between a plan and the DSP-008 poster.
    Returns True only when a human has approved, by exactly one
    of two routes:
      - approve=True: the caller already holds a human approval
        (CLI --approve flag, or the dashboard approve action
        after the signed-in human confirms). The gate trusts
        the caller's claim but never manufactures one.
      - confirm is a prompt function (input): it is called once
        with approval_prompt(plan), and only a stripped,
        case-insensitive "y" or "yes" approves. Any other
        answer denies, and an EOFError from the prompt denies
        instead of crashing — a closed stdin is never approval.
    With approve=False and confirm=None there is no human in
    the loop, so the answer is False: non-interactive runs must
    pass --approve explicitly, and a default never approves.
    DSP-013 second confirmation: when plan_size_warnings is
    non-empty, the first approval alone is not enough. The
    plan also needs a second confirmation, by exactly one of
    two routes: confirm_large=True (the caller already holds
    it, CLI --confirm-large flag), or the confirm prompt
    function called a second time with large_plan_prompt(plan),
    answered y/yes. Any other second answer, an EOFError from
    the second prompt, or no second confirmation at all denies
    the large plan, even when the first approval passed.
    Raises PlanError on a malformed plan shape. Never posts,
    never claims, never touches job state, and never mutates
    the plan: approval is a decision, not a side effect.
    """
    if not isinstance(plan, dict) or not isinstance(plan.get("jobs"),
                                                     list):
        _fail("plan: expected a parsed plan dict with a 'jobs' list")
    if approve:
        first = True
    elif confirm is None:
        return False
    else:
        try:
            answer = confirm(approval_prompt(plan))
        except EOFError:
            return False
        first = isinstance(answer, str) and \
            answer.strip().lower() in ("y", "yes")
    if not first:
        return False
    warnings = plan_size_warnings(plan)
    if not warnings:
        return True
    if confirm_large:
        return True
    if confirm is None:
        return False
    try:
        answer = confirm(large_plan_prompt(plan, warnings))
    except EOFError:
        return False
    return isinstance(answer, str) and answer.strip().lower() in (
        "y", "yes")


class PostError(Exception):
    """A plan poster run failed: a job could not be posted."""


def _jobs_main_post(argv):
    """Post one job through jobs.main(); return its real id or None.

    jobs.main prints "JOB <id>" on success and returns 0; any
    other return code, or a success code with no JOB line, is a
    failed post. Only stdout is captured: jobs.py warnings (for
    example the FND-009 nonexistent-dep warning) stay on stderr
    for the operator. The import is lazy so the pure pipeline
    above never imports the queue at module import time.
    """
    import contextlib
    import io

    import jobs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = jobs.main(argv)
    if code != 0:
        return None
    for line in reversed(buf.getvalue().splitlines()):
        if line.startswith("JOB "):
            job_id = line[4:].strip()
            if job_id:
                return job_id
    return None


def format_dispatch_announcement(record):
    """DSP-010: one frozen-format announcement line for a plan.

    Returns "DISPATCH:<id> -> <n> jobs" for a dispatch record
    stored by post_plan, or None when the record cannot carry
    a line. <n> is len(record["jobs"]), the jobs actually
    posted, never the number planned. An id with whitespace
    yields None, because the FND-020 freeze requires ids with
    no spaces, and a record with no jobs list yields None,
    because there is nothing posted to announce. Pure: it
    posts nothing, claims nothing, and writes no record.
    """
    if not isinstance(record, dict):
        return None
    record_id = record.get("id")
    if not isinstance(record_id, str) or not record_id.strip():
        return None
    if any(ch.isspace() for ch in record_id):
        return None
    jobs = record.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        return None
    return f"DISPATCH:{record_id} -> {len(jobs)} jobs"


def post_plan(plan, order=None, room="main", secret_file=None,
              dispatch_id=None, post_one=None, now=None,
              crew_mode=False, confirm_large=False,
              monotonic=None, announce=None):
    """Post a validated plan's jobs in topological order (DSP-008).

    plan is a validated_plan output (already parsed, overlap
    guarded, dep graphed, and budget clamped by the caller; the
    CLI path runs exactly that pipeline before the DSP-007
    gate). Each job's req list (DSP-012, empty when the goal
    names no skill) is passed to jobs.py as --req and stored
    on the posted job, in the form mos/capabilities.find_for
    matches. order is the posting order, defaulting to
    check_dep_graph(plan) when omitted; it must cover exactly
    the plan's jobs, and every dep must already be posted when
    its dependent is reached, or PostError is raised before
    that job is attempted. Each job is posted through
    jobs.main() with its title, spec, accept lines (newline
    joined, the mos/acceptance.py line format), files
    (comma-joined, the jobs.py FND-008 field), attempt budget,
    and deps rewritten from plan keys to the real job ids
    already posted. The "--opt=value" argv form is used so a
    title or spec starting with "-" is a value, not an option.
    post_one, when given, replaces the jobs.main call in tests:
    it takes the argv list and returns a job id string, or a
    falsy value for a failed post. confirm_large, when false
    on a plan that breaches the DSP-013 size guardrail, refuses
    the post outright (PostError before any job is posted, no
    record stored), mirroring the crew-mode refusal: the
    poster never lets a large plan through on a single
    approval. secret_file, when given, is
    passed through to jobs.py for HMAC signing (DSP-009):
    every posted job then verifies OK via jobs.py verify
    against the same keyring, and the record carries
    signed=True. crew_mode, when true, refuses an unsigned
    post outright: with no secret_file it raises PostError
    before any job is posted (zero jobs posted, no record
    stored). Without crew_mode and without a secret_file,
    the plan still posts, but a loud WARNING goes to stderr
    that the jobs post unsigned, and the record carries
    signed=False.

    On full success the dispatch record is stored via
    intel.store.put_dispatch and returned: {id, summary, room,
    created_at, order, signed, latency_ms, jobs: [{key, id,
    title, files, deps (real ids), max_attempts, req}, ...] in
    posting order}. DSP-014: the same run appends one entry
    to the spend ledger (lane_feature "dispatch", the record
    id, jobs_posted, latency_ms, no token counts or cost,
    since posting makes no Spark call); a failed ledger
    write is logged to stderr and never fails the post.
    monotonic, when given, is the clock post_plan reads for
    the latency (default time.monotonic); tests pass a fake
    clock so the latency is exact. The
    record id is dispatch_id when given, else
    "dsp-<created_at>-<first posted job id>", which is unique
    per post even when the clock is frozen. On any failed post
    PostError is raised naming the failed key, the jobs
    already posted (which stay posted — jobs.py has no
    unpost), and the fact that no dispatch record was stored.
    The poster announces nothing itself: the only bus lines
    are the JOB: announcements jobs.py writes per post, and
    the DISPATCH: announcement belongs to DSP-010.
    """
    clock = monotonic or time.monotonic
    started = clock()
    if not isinstance(plan, dict) \
            or not isinstance(plan.get("jobs"), list) \
            or not plan["jobs"]:
        _fail("plan: expected a validated plan dict with a "
              "non-empty 'jobs' list")
    by_key = {}
    for job in plan["jobs"]:
        if not isinstance(job, dict) \
                or not isinstance(job.get("key"), str):
            _fail("plan: each job must be a validated job dict "
                  "with a 'key'")
        by_key[job["key"]] = job
    if order is None:
        order = check_dep_graph(plan)
    if sorted(order) != sorted(by_key):
        _fail("plan: posting order must cover exactly the plan's "
              "jobs")
    size_warnings = plan_size_warnings(plan)
    if size_warnings and not confirm_large:
        raise PostError(
            "dispatch refused: this plan is large and needs a "
            "second confirmation before posting ("
            + "; ".join(size_warnings)
            + "); pass confirm_large=True (CLI "
            "--confirm-large) after the second human "
            "confirmation; nothing posted, no dispatch record "
            "stored")
    if crew_mode and not secret_file:
        raise PostError(
            "dispatch refused: crew mode requires a --secret-file "
            "keyring so every job posts signed; refusing to post "
            "unsigned — nothing posted, no dispatch record stored")
    if not secret_file:
        print("WARNING: dispatch posting unsigned — no "
              "--secret-file given, so these jobs post without "
              "HMAC signatures and a crew verifying signatures "
              "sees them as UNSIGNED; pass --secret-file "
              "<keyring> to sign, or --crew-mode to refuse "
              "unsigned posts outright", file=sys.stderr)
    post = post_one or _jobs_main_post
    key_to_id = {}
    posted = []
    for key in order:
        job = by_key[key]
        missing = [dep for dep in job.get("deps", [])
                   if dep not in key_to_id]
        if missing:
            raise PostError(
                f"dispatch posting failed at plan job {key!r}: "
                f"dep {missing[0]!r} is not posted yet — the "
                f"posting order must place every dep before its "
                f"dependent; jobs already posted stay posted: "
                + (", ".join(f"{k} -> {i}" for k, i in posted)
                   or "none")
                + "; no dispatch record stored")
        argv = ["post",
                f"--title={job['title']}",
                f"--spec={job['spec']}",
                "--accept=" + "\n".join(job.get("accept", [])),
                "--files=" + ",".join(job.get("files", [])),
                "--req=" + ",".join(job.get("req", [])),
                "--max-attempts=" + str(job.get(
                    "max_attempts", DEFAULT_MAX_ATTEMPTS)),
                f"--room={room}"]
        real_deps = [key_to_id[dep] for dep in job.get("deps", [])]
        if real_deps:
            argv.append("--deps=" + ",".join(real_deps))
        if secret_file:
            argv.append(f"--secret-file={secret_file}")
        try:
            job_id = post(argv)
        except Exception as exc:  # noqa: BLE001 - a post that
            # raises is a failed post, reported, not traced
            job_id = None
            reason = f" ({type(exc).__name__}: {exc})"
        else:
            reason = ""
        if not job_id:
            raise PostError(
                f"dispatch posting failed at plan job {key!r}: "
                f"jobs.py post returned no job id{reason}; "
                f"jobs already posted stay posted: "
                + (", ".join(f"{k} -> {i}" for k, i in posted)
                   or "none")
                + "; no dispatch record stored")
        key_to_id[key] = job_id
        posted.append((key, job_id))
    created_at = int(now if now is not None else time.time())
    record_id = dispatch_id or \
        f"dsp-{created_at}-{posted[0][1]}"
    latency_ms = int(round((clock() - started) * 1000))
    record = {
        "id": record_id,
        "summary": plan.get("summary", ""),
        "room": room,
        "created_at": created_at,
        "order": list(order),
        "signed": bool(secret_file),
        "latency_ms": latency_ms,
        "jobs": [{
            "key": key,
            "id": key_to_id[key],
            "title": by_key[key]["title"],
            "files": list(by_key[key].get("files", [])),
            "deps": [key_to_id[dep]
                     for dep in by_key[key].get("deps", [])],
            "max_attempts": by_key[key].get(
                "max_attempts", DEFAULT_MAX_ATTEMPTS),
            "req": list(by_key[key].get("req", [])),
        } for key in order],
    }
    from intel import store as _store  # noqa: E402 - lazy, see
    # module docstring: the pure pipeline never imports the store
    _store.put_dispatch(record_id, record)
    try:
        _store.record_spend({
            "ts": created_at,
            "lane_feature": "dispatch",
            "dispatch_id": record_id,
            "jobs_posted": len(posted),
            "latency_ms": latency_ms,
            "tokens_in": None,
            "tokens_out": None,
            "est_cost": None,
        })
    except Exception as exc:  # ledger is observability; the post
        # already happened, so a failed write is logged, not fatal
        print(f"spend ledger write failed: {exc}", file=sys.stderr)
    if announce is not None:
        line = format_dispatch_announcement(record)
        if line is not None:
            try:
                announce(line)
            except Exception as exc:  # noqa: BLE001 - a
                # failing announcement must not fail the post
                print(f"WARNING: dispatch announcement failed "
                      f"({exc})", file=sys.stderr)
    return record


class UndoError(Exception):
    """A dispatch undo run failed before any job was touched."""


def _jobs_main_cancel(argv):
    """Cancel one job through jobs.main(); return its exit code.

    Stdout is captured so the CANCELLED line does not leak into
    the caller's report; the exit code is the verdict. The
    import is lazy for the same reason as _jobs_main_post.
    """
    import contextlib
    import io

    import jobs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return jobs.main(argv)


def undo_dispatch(dispatch_id, cancel_one=None, now=None):
    """Undo a posted plan: cancel its unclaimed jobs (DSP-011).

    dispatch_id names a dispatch record stored by post_plan.
    Every job in the record is read fresh from the queue, so
    the undo acts on the job's current state, not the state
    at posting time. An open job is cancelled through
    jobs.py cancel (status "cancelled", never claimable
    again); a claimed job is work in progress and is left
    untouched; a done, blocked, failed-final, or already
    cancelled job is history and is left untouched; a job
    id that no longer exists in the queue is reported as
    missing. Nothing else in the queue is touched, and a
    second undo of the same dispatch cancels nothing new:
    the first run's cancelled jobs come back as untouched
    with status cancelled.

    cancel_one, when given, replaces the jobs.main cancel
    call in tests: it takes the argv list and returns an
    exit code (0 cancels). A nonzero code re-reads the
    job and classifies it instead of failing the run, so a
    cancel refused at the queue (a claim landing between
    the read and the cancel) is reported honestly rather
    than aborting the remaining jobs.

    The report is returned and also stored on the dispatch
    record under "undo" with "undone_at": {id, cancelled,
    untouched_claimed, untouched_other, missing}, each entry
    {key, id, title} plus the claim nick for claimed jobs
    and the status for untouched non-claimed jobs. The undo
    announces nothing: the cancelled jobs carry their own
    note, and this report is the record the operator sees.
    A dispatch id with no record raises UndoError before
    any job is touched.
    """
    import jobs as _jobs  # noqa: E402 - lazy, see module docstring
    from intel import store as _store  # noqa: E402 - lazy

    record = _store.get_dispatch(dispatch_id)
    if record is None:
        raise UndoError(
            f"dispatch undo failed: no dispatch record {dispatch_id!r} "
            f"(nothing touched)")
    cancel = cancel_one or _jobs_main_cancel
    reason = f"dispatch undo {dispatch_id}"
    report = {"id": dispatch_id, "cancelled": [],
              "untouched_claimed": [], "untouched_other": [],
              "missing": []}
    for entry in record.get("jobs", []):
        key = entry.get("key", "?")
        job_id = entry.get("id", "?")
        title = entry.get("title", "")

        def _classify(fields):
            if fields is None:
                report["missing"].append(
                    {"key": key, "id": job_id, "title": title})
            elif fields.get("status") == "claimed":
                report["untouched_claimed"].append(
                    {"key": key, "id": job_id, "title": title,
                     "claim": fields.get("claim", "")})
            else:
                report["untouched_other"].append(
                    {"key": key, "id": job_id, "title": title,
                     "status": fields.get("status", "?")})

        fields, _spec = _jobs.job_get(job_id)
        if fields is None:
            _classify(None)
        elif fields.get("status") == "open":
            code = cancel(["cancel", job_id,
                           f"--reason={reason}"])
            if code == 0:
                report["cancelled"].append(
                    {"key": key, "id": job_id, "title": title})
            else:
                # The cancel was refused at the queue; re-read
                # and report the job's actual state instead of
                # guessing (a claim may have landed in between).
                fields, _spec = _jobs.job_get(job_id)
                _classify(fields)
        else:
            _classify(fields)
    undone_at = int(now if now is not None else time.time())
    record["undo"] = report
    record["undone_at"] = undone_at
    _store.put_dispatch(dispatch_id, record)
    return report


class ShowError(Exception):
    """A dispatch show run failed before any job was read."""


def show_dispatch(dispatch_id):
    """Show a posted plan as posted vs current job states (DSP-016).

    dispatch_id names a dispatch record stored by post_plan.
    Every job in the record is read fresh from the queue, so
    the report shows the job's current state, not the state
    at posting time: open, claimed, done, blocked, cancelled,
    failed-final, or missing when the job id is no longer in
    the queue. A claimed job carries its claim nick; every
    other state carries an empty claim.

    The report is returned and nothing is stored: showing is
    read-only, so it never posts, claims, cancels, or writes
    the dispatch record, and showing twice reports the same
    plan with only the job states able to move between shows.
    The report is {id, summary, room, created_at, latency_ms,
    order, jobs, counts}: each job entry is {key, id, title,
    files, deps, max_attempts, req, status, claim}, where deps
    are the posted dep job ids exactly as the record stores
    them, and counts maps each status seen to how many of
    the plan's jobs are in it. A dispatch id with no record
    raises ShowError before any job is read.
    """
    import jobs as _jobs  # noqa: E402 - lazy, see module docstring
    from intel import store as _store  # noqa: E402 - lazy

    record = _store.get_dispatch(dispatch_id)
    if record is None:
        raise ShowError(
            f"dispatch show failed: no dispatch record {dispatch_id!r} "
            f"(nothing touched)")
    jobs_out = []
    counts = {}
    for entry in record.get("jobs", []):
        key = entry.get("key", "?")
        job_id = entry.get("id", "?")
        title = entry.get("title", "")
        fields, _spec = _jobs.job_get(job_id)
        if fields is None:
            status, claim = "missing", ""
        else:
            status = fields.get("status", "?")
            claim = fields.get("claim", "") \
                if status == "claimed" else ""
        counts[status] = counts.get(status, 0) + 1
        jobs_out.append({
            "key": key,
            "id": job_id,
            "title": title,
            "files": list(entry.get("files", [])),
            "deps": list(entry.get("deps", [])),
            "max_attempts": entry.get("max_attempts",
                                      DEFAULT_MAX_ATTEMPTS),
            "req": list(entry.get("req", [])),
            "status": status,
            "claim": claim,
        })
    return {
        "id": dispatch_id,
        "summary": record.get("summary", ""),
        "room": record.get("room", ""),
        "created_at": record.get("created_at"),
        "latency_ms": record.get("latency_ms"),
        "order": list(record.get("order", [j["key"] for j in jobs_out])),
        "jobs": jobs_out,
        "counts": counts,
    }


_SHOW_STATUS_ORDER = ("open", "claimed", "done", "blocked",
                      "cancelled", "failed-final", "missing")


def render_dispatch_show(report):
    """Render a show_dispatch report as plain lines (DSP-016).

    First line names the dispatch id; the summary line follows
    when the record carries one. Then one line per job in
    posting order: key -> job id, title, the files and deps
    as posted, and the job's current state. Plan-local dep
    ids are translated back to plan keys so the deps read
    like the plan, not like queue ids; a dep id outside the
    plan is printed as-is. Claimed jobs name their claim
    nick; a missing job says so in its state word. The last
    line counts jobs per status in a fixed order (open,
    claimed, done, blocked, cancelled, failed-final, missing,
    then any other status alphabetically), so the shape of a
    half-finished plan is visible at a glance. Pure string
    building; it reads no queue and writes nothing.
    """
    lines = [f"dispatch {report['id']}:"]
    if report.get("summary"):
        lines.append(f"  summary: {report['summary']}")
    id_to_key = {job["id"]: job["key"] for job in report["jobs"]}
    for job in report["jobs"]:
        files = ", ".join(job["files"]) if job["files"] else "none"
        deps = ", ".join(id_to_key.get(dep, dep)
                          for dep in job["deps"]) \
            if job["deps"] else "none"
        state = job["status"]
        if state == "claimed" and job["claim"]:
            state = f"claimed by {job['claim']}"
        lines.append(f"  {job['key']} -> {job['id']}: {job['title']} "
                     f"(files: {files}; deps: {deps}) "
                     f"now: {state}")
    counts = report.get("counts", {})
    ordered = [s for s in _SHOW_STATUS_ORDER if s in counts]
    ordered += sorted(s for s in counts if s not in _SHOW_STATUS_ORDER)
    lines.append("  counts: " + (", ".join(
        f"{counts[s]} {s}" for s in ordered) if ordered
        else "0 jobs"))
    return "\n".join(lines)
