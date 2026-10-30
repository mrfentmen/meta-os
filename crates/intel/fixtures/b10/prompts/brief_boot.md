# Boot brief spec - v1 (OS-048)

The boot brief is the first brief after a boot. It is NOT a new
format. It is the morning brief format (BRF-001): the window line
first, then the same five sections in the same order - Decisions,
In flight, Owners, Blocked and why, Watch items - under the same
rules: a brief never invents a fact, blocked reasons are quoted
verbatim, job names and nicks come from the snapshot only, prose
is plain English, and the morning word budget is 220 words
(FND-034). If the carried-over lines below push a boot brief over
budget, cut words the morning way (BRF-001 rule 5): drop the least
important watch item first, never a blocked job or a decision.

What makes a brief a boot brief is its carried-over state, not a
new section. The snapshot for a boot brief covers the window from
the previous shutdown to this boot, and the three carried-over
inputs land in the morning sections they already belong to:

- Overnight decisions go in Decisions. A decision recorded between
  the previous shutdown and this boot is a decision in the window,
  listed like any other decision: what was decided, as recorded
  in the snapshot (DECISION:/DONE:/BLOCKED: markers, BRF-004).
- Jobs in flight at shutdown go in In flight. A job that was open
  or claimed at shutdown and is still open or claimed at boot is
  listed with its title and its status at boot. A job that
  finished since shutdown is not in flight: it appears as a DONE
  decision, not as in-flight work.
- What the watchdog saw during boot goes in Watch items. An alert
  fired during the boot window is listed by alert id with its
  one-line summary, by reference only (BRF-022). The boot brief
  does not re-explain the alert; it names it so the reader can
  look it up.

The other two sections do not change: Owners lists who holds the
in-flight work (BRF-006, claimed jobs only), and Blocked and why
lists every blocked job with its reason verbatim (BRF-005).

Sources are the same five brief sources in
`intel/notes/hana-source-map.md` (FND-033): the digest, the store
JSONL, the jobs list, presence, and capabilities. The shutdown
time, the boot time, and the alert ids all come from those
sources. If the snapshot does not hold a shutdown state - the
machine cannot say when it shut down, or which jobs were in
flight then - the boot brief says only what the snapshot holds
and invents no shutdown story.

## Cold-start honesty rule (OS-050)

The boot brief states its data window, and never implies history
the machine does not have. The rule has four parts, all enforced
by the template composer (`intel/brief.py`
`compose_template_brief`) and scored by the rubric check in
`intel/evals/brief_rubric.md` ("OS-050 cold-start honesty"):

1. Empty history says it is empty. A snapshot with no messages,
   no jobs, and no alerts, and no stated window, produces a
   brief whose window line reads "Window: empty (no history is
   available for this boot)". A capped window that kept nothing
   (0 messages kept) says "The window is empty." on its window
   line. In both cases the brief still says "no activity yet"
   (BRF-012) and names no job, nick, decision, or alert.
2. No shutdown story without a shutdown record. When the snapshot
   states no previous shutdown time, the brief states no shutdown
   time - it does not guess one, borrow one from another window,
   or describe jobs as "carried over" when no shutdown record
   shows them in flight then.
3. No previous session without a previous-session record. A boot
   brief with no previous-session record in the snapshot says
   nothing about a previous session at all - no digest, no
   summary, no "last time" claim. With a record, it says exactly
   the OS-051 digest line below, and nothing more about the
   previous session than that line holds.
4. A stated window bounds the brief. A boot brief with content
   but no stated window keeps the plain "Window: not stated in
   this snapshot" line (BRF-013); it never upgrades that line
   into a claimed shutdown-to-boot span. Content outside the
   stated window is never pulled in to fill a thin brief.

## Previous-session digest line (OS-051)

The boot brief opens with a one-line digest of the previous
session, right after the window line and before Decisions. The
line is rendered by `intel/brief.py`
`previous_session_digest` from the snapshot's
`previous_session` record, which `build_previous_session`
derives from stored state: the last stored brief record (its
`generated_at` timestamp becomes the last-brief time, in ET)
and the job list as it stood at shutdown (status `done` jobs
are the jobs completed, status `open`/`claimed` jobs are the
open threads - this repo has no separate thread store, so the
job list is the thread list). The line reads:

```
Previous session: last brief 2026-10-26 22:00 ET, 2 jobs completed (brief panel; dispatch poster), 1 open thread (watchdog loop)
```

Counts with no titles drop the parentheses ("0 jobs
completed, 0 open threads"). A boot brief with no
previous-session record carries no digest line at all (rule 3
above), and a non-boot brief never carries one even when the
snapshot holds a record: the digest belongs to the boot brief
only. The OS-049 unit must pass `boot=True` when it generates
the boot brief, or the line will not appear. The digest line
counts toward the 220-word morning budget like any other line.

OS-051 follow-up, the boot-path caller: before this change
no caller filled `previous_session`, so a boot brief
carried the digest only when its snapshot hand-stated the
record. Now `intel.py brief --boot` calls
`intel/brief.py` `with_previous_session` first, so a boot
snapshot that states its own `last_brief` record and its
own `shutdown_jobs` list carries the digest without
hand-stating the record; a snapshot that hand-states one
keeps it untouched, and a snapshot that states nothing
usable keeps its exact old shape. The filler reads
neither the snapshot's current jobs list (the window's
jobs at boot, not the shutdown list) nor its
`previous_brief` diff record (job ids with previous
statuses, not a stored brief), and a missing shutdown
list yields no record while an explicitly empty one
states a clean shutdown. NOT proven here, still owed:
the digest against a last brief read from the brief
store itself rather than a caller-stated `last_brief`
(the filler consults no store, so a caller that states
no last brief gets no digest even when an earlier brief
sits in the store), and a Spark-composed boot brief
carrying this line (transport still blocked).

## Boot brief eval set (OS-052)

Three seeded shutdown states, each a hand-written snapshot
scored against the 8 rubric checks in
`intel/evals/brief_rubric.md` plus the OS-050 cold-start
honesty check and the OS-051 digest check. The test is
`tests/test_intel_brief.py` `BootBriefEvalSetTest`. Each
previous-session record is derived with
`build_previous_session` from a stored last-brief time
(2026-10-26 22:00 ET) and a shutdown job list, not typed by
hand. Each brief is a template brief (BRF-008): no Spark call
runs, because real Spark transport is still blocked, and a
Spark-composed boot brief is scored separately when it lands.
All three briefs share one stated window: previous shutdown
2026-10-26 22:00 ET to boot 2026-10-27 02:00 ET, last 500
messages or last 24 hours, whichever is smaller.

- clean: every shutdown job done (brief panel, dispatch
  poster), so the previous session reads 2 jobs completed, 0
  open threads. The boot snapshot carries no current jobs and
  no alerts, so Decisions lists the two overnight markers and
  every other section reports nothing. Score: 8 of 8 rubric
  checks, OS-050 yes, OS-051 yes.
- mid-job: one shutdown job done (spark client) and one still
  claimed (brief panel), so the previous session reads 1 job
  completed, 1 open thread. At boot, job 5 brief panel is
  claimed by rowan, job 6 dispatch poster is open, and alert
  ALERT-MID-1 names the slow boot check. Score: 8 of 8 rubric
  checks, OS-050 yes, OS-051 yes.
- post-crash: one shutdown job done (dispatch poster) and one
  still claimed (watchdog loop), so the previous session reads
  1 job completed, 1 open thread. At boot, job 5 brief panel
  is claimed by rowan, job 7 watchdog loop is blocked with
  reason verbatim "needs the stall fixture from Buffy", and
  alert ALERT-CRASH-1 names the crash. Score: 8 of 8 rubric
  checks, OS-050 yes, OS-051 yes.

Result: 3 of 3 briefs pass. No check failed, so no prompt fix
task was filed. A future failure in this set is filed as a
prompt fix task, not hand-waved.

## The boot brief unit (OS-049)

The unit is `os/services/relay-brief.service`, written to
the META_OS.md service-map shape: oneshot, relay user,
`/opt/relay` checkout, no restart, installed under
`relay.target`. It runs after the relay-ready gate
(`After=relay-ready.service`, boot sequence step 6), with
this command:

```
python3 /opt/relay/intel.py brief --boot --room main
```

The CLI `--boot` path builds a morning-format boot brief
with the boot flag, so the previous-session digest (OS-051)
opens it and the BRF-028 regeneration guard does not hand
back the previous session's brief; a boot record carries
`"boot": true`. The brief is stored in the brief store by
the same path, so the dashboard and `brief --show` read the
same record the unit wrote.

Proven here, stated plainly: the unit file's shape (oneshot
after the ready gate, boot command, relay user, relay.target
install) is guarded by test, and the CLI boot path is proven
on a hand-written snapshot with a fake store: a boot brief
is generated fresh even inside 5 minutes of an earlier
brief, carries the digest, and is marked TEMPLATE. NOT
proven here: the 60-second-after-ready timing on the test
image (no test image exists in this repo, and the ready
gate OS-016 plus the image harness OS-019 have not landed),
and a Spark-composed boot brief (the CLI passes no Spark
client and live Spark transport is blocked, so the unit
currently produces the template fallback, marked TEMPLATE,
by design and not by accident).

## Drivers + tools + apps lines (OS-062)

A boot brief carries three more lines, in this order, after
the previous-session digest (when one exists) and before
Decisions: Drivers, Tools, Skill apps. They are boot-only
lines, like the digest: a non-boot brief never carries them,
even when its snapshot holds a system_state record. They are
rendered by `intel/brief.py` `system_state_lines` from the
snapshot's `system_state` record, which the caller that
builds the boot snapshot fills from live machine state:

```
system_state = {
    "drivers": ["muse-code"],
    "gateway_healthy": True,
    "skill_apps": ["briefing", "dispatch"],
}
```

- Drivers: the agent drivers available on the machine, by
  name, in the order the record lists them, followed by
  "available". With an empty list the line reads "Drivers:
  no drivers reported". The driver names are the OS-053
  driver roster as the machine reports it; this task does
  not invent a driver, and a driver the record does not
  name is not listed.
- Tools: the MCP gateway, the machine's tool service, the
  one local service every agent process reaches its tools
  through. With `gateway_healthy` true the line reads
  "Tools: MCP gateway healthy". With it false the line
  reads "Tools: MCP gateway down, so agents cannot reach
  their tools through it". A down gateway is said to be
  down, never omitted: that is the OS-050 honesty rule
  applied to this line, so a reader can tell a down
  gateway from a brief that simply forgot to mention it.
- Skill apps: the skill apps mounted on the machine, by
  name, in the order the record lists them, followed by
  "mounted". With an empty list the line reads "Skill
  apps: no skill apps mounted".

A field the record does not carry is reported as not
reported, never guessed: "Drivers: not reported in this
snapshot", "Tools: MCP gateway health not reported in
this snapshot", "Skill apps: not reported in this
snapshot". A boot brief over an empty window carries the
three lines too, before "no activity yet": the machine
state is not activity in the window, and a down gateway
must never hide behind an empty room. The three lines
count toward the 220-word morning budget like any other
line, and the BRF-007 budget trim never drops them: they
are not bullet lines, so the trim drops job bullets first.

Proven here, stated plainly: the rendering from a stated
record is guarded by test, including the gateway-down line,
the not-reported lines, the boot-only rule, the empty
window case, and survival of the budget trim. OS-062
follow-up, the boot-path caller: `intel.py brief --boot`
calls `with_system_state` after `with_recovery`, so a
boot snapshot that states its drivers, gateway health,
and skill apps as flat lists (`drivers`,
`gateway_healthy`, `skill_apps`) carries the three lines
with values without a hand-stated record; a snapshot
that hand-states one keeps it, and one that states
nothing usable keeps its exact old shape, still
rendering the three not-reported lines. The caller is
guarded by test the same way, including the gateway
down line, the stated empty list reading none rather
than not reported, the name listed twice, the skipped
malformed name, and the non-bool gateway health that
is never guessed into healthy or down. NOT proven
here, still owed: the lines against live machine state
on the test image. The driver contract (OS-053), the
gateway daemon (OS-058), and the skills loader (OS-065)
have not landed, so the caller fills the record only
from a snapshot that states its machine state, and the
OS-066 integration run is where the lines are proven
against the machine they describe; a Spark-composed
boot brief carrying these lines is owed with the prompt
wiring (DOC-011 gap).

## Environment lines (OS-103)

At launch, a boot brief carries four more lines, in this
order, after the system lines (when the snapshot carries a
system_state record) and before Decisions: Repo, Bus,
Working now, Budget. They are the brief's information
layer: the surroundings the agent wakes up in, in the
brief's plain-English standard. They are boot-only lines,
like the digest and the system lines: a non-boot brief
never carries them, even when its snapshot holds an
environment record. They are rendered by `intel/brief.py`
`environment_lines` from the snapshot's `environment`
record, which the caller that builds the launch snapshot
fills from the sources at generation time:

```
environment = {
    "repo": {"branch": "main", "commit": "a6c190f",
             "dirty": 0, "as_of": 1793093400},
    "bus": {"rooms": ["main"], "messages": 500,
            "as_of": 1793093400},
    "jobs": [{"id": "5", "title": "brief panel",
              "status": "claimed", "claim": "rowan"}],
    "budget": {"lane": "HANA", "spent": 120, "cap": 300,
               "as_of": 1793093400},
    "as_of": 1793093400,
}
```

- Repo: the repo's current state, branch and short
  commit, plus the working tree: "clean" when nothing is
  uncommitted, or the count of uncommitted files. The
  branch and commit are the repo's at generation time;
  this task does not invent a commit, and a repo the
  record does not describe is reported as not reported.
- Bus: the bus state, message count and rooms, in the
  order the record lists them. A bus the record does not
  describe is reported as not reported.
- Working now: who is working on what, claimed jobs
  only, nick and title, in job order. An open job with
  no claim is not work in progress and is assigned to
  nobody; when nobody holds a claimed job the line says
  so plainly instead of padding a name.
- Budget: the lane's budget remaining, spent subtracted
  from cap, or the remaining figure directly when the
  record gives it, with the cap when the record gives
  that too. A budget the record does not describe is
  reported as not reported.

Stale fields are labelled with their age, never silently
presented as current: every valued line carries its
record's as_of time, "(as of 2026-10-27 05:30 ET)", and
a valued line whose record gives no time carries
"(snapshot time not reported)" instead. A reader can
therefore tell a fresh repo line from a line read an
hour ago, and a line with no known age from a current
one. A snapshot with no environment record at all
carries no environment lines, so older boot briefs keep
their exact shape; a record with no usable fields
renders all four lines as not reported.

A boot brief over an empty window carries the four lines
too, before "no activity yet": the surroundings are not
activity in the window, and a budget line must never hide
behind an empty room. The four lines count toward the
220-word morning budget like any other line, and the
BRF-007 budget trim never drops them: they are not
bullet lines, so the trim drops job bullets first.

Proven here, stated plainly: the rendering from a stated
record is guarded by test, including the age labels, the
not-reported lines, the boot-only rule, the empty window
case, and survival of the budget trim. Since then, four
pieces of the live fill are built (OS-103 follow-ups,
2026-10-28): `intel/brief.py` `environment_repo_record`
reads branch, short commit, and dirty count from a local
git checkout, never raising, and a boot template brief
over a record carrying only that part renders the repo
line and the other three as not reported — proven by
tests/test_intel_brief_environment_repo.py against real
temp checkouts, and against this repo's own checkout
(main, its current short commit, its dirty count); and
`environment_jobs_record` reads the claimed jobs, in job
order, out of the snapshot's own jobs list, skipping
open, blocked, done, claim-less, and title-less entries
instead of guessing them into names, and a record
carrying only that part renders the Working now line
and the other three as not reported — proven by
tests/test_intel_brief_environment_jobs.py; and
`build_environment_record` merges the two built parts
into one launch record — repo from git, jobs from the
snapshot's own jobs list, one as_of stamp for the whole
record so the two lines' ages agree — leaving a part
that yields nothing usable out instead of padding it,
so a boot template brief over the merged record carries
the repo and Working now lines and the bus and budget
lines as not reported — proven by
tests/test_intel_brief_environment_record.py against real
temp checkouts; and `environment_bus_record` reads the
message count out of the snapshot's own messages list,
with rooms stated by the caller (snapshot messages carry
no room field, so rooms are never guessed from them),
and `build_environment_record` now merges that part in
too, with the same one-stamp rule — a merged record
over a snapshot with messages carries the Bus line and
the budget line as not reported — proven by
tests/test_intel_brief_environment_bus.py; and
`environment_budget_record` reads the lane's figures
out of the snapshot's own budgets list (the OS-079
entries: lane, spent, cap, or remaining), skipping
malformed entries instead of guessing them into a
figure, and `build_environment_record` now merges that
part in too, with a new optional lane argument and the
same one-stamp rule — a merged record over a snapshot
carrying a budgets list carries the Budget line —
proven by tests/test_intel_brief_environment_budget.py;
and `with_boot_environment` is the launch-path caller
the earlier follow-ups left owed: `intel.py brief --boot`
— the path relay-brief.service runs — fills a snapshot
that carries no environment record before generating,
so a bare launch snapshot carries the live repo line
from its own checkout plus the bus, jobs, and budget
lines from its own lists, and a snapshot that
hand-states an environment record keeps it, never
overwritten — proven by
tests/test_intel_brief_boot_environment.py and by a
dry-run `brief --boot` over this checkout carrying all
four lines with one stamp.
NOT proven here, still owed: the lines against full
live launch state on a booted image, and a
Spark-composed boot brief carrying these lines. The
budget part reads the snapshot's stated figures, not a
live ledger: the budget config
(Milo OS-085) has landed since this section was
written, but there is still no spend ledger for a
filler to read spent from, so a launch snapshot that
carries no budgets list still reads not reported, and
a Spark-composed boot brief carrying these lines is
owed with the prompt wiring (DOC-011 gap).

## Settled decisions + spend vs budget lines (OS-079)

A brief opens with what is already settled and what
is already spent, before the new work. The brief
carries one settled-decisions line, then one
spend-vs-budget line per lane, in that order, right
after the window line and before the digest and the
sections. They are rendered by `intel/brief.py`
`memory_budget_lines` from the snapshot's
`memory_budget` record, which the caller that builds
the brief snapshot fills from the memory service and
the budget config at generation time:

```
memory_budget = {
    "settled_decisions": ["Morning brief format is final"],
    "budgets": [{"lane": "HANA", "spent": 120, "cap": 300,
                 "as_of": 1793093400},
                {"lane": "MILO", "remaining": 90, "cap": 200}],
    "as_of": 1793093400,
}
```

- Settled decisions: the decisions the memory
  service holds as settled, named verbatim, in the
  order the record lists them, joined with semicolons
  on one line. They are pulled from memory, not
  re-derived from raw history: a decision the memory
  record does not name is not listed, and a brief
  never reconstructs a settled decision from the
  window's messages. With an empty list the line reads
  "Settled decisions from memory: none reported".
- Memory down: when the record says the memory
  service did not answer (`memory_down` true), the
  line says so plainly — "memory service down, so no
  settled decisions are shown" — and shows no
  decision at all. A down service is said to be down,
  never hidden behind an absent line: that is the
  OS-050 honesty rule applied to this line, so a
  reader can tell a down memory service from a brief
  that simply forgot to mention it.
- Spend vs budget: one line per lane, in the order
  the record lists them. A lane with spent and cap
  reads "Spend: HANA lane: 120 of 300 budget (180
  remaining)"; a lane with remaining and cap reads
  "Spend: MILO lane: 90 remaining of 200 cap"; a lane
  with remaining only reads "Spend: MILO lane: 90
  remaining". A budget entry without a lane name or
  without a usable figure is skipped, and a record
  with no usable budget entry renders "Spend vs
  budget: not reported in this snapshot" instead of a
  made-up figure.

Stale fields are labelled with their age, never
silently presented as current: every line carries its
record's as_of time, "(as of 2026-10-27 05:30 ET)",
and a line whose record gives no time carries
"(snapshot time not reported)" instead. A budget
entry with its own as_of time carries that time, not
the record's.

The lines are rendered whenever the snapshot carries
a memory_budget record, in a boot brief and in a
morning brief alike: OS-079 covers both, and the
template composer renders the morning brief's
fallback path too, so the record's presence is the
opt-in. A snapshot with no memory_budget record at
all carries none of the lines, so older briefs keep
their exact shape. A brief over an empty window
carries the lines too, before "no activity yet":
settled decisions and budgets are not activity in
the window, and a down memory service must never
hide behind an empty room. The lines count toward
the 220-word morning budget like any other line,
and the BRF-007 budget trim never drops them: they
are not bullet lines, so the trim drops job bullets
first.

Proven here, stated plainly: the rendering from a
stated record is guarded by test, including the
verbatim decision, the memory-down line, the
not-reported lines, the no-record case, the morning
brief case, the empty window case, and survival of
the budget trim. OS-079 follow-up: the brief path
now fills the record first (`intel/brief.py`
`with_memory_budget`, called by `intel.py brief`
for boot, morning, and ondemand), so a snapshot
that only carries a budgets list — and, when the
caller states them, settled decisions or a down
memory service — carries the lines, with one stamp;
a snapshot that hand-states a record keeps it, and
a snapshot that states nothing usable keeps its
exact old shape. Proven live, not just in tests: a
dry-run morning brief over a fixture snapshot
carried the stated settled decision and the HANA
spend line over an empty window. NOT proven here,
still owed: the lines against live state. No caller
in this repo yet fills `memory_budget` from a
memory service: the budget config (Milo OS-085) has
landed as `intel/budgets.py`, but there is still no
spend ledger for a filler to read spent from and no
memory service for it to read settled decisions
from, so the lines in practice read only what the
snapshot's own lists state, and a Spark-composed
brief carrying these lines is owed with the prompt
wiring (DOC-011 gap).

## Recovery line (OS-127)

At boot, a boot brief carries one more line, after the
environment lines (when the snapshot carries an
environment record) and before Decisions: the
in-flight-jobs-recovered line. It is the boot
checklist item 13 in META_OS.md, and it is the line
that proves the reboot was a shift change and not a
quiet loss: it names what the lease sweep recovered,
and it is reconciled against the sweep, so a job that
vanished silently can never produce a clean line. It
is a boot-only line, like the digest, the system
lines, and the environment lines: a non-boot brief
never carries it, even when its snapshot holds a
recovery record. It is rendered by `intel/brief.py`
`recovery_line` from the snapshot's `recovery`
record, which the caller that builds the boot
snapshot fills from the lease sweep record at
generation time:

```
recovery = {
    "recovered": [{"id": "5", "title": "brief panel",
                   "baton_step": "step 2"},
                  {"id": "6", "title": "dispatch poster",
                   "baton_step": "step 1"}],
    "sweep_count": 2,
    "corrupted": [],
}
```

- Recovered: each recovered job, in sweep order, by
  job id and title, with the baton step it resumed
  from: "job 5 brief panel (resumed at step 2)". A
  recovered job whose record gives no baton step is
  named with "step not reported", never with an
  invented step. A recovered job whose record is
  unreadable makes the whole line incomplete, never a
  partial clean count.
- Sweep count: the lease sweep's own recovered count.
  The line is reconciled, not merely counted: the
  clean count is rendered only when the sweep count
  equals the number of recovered job records. When
  they disagree, the line says recovery is
  incomplete, gives both counts, and names no clean
  total, so the vanished job is visible as a gap
  instead of hidden inside a tidy number.
- Clean shutdown: a reconciled record with no
  recovered jobs reads "0 recovered", plainly. It is
  the only zero the line ever prints: a snapshot
  with no recovery record at all carries no recovery
  line, so a brief never claims zero recovered
  without a sweep record to reconcile against, and
  older boot briefs keep their exact shape.
- Corrupted: a job whose record the sweep found
  corrupted makes the line incomplete and is named:
  "job 7 watchdog loop has a corrupted record". The
  line never prints a clean count beside a corrupted
  job, and it never prints a false all-clear.
- No sweep count: a record that names recovered jobs
  but gives no sweep count to reconcile against says
  recovery is incomplete, never a clean count.

A boot brief over an empty window carries the line
too, before "no activity yet": the recovered jobs are
not activity in the window, and an incomplete recovery
must never hide behind an empty room. The line counts
toward the 220-word morning budget like any other
line, and the BRF-007 budget trim never drops it: it
is not a bullet line, so the trim drops job bullets
first.

Proven here, stated plainly: the rendering from a
stated record is guarded by test, including the
reconciled count, the clean zero, the sweep
mismatch, the corrupted job, the missing sweep
count, the missing baton step, the boot-only rule,
the no-record case, the empty window case, and
survival of the budget trim. OS-127 follow-up, the
boot-path caller: `intel.py brief --boot` calls
`with_recovery` after `with_previous_session`, so a
boot snapshot that states the sweep's own outcome
(`sweep_recovered`, `sweep_count`,
`sweep_corrupted`) carries the line without a
hand-stated record; a snapshot that hand-states one
keeps it, and one that states no sweep outcome
keeps its exact old shape. The caller is guarded by
test the same way, including the clean zero, the
mismatch, the corrupted job, the missing sweep
count, the missing baton step, the job listed
twice, and the skipped entry that never reconciles
into a clean count. NOT proven here, still owed:
the line against a real OS-126 plug-pull drill, and
against a live lease sweep at all: the sweep
verification (Milo OS-129) has not landed, so the
caller fills the record only from a snapshot that
states its sweep outcome, and a Spark-composed boot
brief carrying this line is owed with the prompt
wiring (DOC-011 gap).

## Federation section (OS-117)

The morning brief gains one more section, after Watch
items and before Screenshots (when screenshots
render): Federation. It is the crew of crews section:
one brief for every machine Dale runs, so he reads
what each joined machine's crew did, the
cross-machine jobs and their state, and the trust
events overnight, in the brief's plain English
standard. The morning brief format already carries
the section; a boot brief, which is the morning
format, carries it too when its snapshot holds a
federation record. It is rendered by `intel/brief.py`
`federation_lines` from the snapshot's `federation`
record, which the caller that builds the brief
snapshot fills from the joined machines' room record
at generation time:

```
federation = {
    "machines": [{"name": "machine-a",
                  "completions": ["brief panel",
                                  "dispatch poster"],
                  "cross_machine_jobs": [
                      {"id": "3", "title": "watchdog loop",
                       "status": "claimed"}]},
                 {"name": "machine-b",
                  "completions": ["board grouping"],
                  "cross_machine_jobs": []}],
    "trust_events": [
        {"kind": "refusal", "machine": "machine-c",
         "detail": "unsigned job refused"},
        {"kind": "join", "machine": "machine-b",
         "detail": "signed jobs accepted"}],
}
```

- Two machines, or no section at all. The section
  exists only for a real crew of crews: a record
  naming at least two usable machines renders it, and
  a record naming one machine renders it absent,
  never empty padded. A snapshot with no federation
  record at all carries no section, so older briefs
  keep their exact shape.
- Per machine: one line, in record order, naming the
  machine, the titles its crew completed, and its
  cross-machine jobs with id, title, and status:
  "machine-a: completed brief panel, dispatch
  poster; cross-machine jobs: job 3 watchdog loop
  (claimed)". A machine with no completions reads
  "no completions reported", never a padded title.
  A cross-machine job without an id and a title is
  skipped, never guessed.
- Trust events: one line each, after the machine
  lines, in record order. A join reads "Trust:
  machine-b joined the federation: signed jobs
  accepted". A refusal reads "Trust: machine-c was
  refused: unsigned job refused". A refusal with no
  detail reads "reason not reported", never an
  invented reason. A trust event without a machine
  name is skipped.
- Honesty, as in every other section: completions,
  job titles, and trust details are named verbatim
  from the record, never re-derived from raw
  history. A brief over an empty window carries the
  section too, before "no activity yet": what other
  machines' crews did is not activity in this
  window. The section counts toward the 220-word
  morning budget like any other section, and its
  bullet lines may be dropped by the BRF-007 trim
  when a brief runs over budget.

Proven here, stated plainly: the rendering from a
stated record is guarded by test, including the
two-machine case, the single-machine absence, the
no-record case, the no-completions line, the
refusal without a detail, and the empty window
case. The morning-path caller is proven too:
`intel/brief.py` `with_federation` fills the record
from the snapshot's own stated joined_machines list
(names, completions verbatim, cross-machine jobs
with id, title, and status) and its stated
trust_events list (joins and refusals), with one
stamp, and `intel.py brief` calls it for boot and
morning briefs (ondemand left alone, the section
belongs to the morning/daily brief); a snapshot
that hand-states a record keeps it, a snapshot
stating fewer than two usable machines gets no
record, a machine named twice counts once, and
malformed entries are skipped, never guessed, so
older briefs keep their exact shape. NOT proven
here, still owed: the section against a live
federation. The join flow (Pax OS-110), trust
enforcement (Milo OS-112), the two-machine drill
(Buffy OS-113), and the policy ruling (Dale
OS-115) have not landed, so the caller in practice
fills the record only from a snapshot that states
its joined machines, and a Spark-composed morning
brief carrying this section is owed with the prompt
wiring (DOC-011 gap). This is a Phase B [B] task,
built early as a renderer plus a stated-input
caller; the federation minimum itself is not
claimed done here.

## Dale's daily brief (OS-075)

The morning brief becomes Dale's actual daily brief
on the desktop session: overnight crew results,
today's queue, and what needs his word, in the
brief's plain-English standard. Until the desktop
session exists, the section lives in the morning
format, which the daily brief extends: one section,
after Watch items and before Long-term memory,
named Daily brief. It is rendered by `intel/brief.py`
`daily_lines` from the snapshot's `daily` record,
which the caller that builds the brief snapshot
fills at generation time:

```
daily = {
    "overnight_results": ["shipped the brief panel"],
    "todays_queue": [{"id": "7", "title": "boot shot"}],
    "needs_word": [{"question": "ship the demo cut?",
                    "job": "7"}],
}
```

- One line per item, in record order, in plain
  English. An overnight result reads "Overnight
  result: shipped the brief panel". A queue job
  reads "Today's queue: job 7 boot shot". A
  question waiting on Dale's word reads "Needs
  your word: ship the demo cut? (job 7)", or
  without the job tag when the record gives no
  job. Results and questions are named verbatim
  from the record, never re-derived from raw
  history, and never paraphrased away.
- Unusable entries are skipped, never padded. A
  queue job without both an id and a title is
  skipped. A needs-word entry without a question
  is skipped. A result that is not a plain string
  is skipped.
- An empty category reads none reported, never a
  padded item: "Overnight results: none
  reported", "Today's queue: none reported",
  "Needs your word: none reported". A record
  with nothing usable still renders those three
  lines, so a reader can tell the daily section
  was checked and held nothing, rather than
  guessing whether it was checked at all. A
  snapshot with no daily record at all carries
  no section, so older briefs keep their exact
  shape.
- Every line carries its age label from the
  record's as_of time, or the snapshot-time-not-
  reported label when the record gives no time, so
  a stale daily section is never silently
  presented as current. The lines are plain
  lines, not bullets, so the BRF-007 budget trim
  never drops a question waiting on Dale's word
  ahead of a watch item. A brief over an empty
  window carries the section too, before "no
  activity yet": overnight results, today's
  queue, and what needs his word are not
  activity in this window.
- Format changes from Dale's feedback belong in
  the prompt history when real daily use
  produces them. None is recorded here yet,
  because no daily brief has run on the daily
  machine; inventing feedback ahead of use would
  break the brief-never-invents-a-fact rule.

Proven here, stated plainly: the rendering from a
stated record is guarded by test, including the
all-three-categories case, the no-record case,
the skipped-entry case, the empty-record lines,
the empty window case, the budget-trim case,
and the missing-time age label. OS-075 follow-up:
the morning-path caller now fills `daily` from the
snapshot itself — `intel/brief.py` `with_daily`
builds the record from the snapshot's own stated
overnight_results and needs_word lists (verbatim,
never re-derived from messages) and its jobs list
(open or claimed jobs with an id and a title, each
job once), one as_of stamp, hand-stated record
winning unchanged, nothing usable yielding no
record so older briefs keep their exact shape;
`intel.py` brief calls it for boot and morning
briefs (ondemand briefs are left alone, since the
daily section belongs to the morning/daily brief),
and a dry-run morning brief over a fixture snapshot
carried all three categories. NOT proven here,
still owed: the section in a daily brief read on
the desktop session. The desktop session (Rowan
OS-071) has not landed and two weeks of daily
briefs on the daily machine have not run, and a
Spark-composed daily brief carrying this section
is owed with the prompt wiring. This is a Phase
B [B] task, built early as a renderer plus a
snapshot caller; the daily brief itself, and its
two-week acceptance, are not claimed done here.

## Long-term memory lines (OS-092)

The daily brief (OS-075) surfaces long-term memory:
decisions aging out, commitments made weeks ago
that are due, and context a fresh agent would miss,
drawn from the memory service, not re-derived from
raw history. Until the daily brief exists, the lines
live in the morning format, which the daily brief
extends: one section, after Watch items, named
Long-term memory. It is rendered by `intel/brief.py`
`memory_depth_lines` from the snapshot's
`memory_depth` record, which the caller that builds
the brief snapshot fills from the memory service
at generation time:

```
memory_depth = {
    "aged_decisions": [{"decision": "freeze the demo "
                                     "fixture at noon",
                        "original_date": "2026-10-01"}],
    "due_commitments": [{"commitment": "ship the demo "
                                        "cut",
                         "due": "2026-11-03"}],
    "fresh_context": ["the demo room is build only, "
                      "never a posting room"],
}
```

- One line per item, in record order, in plain
  English. An aged decision reads "Aged decision:
  freeze the demo fixture at noon (from
  2026-10-01)". A due commitment reads "Due
  commitment: ship the demo cut (due 2026-11-03)".
  Fresh-agent context reads "Fresh-agent context:
  the demo room is build only, never a posting
  room". Dates and texts are named verbatim from
  the record, never re-derived from raw history.
- Missing dates are said, never guessed. An aged
  decision with no original date reads "original
  date not reported". A due commitment with no due
  date reads "due date not reported". An entry
  without its text is skipped, never padded.
- An empty category reads none reported, never a
  padded item: "Aged decisions: none reported",
  "Due commitments: none reported", "Fresh-agent
  context: none reported". A record with nothing
  usable still renders those three lines, so a
  reader can tell the memory was checked and held
  nothing, rather than guessing whether it was
  checked at all.
- A down memory service is said, never hidden
  behind an absent section (OS-050 honesty rule):
  "Long-term memory: memory service down, so no
  aged decisions, due commitments, or fresh-agent
  context are shown", and no item is shown beside
  it. A snapshot with no memory_depth record at all
  carries no section, so older briefs keep their
  exact shape.
- Every line carries its age label from the
  record's as_of time, or the snapshot-time-not-
  reported label when the record gives no time, so
  a stale item is never silently presented as
  current. The lines are plain lines, not bullets,
  so the BRF-007 budget trim never drops an aged
  commitment ahead of a watch item. A brief over an
  empty window carries the section too, before "no
  activity yet": long-term memory is not activity
  in this window.

Proven here, stated plainly: the rendering from a
stated record is guarded by test, including the
all-three-categories case, the memory-down line,
the no-record case, the missing-date lines, the
empty-record lines, the empty window case, and the
budget-trim case. NOT proven here, still owed: the
lines against a live memory service. The morning
path now fills `memory_depth` from the snapshot's
own stated lists (`intel/brief.py` `with_memory_depth`,
called by `intel.py` brief for boot and morning
briefs, ondemand left alone): aged decisions, due
commitments, and fresh-agent context verbatim from
the stated lists, a down service carried alone with
no item beside it, a hand-stated record winning
unchanged, and a snapshot stating nothing usable
gaining no record, so older briefs keep their exact
shape. The filler still reads no live memory
service: the daily brief itself (OS-075) has not
landed, because the desktop session (Rowan OS-071)
has not landed and two weeks of daily briefs on the
daily machine have not run, and the memory service
depth (OS-078 in-window service, OS-087 compaction)
is not wired as a brief source, so the lines carry
only what a caller states, and a Spark-composed
daily brief carrying these lines is owed with the
prompt wiring. This is a Phase B [B] task, built
early as a renderer plus a morning-path caller; the
daily brief itself, and its two-week acceptance, are
not claimed done here.

## Not in this spec (later boot tasks, named, not done here)

- OS-049: the `relay-brief.service` systemd unit. DONE in
  this spec (the section above, the unit file, the CLI
  `--boot` path, and the unit tests) - it is no longer a
  later task. The test-image timing proof is still owed, as
  stated in that section.
- OS-050: the cold-start honesty rule. DONE in this spec (the
  rule section above, the rubric check, and the template
  composer behavior) - it is no longer a later task.
- OS-051: the previous-session digest line. DONE in this spec
  (the section above, the rubric check, and the template
  composer behavior) - it is no longer a later task.
- OS-052: the boot brief eval set. DONE in this spec (the
  eval set section above, the rubric checks, and the template
  composer behavior) - it is no longer a later task.
- OS-062: the drivers + tools + apps line. DONE in this
  spec (the section above, the rubric check, and the
  template composer behavior) - it is no longer a later
  task. The test-image proof against live state is still
  owed, as stated in that section.
- OS-103: the environment lines. DONE in this spec (the
  section above, the rubric check, and the template
  composer behavior) - it is no longer a later task. The
  live-launch proof against git, bus, queue, and budget
  config state is still owed, as stated in that section.
- OS-079: the settled-decisions and spend-vs-budget lines. DONE in
  this spec (the section above, the rubric check, and the template
  composer behavior) - it is no longer a later task. The live-state
  proof against a memory service and a budget config is still owed,
  as stated in that section.
- OS-127: the in-flight-jobs-recovered line reconciled against
  the lease sweep. DONE in this spec (the section above, the
  rubric check, and the template composer behavior) - it is no
  longer a later task. The OS-126 drill proof against a live
  lease sweep is still owed, as stated in that section.
- OS-117: the crew-of-crews federation section. DONE in
  this spec (the section above, the rubric check, and the
  template composer behavior) - it is no longer a later
  task. The live-federation proof against joined machines
  is still owed, as stated in that section.

A reader who wants one of those lines must wait for its task;
none of them may be read into this spec.

## Hand-checked example (template brief, fixture state)

The example below is the template composer's output
(`intel/brief.py` `compose_template_brief`, BRF-008) over a
hand-written boot fixture, not a Spark-composed brief and not a
boot test on the test image. The fixture is hand-written because
no boot fixture has landed in this repo yet; it is not Buffy's
fixture, and it is not the demo fixture. Every line below was
checked against the fixture manifest that follows it.

```
TEMPLATE
Window: boot window: previous shutdown 2026-10-26 22:00 ET to boot 2026-10-27 02:00 ET, last 500 messages or last 24 hours, whichever is smaller

Decisions
- decision: freeze the demo fixture at noon
- done: watchdog boot check passes
- decision: carry the open jobs into the morning

In flight
- 5 brief panel (claimed)
- 6 dispatch poster (open)

Owners
- rowan: brief panel

Blocked and why
- 7 watchdog loop: needs the stall fixture from Buffy

Watch items
- ALERT-BOOT-1: watchdog saw a slow boot check during boot
```

Fixture manifest, line by line:

- Window: previous shutdown 2026-10-26 22:00 ET, boot
  2026-10-27 02:00 ET, last 500 messages or last 24 hours,
  whichever is smaller (BRF-023 cap, stated in the window line).
- Decisions: pax "DECISION: freeze the demo fixture at noon"
  (overnight decision); milo "DONE: watchdog boot check passes"
  (watchdog during boot, as a done marker); del "DECISION:
  carry the open jobs into the morning" (overnight decision).
- In flight at shutdown, still in flight at boot: job 5 "brief
  panel", claimed by rowan; job 6 "dispatch poster", open.
- Owners: rowan holds job 5. Job 6 is unclaimed and is assigned
  to nobody.
- Blocked: job 7 "watchdog loop", reason verbatim "needs the
  stall fixture from Buffy".
- Watch items: alert ALERT-BOOT-1, summary "watchdog saw a slow
  boot check during boot" (what the watchdog saw during boot).
- Word count: 90 words, inside the 220-word morning budget.
- Marker: the brief is marked TEMPLATE in its first line, so no
  reader mistakes it for a Spark-composed brief. A Spark-composed
  boot brief cannot be produced until real Spark transport lands,
  and it is scored separately then.

## Status

OS-048 v1, 2026-10-27, plus OS-050 (cold-start honesty rule),
2026-10-27, plus OS-051 (previous-session digest line),
2026-10-27, plus OS-052 (boot brief eval set), 2026-10-27,
plus OS-062 (drivers + tools + apps lines), 2026-10-27,
plus OS-103 (environment lines), 2026-10-27,
plus OS-127 (in-flight-jobs-recovered line), 2026-10-27,
plus OS-079 (settled decisions + spend vs budget lines),
2026-10-27, plus OS-117 (crew-of-crews federation section),
2026-10-27.
Spec and hand-checked example only, plus the OS-050 rule, the
OS-051 digest line, the OS-052 eval set, the OS-062
system lines, the OS-103 environment lines, and the OS-127
recovery line, and the OS-079 memory + budget lines, and
the OS-117 federation section enforced
in the template composer and scored in the rubric. No systemd unit, no
boot test on the test image, no Spark prompt wiring: the prompt
files are not wired to the inline composer prompt (DOC-011 gap),
so this spec is a document beside the prompts, not a prompt the
composer reads yet. No bus post was made for this file.
