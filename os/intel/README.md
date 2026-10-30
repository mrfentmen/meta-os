# Relay Intelligence — intel package

This file holds the intel wire formats and record schemas, plus
the briefing engine section (BRF-030) and the dispatch
section (DSP-020) below. The wire format freeze itself is
FND-020, in the section below.

## Wire format freeze: FND-020 (Pax, 2026-10-26)

Intel announcement lines are one-line bus messages that point at a
Redis record. They are never the record itself: the full text lives
in Redis (intel/store.py key layout), the line carries only the id
and the fields a reader needs to triage without a lookup. This
mirrors the jobs.py convention: wire announcements are best-effort
chat lines, Redis state is the source of truth.

Bus framing: a line is the message body of a plain-text
`<nick>: <text>` bus message, posted by the announcing nick. The
`BRIEF:`, `ALERT:`, or `DISPATCH:` prefix is part of the body, not
part of the nick.

### Rules for every intel line

- Exactly one line. No newline, no trailing free text beyond the
  shape. A line that does not match its shape exactly is not an
  intel line; parsers ignore it.
- No secrets, no spec text, no job titles, no credential-shaped
  strings. A line names a record; it never quotes one.
- Ids contain no spaces. Readers split a line on spaces: the first
  token is the prefixed id, the remaining tokens are the shape's
  fixed fields in order.
- FROZEN DOES NOT MEAN LIVE. No intel announcement line is posted
  until Dale approves posting under GOV-002. BRF-010, WDG-015, and
  DSP-010 are all held on that rule today. Lanes build against
  these shapes now; the posting call sites stay gated.
- A frozen shape changes only with a new dated note in this
  section, never a silent edit. Lanes already parsing a shape must
  keep working across any change, or the change does not land.

### BRIEF: a brief was stored (writer: BRF-010)

Shape:

```
BRIEF:<room>:<ts> <kind>
```

- `<room>` is the relay_common.clean_room() output for the brief's
  room, with `main` for the default room (same rule as
  intel/store.py brief_key). `<ts>` is the brief's `generated_at`
  Unix timestamp, and must match the `<ts>` in the store key
  `muse-bus:intel:brief:<room>:<ts>`.
- `<kind>` is one of `morning`, `onjoin`, `ondemand` (the
  BRIEF_KINDS enum in intel/brief.py).
- Example: `BRIEF:main:1761500000 morning`
- The line carries no section text. Sections live only in the
  stored brief record (FND-032 schema below).

### ALERT: a critical alert was raised (writer: WDG-015)

Shape:

```
ALERT:<id> <severity> <kind>
```

- `<id>` is the alert writer's store id, verbatim as in the store
  key `muse-bus:intel:alert:<id>`. It contains no spaces; colons
  inside it are allowed because readers split on spaces, not
  colons. The freeze does not fix the id scheme: whatever WDG-010
  stores as `<id>` is what the line carries.
- `<severity>` is `critical` or `warning`. `<kind>` is the detector
  kind, e.g. `presence-stall`, `progress-stall`, `dead-dep`,
  `missing-dep`, `file-collision` (the `kind` field of the alert
  record in intel/watchdog.py).
- Only critical alerts are announced. Warnings accumulate silently
  for the brief and the dashboard and never produce a line.
- Example: `ALERT:presence-stall-pax-123 critical presence-stall`
- The line carries no explanation text and no suggested fix. Both
  live only in the stored alert record.

### DISPATCH: a plan was posted (writer: DSP-010)

Shape:

```
DISPATCH:<id> -> <n> jobs
```

- `<id>` is the dispatch record's store id, verbatim as in the
  store key `muse-bus:intel:dispatch:<id>`. It contains no spaces.
- `<n>` is the number of jobs actually posted to the queue, not the
  number planned. A plan approved for 4 jobs that posts 3 announces
  `-> 3 jobs`.
- Example: `DISPATCH:plan-20261026-001 -> 4 jobs`
- The line carries no job titles, no file lists, no specs. Those
  live in the dispatch record and the posted jobs.

### Collision note: the older overseer DISPATCH: line

mos/overseer.py already posts a different line with the same
prefix:

```
DISPATCH:<job-id> -> <n> worker(s)
```

That line reports one overseer job fanned out to workers: its id
is a numeric jobs.py job id and its trailing word is `worker(s)`.
The intel line reports a dispatch plan posted as jobs: its id is
a dispatch record id and its trailing word is `jobs`. This freeze
does not change the overseer line. Parsers tell them apart by the
trailing word, never by the prefix alone: a `worker(s)` line is
never a plan post, and a `jobs` line is never an overseer fan-out.

### Status

Shapes above are frozen by Pax 2026-10-26 as the lines BRF-010,
WDG-015, and DSP-010 build against. Lane sign-off is still owed
in the lane notes: Hana (BRIEF:), Milo (ALERT:), Rowan (DISPATCH:
as the dashboard consumer). Until each lane signs, treat that
lane's shape as Pax's freeze, not the crew's: the shape does not
change without a dated note here, but the crew freeze is complete
only when all three have signed.

2026-10-27 Hana sign-off on BRIEF: only (BRF-010):
intel.brief.format_brief_announcement renders the shape above,
tested against the README example; posting remains held under
GOV-002. Milo and Rowan sign-offs are still owed, so the crew
freeze is not complete on this note.
## Brief record schema — FND-032 (Hana, with Pax)

A brief record is the dict stored through `intel.store.put_brief`
under key `muse-bus:intel:brief:<room>:<ts>`, where `<ts>` is the
brief's `generated_at` Unix timestamp. Every field below is
required unless marked optional. `intel.brief.validate_brief_record`
checks a record against this schema and returns a list of errors;
an empty list means the record is valid.

| Field | Type | Meaning |
|---|---|---|
| `room` | string, non-empty | Room the brief covers. |
| `generated_at` | int, Unix timestamp | When the brief was generated. Must match the `<ts>` in its store key. |
| `kind` | string, one of `morning`, `onjoin`, `ondemand` | Which brief this is. |
| `sections` | dict | The five brief sections, each a list of strings: `Decisions`, `In flight`, `Owners`, `Blocked and why`, `Watch items`. A section with nothing to report is an empty list, never a missing key, and never an invented entry. |
| `source_window` | string or dict | The window the snapshot actually covered. A string states it in words; a dict is the BRF-023 cap record (`max_messages`, `max_hours`, `messages_kept`, `messages_dropped`). It must never claim history the machine does not have. |
| `model` | string, non-empty | Model that composed the brief, or `template` for a BRF-008 template fallback brief with no language-model call. |
| `spend_id` | string or null | Spend ledger entry for the composing call, or null when there was no call (template fallback). |

Rules that are part of the schema, not just good practice:

- A blocked reason in `sections["Blocked and why"]` is verbatim
  from the job record, except when redaction (BRF-014) replaces
  a credential-shaped string with `[redacted]`.
- No section may contain a job id, title, nick, decision, or
  alert id that is not in the snapshot the brief was built from.
- A brief older than 2 hours is stale: readers use
  `generated_at` plus `age_seconds` (BRF-020) to label it, and
  must not present it as current.

## Briefing engine — BRF-030 (Hana)

How to run a brief, end to end, from this file alone. No step
below needs a bus post, a secret, or a Spark call: with no client
passed, the engine builds a template brief from the extractors.
A Spark-composed brief is the same pipeline with a client; the
Spark pass over decisions named in BRF-004 is NOT implemented,
because real Spark transport is a hard blocker on record (fake
transport rejected, endpoint and key unnamed). Nothing here
claims a Spark-composed brief has been produced.

### Ground rule

A brief never invents a fact. Every job id, title, nick,
decision, and alert id in a brief must appear in the snapshot
the brief was built from. A section with nothing to report is
empty, never padded with an invented entry. Blocked reasons are
quoted verbatim from the job record, except when redaction
(BRF-014) replaces a credential-shaped string with `[redacted]`.
Brief prose stays English even when room chatter is in another
language; a job title or blocked reason that must be named is
quoted exactly as recorded, never translated (BRF-021).

### Inputs

The input is a snapshot dict, built by `intel.ingest.snapshot`
(room messages, jobs, presence, capabilities) or handed to the
CLI as a JSON file. Its shape is documented at the top of
`intel/brief.py`: `messages` (dicts or plain `"<nick>: <text>"`
bus strings), `jobs` (id, title, status, claim, note,
claimed_at, lease_until), `presence` (nicks), `caps`, and
`alerts` (id, summary). Missing sections are treated as empty.

### Extractors (`intel/brief.py`)

- Decisions (BRF-004): messages starting with `DONE:`,
  `BLOCKED:`, or `DECISION:` (case-insensitive), via
  `extract_decisions`. The Spark pass over decisions is the
  unimplemented part named above.
- Blocked (BRF-005): every blocked job with its reason
  verbatim, via `extract_blocked`.
- Owners (BRF-006): claimed jobs mapped claim nick -> title ->
  last progress age, via `extract_owners`.
- Watch items (BRF-022): open watchdog alerts by id plus a
  one-line summary, via `extract_watch_items`.
- On-join offer (BRF-029): a present nick with no prior message
  in the room yields an offer record only, via
  `offer_onjoin_brief`; no brief is generated until invoked.

### Prompts (`intel/prompts/`)

- `brief_morning.md` (BRF-001, v1): the morning brief.
- `brief_onjoin.md` (BRF-002, v1): the welcome brief for a
  nick that just joined; the reader must be able to start work
  from it alone.
- `brief_ondemand.md` (BRF-003, v1): any room, any window,
  reusing the morning sections with the window as a parameter.
All three produce the same five sections: Decisions, In flight,
Owners, Blocked and why, Watch items. All three state the
window they cover in their first lines, and say so when the
window starts mid-story (BRF-013, trimmed-history honesty).

### Budgets (BRF-034 / FND-034)

Word budgets, enforced as constants `BRIEF_BUDGETS` in
`intel/brief.py` and checked by `brief_exceeds_budget`:
morning 220 words, on-join 150 words, on-demand 300 words.
The composer trims to budget (`compose_brief`); the template
brief has no rewrite pass, so on a long-title day it can run
over budget — that limit is recorded in `intel/evals/log.md`
under BRF-017 and is not hidden by scoring on short titles.

### Window cap, regeneration guard, staleness

- Window cap (BRF-023): a brief covers the last 500 messages
  or the last 24 hours, whichever is smaller, via
  `cap_snapshot_window`. The cap is recorded in the brief
  record's `source_window`. An ad hoc window (`--since 2h`)
  replaces the 24-hour side of the cap, never extends it.
- Regeneration guard (BRF-028): the same room, kind, and
  window requested twice inside 5 minutes returns the stored
  brief (identical id), with no new composing call and no new
  spend entry.
- Staleness (BRF-020): a brief older than 2 hours renders with
  its age: `generated_at` plus `age_seconds` from
  `brief_age_seconds`. Never present a stale brief as current.
- Empty room (BRF-012): no history yields a short brief saying
  there is no activity yet, never an error or invented content.

### Fallback and failure copy

- Fallback (BRF-008): if the composing call fails, the engine
  emits a template brief built from the extractors alone,
  marked `TEMPLATE`, with `model` set to `template` and
  `spend_id` null. A template brief is a real brief, not a
  placeholder, and it says so.
- Failure copy (BRF-026): only three canned one-liners exist,
  in `BRIEF_FAILURE_COPY`, via `brief_failure_line`: brief
  unavailable, brief writer down, and no data. No other failure
  copy may be improvised. A room with no briefs at all gets the
  no-data line, not empty output.

### Running it

From the repo root:

```
python3 intel.py brief --morning --room <room> --snapshot <snapshot.json>
python3 intel.py brief --ondemand --room <room> --since 2h
python3 intel.py brief --boot --room <room> --snapshot <snapshot.json>
python3 intel.py brief --list --room <room>
python3 intel.py brief --show --room <room> --ts <generated_at>
```

`--morning` without `--since` runs today's morning brief
(BRF-011: the 08:00 ET daily brief; `--dry-run` prints without
storing). The printed `brief id: <room>:<generated_at>` is the
handle for `--show` and for the eval log. Stored briefs live
under `intel.store.put_brief` keys
`muse-bus:intel:brief:<room>:<ts>` with a per-room index
(BRF-009); the record schema above is the contract a stored
brief must pass, checked by `validate_brief_record`.

### Eval pointer

Score every brief against the 8-check rubric in
`intel/evals/brief_rubric.md` (BRF-015) and log the per-check
result, with the brief id, in `intel/evals/log.md`
(BRF-016/017/018). An 8/8 score on a template brief is a pass
for the template brief only; a Spark-composed brief is scored
separately when real transport lands, and the re-scores owed
on Buffy's fixtures (busy, quiet, stall) are still owed until
those fixtures land in this repo.

### Brief limitations — DOC-013 (Hana)

Stated plainly, so nobody reads a brief as knowing more than
it does. A brief is only as complete as the snapshot it was
built from, and it must say what window it covers rather than
imply more history.

- Window caps: a brief covers the last 500 messages or the
  last 24 hours, whichever is smaller (BRF-023). An ad hoc
  `--since` window narrows that cap; it never extends it.
  Anything older than the cap is simply not in the brief.
- Trimmed history: when the store window starts mid-story,
  the brief opens with the window it actually covers
  (BRF-013). A brief that starts mid-story is not evidence
  about what happened before that window.
- No DM visibility by default: DM rooms are not polled, and
  a brief sees only the rooms in its snapshot. Decisions,
  jobs, or blockers discussed in a DM room, or in a room
  that was not polled, do not appear in the brief, and the
  absence of a topic from a brief is not proof it did not
  happen elsewhere.
- Template fallback: when no composing client is passed, or
  the composing call fails, the brief is a template brief
  built from the extractors alone, marked `TEMPLATE`
  (BRF-008). It has no rewrite pass, so long job titles can
  push a morning brief over its 220-word budget (BRF-017
  log). A template brief is a real brief, not a placeholder
  — but it is not a Spark-composed brief.
- No Spark-composed brief has been produced: real Spark
  transport is the hard blocker, and the Spark pass over
  decisions named in BRF-004 is not implemented. Every eval
  log entry scored so far is a template-brief score only;
  a Spark-composed brief is scored separately when real
  transport lands, and the re-scores owed on Buffy's
  fixtures (busy, quiet, stall) are still owed until those
  fixtures land in this repo.
- Staleness: a brief older than 2 hours renders with its
  age (BRF-020). Never present a stale brief as current;
  check `age_seconds` before quoting one.
- Redaction changes verbatim quotes: a credential-shaped
  string in a blocked reason or message is replaced with
  `[redacted]` before storing or posting (BRF-014). A
  redacted brief therefore quotes the reason except for the
  redacted string — that is deliberate, not a silent edit.
- Empty room is not evidence: a room with no history yields
  a short brief saying there is no activity yet (BRF-012).
  That says nothing about other rooms, DMs, or earlier
  windows.
- On-join is an offer, not a brief: a present nick with no
  prior message gets an offer record only (BRF-029). No
  brief is generated for that nick until it is invoked.
- Watch items are references only: the brief names open
  watchdog alert ids with a one-line summary each
  (BRF-022). It does not reproduce the full alert, and a
  brief with no watch items means no open alerts were in
  its snapshot, not that the watchdog is silent everywhere.
- Brief announcements to a room (BRF-010) are held: no brief
  is posted until Dale rules on the room and the wire format.
  Until then a brief lives in the store and the CLI only.

## The two pushes — OS-097 (Hana)

A job's close fires at most one push, and a job's park fires
at most one push. There is no third push type. The builders
live in `intel/push.py` (pure functions: no network, no
Redis, no Spark, no bus post, no secret) and shape the
payload only — they do not send it.

- done: the overseer closed a job on passed acceptance
  checks. Body: "All done: \<title\>." plus what was built
  (the artifact record's files) and what was verified (the
  passed check names). Gate: job status "done" AND the
  overseer verified stamp (`verified` = "1", set by
  `mos/overseer.py verify_done`) AND a verification whose
  every check passed. A job closed without passing its
  checks gets no done push — a failed check, a missing
  stamp, or a missing verification each yields nothing.
  With no artifacts recorded the body says so instead of
  naming a file; with no checks recorded it says no
  acceptance criteria were recorded instead of claiming a
  check passed.
- blocked: a parked job. Body: "\<title\> is blocked.
  Question: \<question\>." Gate: job status "blocked" and
  a question — the caller's question when one is given,
  else the job's stored note (`jobs.py blocked`). With
  neither, there is no push: a push with no question would
  have to invent one. The question is quoted verbatim,
  never paraphrased away (the BRF-005 verbatim rule).
- Exactly one: `PushLedger` remembers (job id, push type)
  pairs already emitted; `decide_push` with a ledger
  returns nothing for a repeat, so a second close or a
  second park for the same job cannot ring twice.
- No third type: `build_push` raises ValueError for any
  kind outside ("done", "blocked"), and `validate_push`
  rejects any push of another type.

Not proven here, stated plainly: the firing call sites are
not wired. The done push must be fired from a real
overseer close (`mos/overseer.py verify_done`) and the
blocked push from a real escalation-gate park (Milo
OS-096, still open — the gate also decides whether a park
is genuinely Dale's decision, which no job record alone
can tell). The Web Push sender (`muse-relay-push`, outside
this repo) is not driven by this module, so nothing built
here can ring a phone on its own. A live ring — one push
from a real close, one from a real park, none from a close
that failed its checks — is still owed, and belongs to the
OS-099 completion drill, not to this builder task.

## Dispatch - DSP-020 (Pax)

How to turn one plain-English goal into posted jobs, from this
file alone. A cold reader needs nothing else: every command
below runs from the repo root, every function named below is
in `intel/dispatch.py`, and the test in
`tests/test_intel_dispatch_readme.py` pins this section to
the code, so the section and the code cannot drift apart
silently. If a command below stops working, the test fails
first.

### Ground rule

Dispatch never auto-posts. A plan reaches the queue only
after a human approves it (DSP-007), and the approver sees
exactly the plan the gates passed, never a re-parsed
variant. Dispatch code itself posts no bus message: the
only lines that reach the bus from a dispatch are the
`JOB:` lines `jobs.py` itself writes when it posts a job,
and the `DISPATCH:` announcement, which is DSP-010 and is
HELD under GOV-002 until Dale approves posting. Until then
a dispatch lives in the CLI and the store only.

### The pipeline, in order

1. Goal in, plain English. The prompt is DSP-001; the
   current version is v2 (DSP-024, Hana) in
   `intel/prompts/dispatch_v2.md`, with v1 kept beside it
   for diffing. A goal too vague triggers the DSP-021
   elicitation questions (scope, files hint, done
   definition) and posts nothing.
2. Spark returns one JSON plan, nothing else. The live
   goal to plan Spark step is library only today
   (`intel.dispatch.plan_from_spark`): real Spark
   transport is the GOV-001 hard blocker, so no
   Spark-generated plan has been posted, and the plan
   file under review in the commands below is the draft
   on disk, never a plan invented at posting time.
3. The plan passes every gate, in this order, through
   `validated_plan`: parse, overlap, contradiction, dep
   graph, budget clamp. The secret guard runs beside
   that pipeline: the CLI checks the plan text with
   `check_no_secrets` before validation, and library
   callers compose the same guard on the goal text
   before the Spark call and on the plan text after it.
4. Dry-run (DSP-006, `dry_run_plan`) prints the full
   validated plan and posts nothing. A dry-run that
   fails a gate prints the gate error and no partial
   plan.
5. Approval (DSP-007) through `request_approval`: the
   `--approve` flag, or an interactive `y`/`yes` answer
   on a real tty. Anything else is a denial, and a
   denied plan posts zero jobs.
6. Poster (DSP-008, `post_plan`) posts through `jobs.py
   main()` in the DSP-004 topological order, rewriting
   plan-local dep keys to the real job ids already
   posted, and stores one dispatch record. A job's `req`
   list (DSP-012) rides along as `jobs.py --req` and is
   stored on the posted job, so capability matching in
   `mos/capabilities.py` can find the job's workers. A
   failed post raises `PostError` naming the failed job;
   jobs already posted stay posted, and no record claims
   a full plan.
7. A posted plan is claimable by the unchanged mos
   worker loop (DSP-019, proved by
   `tests/test_intel_dispatch_worker.py`): the worker
   claims, works, and completes a dispatched job, and
   `mos/overseer.verify_done` verifies its acceptance
   lines. A dependent job waits until its dep is done.
8. After posting, `--show` (DSP-016, `show_dispatch`)
   reads the plan against live job states, and `--undo`
   (DSP-011, `undo_dispatch`) cancels what is still
   open. Both are in the commands below.

### Plan schema

One JSON object, produced by Spark, parsed by
`parse_plan` (DSP-002):

- `summary`: one plain-English paragraph in the DSP-025
  style: what will happen, in what order, who likely
  claims each job.
- `jobs`: a list of 1 to 12 jobs. Each job carries
  `key` (plan-local id, lowercase and dashes; deps refer
  to keys, never to real job ids, which do not exist
  yet), `title` (short, imperative, one line), `spec`
  (full working spec in the DSP-026 standard: Goal,
  Context, Files, Steps, Out of scope, in that order),
  `files` (every path the job owns, non-empty),
  `deps` (plan-local keys this job waits for),
  `max_attempts` (integer, clamped to 1..5, default 3),
  and `accept` (at least one machine-checkable line in
  the DSP-027 standard, in exactly the
  `mos/acceptance.py` formats: `file-exists:`,
  `tests-pass:`, `command-ok:`, `contains:`).

### Guards (each is a hard refusal, never a warning)

- Parse (DSP-002, `parse_plan`): shape only. Field
  presence, types, non-empty files per job, unique keys,
  no unknown fields, at least one parseable accept line
  per job via `mos/acceptance.parse_accept`. A malformed
  plan fails here with the broken field named.
- Secret guard (DSP-028, `check_no_secrets`): a
  credential-shaped string in the goal text or the plan
  text is refused with a secret warning naming the
  shape found, never the value itself. The prompt ban
  in `intel/prompts/dispatch.md` is the other half; this
  guard is the machine enforcement when Spark does not
  refuse.
- File overlap (DSP-003, `check_file_overlap`): two jobs
  owning the same path is a hard error, unless the
  overlap is shared-sequential: for every consecutive
  pair of owners of a path, the later job lists the
  earlier job in `deps` and its spec marks the path
  with the token `shared-sequential` plus the path
  itself, for example `shared-sequential:
  intel/ingest.py`.
- Contradiction guard (`check_no_contradiction`, run
  inside `validated_plan`): a plan that contradicts
  itself, for example creating and deleting the same
  file, is refused rather than posted.
- Dep graph (DSP-004, `check_dep_graph`): deps must
  name plan-local keys, the graph must be acyclic, and
  the returned posting order puts every job after all
  of its deps. A cycle error names the full cycle, for
  example `dependency cycle: a -> b -> a`.
- Attempt budgets (DSP-005, `clamp_attempt_budgets`):
  every `max_attempts` is clamped into 1..5, default 3,
  per-job overrides honored inside the range, and every
  clamp is reported in the plan summary.
- Size guardrail (DSP-013, `plan_size_warnings`): a
  plan over 12 jobs or over 40 distinct files prints
  its guard message in the dry-run, and posting it
  needs a second confirmation (the `--confirm-large`
  flag alongside `--approve`, or a second `y`/`yes`
  at the prompts). The suggestion is to split the plan
  into smaller plans inside the limits, each approved
  separately.
- Spec and accept scoring (DSP-026, DSP-027) are
  scorers, not parser gates, by design: `score_plan_specs`
  and `score_plan_accepts` check the five-part spec
  standard and the one-accept-line rule over a finished
  plan, and the golden goals below are scored against
  them. A plan that parses but scores badly is a prompt
  failure (DSP-024), not a posting success.

### Running it

From the repo root. The cold-reader dry-run uses the
demo goal plan, the hand-authored G5 draft in
`hackathon/demo_goal_plan.json` (DSP-015), not Spark
output:

```
python3 intel.py dispatch --goal 'Add a read-only snapshot endpoint to the intel package so the dashboard can show the current relay state without touching Redis writes.' --dry-run --plan hackathon/demo_goal_plan.json
```

That prints the full validated plan (titles, files,
deps, budgets, accept lines) and posts nothing; the
jobs list before and after is identical. A dry-run
without `--plan` is a usage error, not a silent empty
plan.

Posting, once a plan file has been reviewed and the
human approves it:

```
python3 intel.py dispatch --goal '...' --plan plan.json --approve
```

With `--secret-file <keyring>` every posted job is
signed with the crew keyring HMAC (DSP-009) and the
dispatch record carries `signed=True`; every posted
job then verifies OK via `jobs.py verify` against the
same keyring. Without a keyring and without
`--crew-mode`, the plan still posts, but a loud
WARNING goes to stderr and the record carries
`signed=False`. With `--crew-mode` and no keyring,
the poster refuses before posting anything: zero jobs
posted, no record stored. A large plan posted with
`--approve` also needs `--confirm-large`.

After posting, the dispatch record id is the handle
for both follow-ups. The record lives under
`muse-bus:intel:dispatch:<id>` via
`intel.store.put_dispatch`, and carries the summary,
the posting order, the key to real id mapping with
each job files, real deps, and budget, the
`signed` flag, and `latency_ms` (DSP-014; the same
latency goes to the FND-007 spend ledger with
`lane_feature` `dispatch`, no token counts and no cost,
because posting itself makes no Spark call):

```
python3 intel.py dispatch --show <dispatch id>
python3 intel.py dispatch --undo <dispatch id>
```

`--show` prints the plan as posted next to each job
current state (open, claimed, done, blocked,
cancelled, failed-final, or missing), with the claim
nick for claimed jobs, and a per-status count. It is
read-only: it never posts, claims, cancels, or writes
the record, and an unknown id exits 2 with nothing
touched. `--undo` cancels every still-open job from
the plan through `jobs.py cancel` (status
`cancelled`, never claimable again), leaves claimed
jobs untouched and reports them with their claim nick,
leaves done, blocked, failed-final, and already
cancelled jobs untouched, reports missing ids, and
stores the report on the dispatch record. A second
undo cancels nothing new. An unknown id exits 2 with
nothing touched.

### Spark failure fallback (DSP-017)

`plan_from_spark` asks its Spark completion callable
for a plan, twice at most: the first malformed JSON
answer gets one retry, and a second malformed answer
in a row yields `fallback_plan`, a single job carrying
the raw goal as its spec, marked FALLBACK in its
summary, title, and spec, with a loud stderr warning.
The fallback job deliberately carries no files and no
accept lines, because Spark supplied nothing usable
to derive them from, and inventing them would break
the no-invention rule. A structured plan that fails a
guard is refused on the first attempt, never retried
and never replaced by a fallback. A Spark transport
error (INT-008) returns the same fallback with an
endpoint-down warning instead of propagating: an
endpoint that answers nothing is not a structured-plan
fault. The fallback still needs
DSP-007 approval before it can post, so the FALLBACK
marking is what the approver sees first. Nothing
malformed is ever posted.

### Templates, golden goals, and the dashboard

- Templates (DSP-018): `intel/prompts/dispatch.md`
  carries prompt hints, not hard code, for four
  recurring shapes: add-endpoint, fix-bug, write-tests,
  docs-pass. A hint never overrides a guard, and the
  parser has no template check.
- Golden goals (DSP-022, Hana) and adversarial goals
  (DSP-023, Hana) live in
  `intel/evals/dispatch_golden.md` and
  `intel/evals/dispatch_adversarial.md`. Each golden
  goal dry-runs to a plan inside its expected shape
  (job-count range, must-own files, must-have deps);
  each adversarial goal triggers its documented guard
  and posts nothing. Both files are hand-authored, not
  Spark output, and both are checked by
  `tests/test_intel_dispatch.py`, so a plan and its
  stated shape cannot drift apart silently. The
  DSP-024 v2 prompt exists because golden and
  adversarial failures demanded it; the eval log ties
  each v2 change to the failing case it fixed.
- Malformed plan pack, overlap scenario pack, and
  dispatch batch runner (DSP-030, DSP-033, DSP-032,
  Buffy) exercise the parser and the guards without a
  Spark call. Demo goal alternates (DSP-034) are the
  backup goals if the primary demo goal plan
  destabilizes.
- Dashboard (DSP-037 to DSP-040, Rowan): the dispatch
  box payload is goal in, plan preview out (jobs,
  files, deps graph summary, budgets), with the approve
  action shape and six states (idle, planning,
  plan-ready, posting, posted, rejected) specified in
  `docs/DASHBOARD_SPEC.md` section 5. The box never
  implies auto-posting: its copy states a human
  approves every plan, and the dependency order
  renders as an indented list, no graph library.

### Open gaps, stated plainly

- Capability matching (DSP-012) is wired at the job
  level: a plan job may carry a `req` list, the poster
  passes it as `jobs.py --req`, and the posted job stores
  it for `mos/capabilities.find_for`. What DSP-012 does
  not do is DM capable workers on posting: that stays
  with `mos/overseer.dispatch`, which the poster does
  not route through, so no DM is sent by a dispatch
  post. The `req` value itself is only what the plan
  names; the parser never invents a capability.
- Announcements (DSP-010) are built, not posted, as the
  ground rule above says: the `DISPATCH:<id> -> <n> jobs`
  line shape is frozen in the FND-020 section above,
  `intel.dispatch.format_dispatch_announcement` builds
  that line from a stored dispatch record, and
  `intel.py dispatch --announce` prints it after a post.
  No line is pushed to the bus until Dale approves
  posting under GOV-002, and without `--announce` the
  CLI prints no line at all.
- No Spark-generated plan has been scored against the
  golden shapes yet, for the GOV-001 reason above.
  When real transport lands, the re-run is: send each
  golden goal to Spark, dry-run the returned plan,
  and check it against the same range, files, and
  edges. A Spark plan that dry-runs clean but falls
  outside its shape is a DSP-024 prompt failure, not
  a pass.
- The demo goal script (`hackathon/demo_goal.py`,
  DSP-015) proves the deterministic dry-run pipeline
  stable across 5 runs (same job count, same file
  ownership, same posting order), not a live Spark
  call stable. Its report says so, in
  `hackathon/demo_goal_stability.md`.


## Mind image bundle format: OS-101 (Pax, 2026-10-28)

A mind image bundle is one JSON manifest plus the files it names,
all inside one bundle directory. `intel/mind_image.py` parses and
resolves it: `parse_bundle()` checks the shape strictly (unknown
fields refused, version like "1" or "1.2", brief as a file or the
`generated-at-launch` slot), and `resolve_bundle()` proves every
layer resolves to a real source inside the bundle (constitution
file, skill folders, memory mount folders, capability grant file
with identity plus actions, tool grants against a supplied gateway
catalog, brief file, changelog file). Absolute paths, bundle
escapes, and secret named layer files are refused, because secrets
never enter an image. With no gateway catalog supplied, tool grants
report unresolved instead of claiming resolution.

The example bundle `intel/examples/mind-images/pax-default/` (v1)
resolves fully against its own declared catalog in
gateway-catalog.json. That catalog is example content only: the
OS-058/059 gateway bake replaces it with a live catalog when it
lands.

## Skills loader: OS-065 (Pax, 2026-10-28)

`intel/skills_loader.py` mounts skills-2 style skill folders
into an agent process's launch environment, the way an OS loads
apps for a user session: a process started from a mounted launch
directory begins with its skills already present. A collection
is a directory whose immediate subdirectories are skill apps; a
folder mounts only when it carries a SKILL.md at its root.
`list_skills()` reports mountable skills only, `mount_skills()`
copies the named skills verbatim into launch_dir/skills/ and
writes skills.json with every mounted file's sha256, and
`verify_mount()` proves a mount still matches its manifest and
that no unlisted directory sits under skills/. Names must be
plain basenames and unique, symlinks escaping their skill folder
are refused, and mounting over an existing mount is refused, so
a refusal never leaves a partial mount behind. A cold reader
mounts a fixture skill with one command, no bundle needed:

```
python3 intel/skills_loader.py list intel/examples/skills
python3 intel/skills_loader.py mount intel/examples/skills \
    fixture-ledger --into /tmp/launch
python3 intel/skills_loader.py verify /tmp/launch
```

The fixture collection `intel/examples/skills/` carries two
mountable skills (fixture-ledger, fixture-brief) and one folder
without a SKILL.md (not-a-skill) that listing skips and mounting
refuses. The OS-102 mind loader mounts its bundle skills
through this same module, so the bundle path and the collection
path share one rule instead of two. All three image routes bake
the conventional collection root /var/lib/metaos/skills empty
plus a .metaos-skills-root marker, relay-owned; no skill content
is baked, population by an install step is owed. 21 pinning
tests in tests/test_os065_skills_loader.py. Still owed: a driver
process showing a mounted skill active in its first action with
an unmounted control run beside it (OS-055 integration proof),
a real collection installed at the image root, and a process
actually started from a mounted launch directory.

## Mind image loader: OS-102 (Pax, 2026-10-28)

`intel/mind_loader.py` assembles a resolved bundle into a launch
environment directory, and that assembly IS the OS-065 skills
loader extended to the full image: skills are one layer, mounted
through intel/skills_loader.py only when the skill folder
carries a SKILL.md (a folder without one is refused, never
silently skipped), with mount-name collisions refused and bundle
folders not named in the manifest never mounted. Worker and driver launches go through the
identical assembly; only the manifest's process_kind differs, so
a worker and a driver from one bundle carry identical layers.
Constitution, grant, and changelog are copied verbatim and
hash-pinned in launch.json; memory mounts are symlinks to the
bundle's resolved mount points (bundle mounts, not an OS-078
service mount yet); tool grants are written as a JSON list; a
file brief is copied verbatim while a `generated-at-launch`
slot brief leaves only a brief.pending marker, never a
fabricated brief. `verify_launch()` re-checks a launch against
its bundle and names any changed layer. 17 pinning tests in
tests/test_intel_mind_loader.py. Follow-up (OS-102, Pax):
`intel/launch_run.py` starts a real child process from an
assembled launch directory, and only after the launch verifies:
a tampered layer refuses the run and spawns nothing, the child
runs with cwd set to the launch directory and
METAOS_LAUNCH_DIR naming it, stdout and stderr return with
the exit code, and a timeout kills the child. 11 pinning tests
in tests/test_os102_launch_run.py prove the mounted skill
visible in the probe's first action with a control launch
silent on the skill it never mounted. Still owed: the OS-078
memory service behind the mount points, a Muse Code driver run
from a launch (OS-055), and a launch against a live gateway
catalog or on a booted test image.

## meta join: OS-110 (Pax, 2026-10-28)

`intel/join.py` is the join flow: one command joins a Meta OS
machine to a room. It writes three chmod-600 files into the
config dir (default /etc/metaos on the image): room.env (room
address + machine name), room.key (the room key alone), and
trust.json ({"trusted_kids": [...]}, empty by default, which is
the default-closed posture: a fresh machine trusts no foreign
crew until its owner adds one with --trust). Existing files are
refused unless --force is given, so a second join never silently
overwrites a machine's room. The announcement it builds names
the machine, the crew nicks from the OS-080 capability files,
each agent's mind-image version (or "unrecorded" when none is
recorded, never an invented version), and each badge. Address,
key, and machine resolve from flags or from firstboot's files
(secrets.env, token, machine), so on the image the join is
`python3 intel/join.py --post`; without --post it writes the
config, prints the announcement, and posts nothing. The module
itself never touches the network: posting goes through a
caller-supplied poster (or, in the CLI, relay_common's bus path),
and the key is asserted absent from the announcement, the env
file, and the trust file. 17 pinning tests in
tests/test_intel_join.py. Still owed: a fresh test image joining
a fixture room with the command alone, the announcement read
back from a live room, claiming per the trust list on a booted
image, and the OS-115 demo-room posture ruling from Dale.

## Watchdog clock: WDG-026 (Milo)

Every age the watchdog reports (stall age, lease time left,
silence age) is computed from one resolved "now" per tick,
never from a mix of clocks. `intel/watchdog.py`
`resolve_tick_now()` fixes the precedence:

1. An explicit `now` argument to `tick()` wins. This is
   the injected clock tests use, and a live caller's
   deliberate override. A test that injects a clock can
   never be silently overridden by a timestamp stamped
   on its fixture.
2. Else the snapshot's `server_time` field, when it
   carries a usable Redis server timestamp: an int
   epoch, a numeric string, or Redis TIME's literal
   `[seconds, microseconds]` pair. This is "Redis server
   time where available."
3. Else the local wall clock.

Detectors never call `time.time()` themselves; they take
the tick's resolved now. So a skewed local clock shifts
every age in a tick together but can never make one
detector's age come from one clock and another's from a
different one.

Documented assumption, stated plainly: when a snapshot
carries no `server_time`, the watchdog assumes the local
wall clock is close to the Redis server clock. Job
timestamps and the server clock are both Redis-side
epochs, so ages are meaningful when that assumption
holds and drift by exactly the skew when it does not.
The live snapshot producer (`intel/ingest.py`,
FND-014) does not yet stamp `server_time` (it has no
Redis TIME read today), so a live tick currently runs
on the wall-clock fallback. File snapshots handed to
`--once` may carry `server_time` by hand, and the full
watchdog section of this README (WDG-029) will pin the
live stamping rule when FND-014 lands. Until then, no
claim is made that a live tick runs on server time.

## Watchdog: WDG-029 (Milo)

The watchdog watches crew work for silent failure: a worker
that dies mid-job, a job stuck behind a blocked dependency,
two workers about to overwrite each other's files. It
alerts only. It never touches job state, never requeues a
job, never claims or unclaims anything - the jobs.py sweep
owns requeueing, and the watchdog proves that separately in
its drills. It also never posts to the bus itself: critical
alerts produce a held announcement line, and the caller
posts it only under Dale's posting rule (WDG-015).

### Running it

One tick over a snapshot file, exit 0 on a clean run:

    python3 intel/watchdog.py --once [--snapshot <file>]

With no snapshot file it ticks an empty snapshot and
reports zero alerts. `--loop` repeats the tick every
`--interval` seconds (default 60) until interrupted;
`--max-ticks` caps a loop run. `--room` names the room
(default `main`); `--announce` hands critical lines to the
announcement callback instead of holding them. A tick
never raises on a bad detector: a crashing detector is
skipped so one broken detector cannot blind the rest.

Programmatic use: `intel.watchdog.tick(snapshot, now=...)`
returns the alert list in detector order. `snapshot` is a
plain dict in the shape `intel/brief.py` documents
(messages, jobs, presence, caps, alerts); missing sections
read as empty, never invented. `now` is an injected Unix
timestamp for tests; a live caller omits it and the tick
resolves the clock per the WDG-026 section above.

### Detectors, in tick order

Every detector yields at most one alert per (subject) pair
per tick, and every alert carries a filled plain-English
explanation plus a suggested fix from `intel/explanations.py`
(WDG-011). Severity follows the WDG-024 mapping, locked by
`SEVERITY_BY_KIND` in `intel/watchdog.py`:

| Detector | Alert kind | Severity | Fires when |
|---|---|---|---|
| Presence stall (WDG-002) | presence-stall | critical | Nick in the caps registry, absent from presence, holding a claimed job with no activity longer than STALL_MINUTES |
| Progress stall (WDG-003) | progress-stall | critical | Nick present (heartbeat alive) but its claimed job has no progress longer than PROGRESS_STALL_MINUTES - the worker lives, the work does not move |
| Lease risk (WDG-004) | lease-risk | warning | Claimed job's lease expires within LEASE_RISK_WINDOW_MINUTES and no heartbeat in the last LEASE_RISK_QUIET_MINUTES - the warning before the sweep requeues it, after which the alert auto-resolves |
| Dead dependency (WDG-005) | dead-dep | critical | Open or claimed job whose dependency is blocked longer than threshold, or failed-final; the alert names both job ids and the blocking reason verbatim |
| Missing dependency (WDG-006) | missing-dep | critical | Posted job whose dependency id does not exist in the job index - a bad post caught early, not a job left sitting |
| File collision (WDG-007) | file-collision | critical | Two claimed jobs with overlapping files fields, or a claimed job overlapping a done-but-unmerged branch's files; names the shared path and both jobs |
| Attempt exhaustion (WDG-008) | attempt-warning / attempt-exhaustion | warning / critical | Job at max_attempts-1 requeueing gets the heads-up warning; at max attempts the failed-final alert is critical |
| Silent room (WDG-009) | silent-room | info | Build room with claimed jobs but zero messages longer than SILENT_ROOM_MINUTES during work hours; an INFO record only, never an alert |
| Refused dispatch (INT-010) | rejected-dispatch | critical | A worker's REJECTED line (BAD or EXPIRED signature) for a job in the snapshot window; one alert per job and verdict, naming the poster and the refuser |
| Journal watch (OS-037) | system-failure | critical | A relay unit's failure in journald (systemd failure message, or err-or-worse priority); one SYSTEM alert per unit, subjects the unit name, no nick or job - a unit failure, not a worker stall |
| Budget warning (OS-085) | budget-warning | warning | A lane that has spent past the warning threshold of its cap (default 80%, intel/budgets.py); names the lane, spent, and cap - the warning before the cap, after which new claims are held and the hold shows in the brief's budget line |

Two non-detector behaviours ride along. Journal watch
(OS-037) is the third: it is not a snapshot detector, so its
critical severity is locked by its own tests and this table
row, not by SEVERITY_BY_KIND (whose test lock covers exactly
the snapshot detectors' kinds). Walk-on tracking
(WDG-025): a job claimed by a nick never in the caps
registry is tracked from jobs data alone - a tracking
record, never an alert, and WDG-002/WDG-003 skip it
honestly instead of crashing. Tick budget guard (WDG-017):
messages are walked page by page and the tick window
keeps only the newest TICK_MAX_MESSAGES; jobs are never
capped, because every detector needs full job visibility.

### Thresholds

All thresholds live in one shared module,
`intel/thresholds.py` (FND-030, WDG-018); the watchdog and
its tests import from there only, never hardcode minutes.
Every value is env-overridable through a `WATCHDOG_*`
variable named in the module's comments; a blank,
unparseable, or below-minimum variable falls back to the
default silently, so a typo in the environment can never
crash the watchdog or invent a threshold. Production
defaults: stall 10 minutes, progress stall 10 minutes,
lease-risk window 5 minutes with a 2-minute quiet window,
alert dedupe cooldown 30 minutes, silent room 60 minutes,
beat TTL 300 seconds, tick page 1000 messages with a
1000-message window. The demo thresholds profile
(DEM-013/OS-038) is the same code with shorter windows set
through the environment on the demo image only; the
production module is untouched. WDG-027 tuned these
defaults against every suite fixture (26 fixtures, zero
false positives, zero false negatives, quiet fixture zero
alerts); INT-022 locks them for the demo after the
integration fixtures grow.

### Alert records and lifecycle

An alert record (`intel/store.py`, WDG-010) carries: id,
kind, severity, room, subjects, explanation, suggested_fix,
created_at, resolved_at, dedupe_key. Records round-trip
through `store.write_alert` and are queried with
`store.query_alerts(room, since, kind)` (WDG-023), oldest
first. Dedupe (WDG-013): the same dedupe_key inside the
30-minute cooldown updates the open record's last_seen
instead of creating a new alert, so a stuck condition
yields one record that stays current, not an alert storm.
Lifecycle (WDG-014), in order: open -> acknowledged ->
resolved. Resolve is automatic when the condition clears
(the sweep requeues the job, the dep unblocks, the job
finishes) or manual. The CLI for all three steps:

    python3 intel.py alerts --show [--room R] [--since TS] [--kind K]
    python3 intel.py alerts --ack --id <id>
    python3 intel.py alerts --resolve --id <id>

### Announcements and the self-heartbeat

Only critical alerts announce, in the frozen format
`ALERT:<id> <kind>: <explanation>`, exactly one line
(WDG-015). Warnings accumulate silently for the brief and
dashboard; info records never announce. `tick()` takes an
optional `announce` callback and calls it once per
critical alert; with no callback it announces nothing and
the lines stay held. The watchdog's own heartbeat
(WDG-016): pass `intel.store.wd_self_beat` as tick's
`beat` callback and every tick renews the
`muse-bus:intel:wd:beat` key with a 300-second TTL, quiet
ticks included - a missing beat is itself the signal, and
the dashboard renders it as watchdog-silent. Optional
Spark polish (WDG-012): pass a client as tick's
`polish_client` and explanations are rewritten for
clarity; with no client the template text stands, and on
Spark failure or an empty answer the template is kept, so
a bad polish can never blank an alert. The suggested fix
is never polished.

### Self-repair ladder (OS-095)

On a stall the watchdog acts before it reports, in a
ladder: nudge, restart, reassign (`intel/ladder.py`).
Rung selection reads snapshot facts only: a registered
worker that is present but stale gets a nudge, a
registered worker absent from presence gets a restart,
and a claimer outside the caps registry gets a reassign
with a baton (title, deposited progress, files touched).
Every rung is journaled with its reason
(`ladder:<job>:<rung>` dedupe, so a second tick on the
same stall journals nothing new) and rendered as a brief
line (`Ladder: <rung> job <id> (<nick>): <reason>`).
Dale is contacted at no rung: the module has no push or
announcement path. The ladder never mutates a snapshot or
a claim, so it cannot fight systemd over a restart (that
half belongs to systemd under OS-034) or steal a live
worker's job (the reassign half belongs to the overseer
via the OS-125 baton pass). Drill:
`intel/drills/self_repair_ladder.py`. Attempt budgets and
the escalation gate are OS-096, next section, not this
ladder.

### Attempt budgets + the escalation gate (OS-096)

When every rung is spent, the loop stops
(`intel/gate.py`). A job whose attempt budget is spent
(attempts >= max_attempts) parks visibly, and a blocker
that is genuinely Dale's call (blocker_kind money,
permission, or direction) parks the same way, even with
attempts remaining. Each park yields a parked record and
an escalation record carrying the blocked-push payload
built by `intel/push.py` (the question quoted verbatim);
the gate builds the payload and never sends it, so no
phone can ring from the gate alone. Dedupe
(`park:<job>`) makes a second tick over a parked job
journal nothing new: no loop, no duplicate push. A
crew-fixable blocker, an unbudgeted job, and a malformed
budget all stay quiet. Brief lines: `Parked job <id>:
<reason>` and `Escalated job <id>: one blocked push
queued`. Drill: `intel/drills/attempt_gate.py`.

### Budget forecasting + preemption (OS-091)

The watchdog sees a breach coming hours ahead instead of
reporting it after the silence (`intel/forecast.py`). A
lane's end-of-day spend is projected from its ledger rate
(spent over elapsed hours, scaled to a 24-hour day), and
every forecast carries its basis in plain words - the
elapsed hours the rate comes from - plus a confidence word
from those hours alone (low under 4, medium 4 to under 12,
high at 12 or more). A lane with no usable ledger gets no
forecast, never a guessed number. The brief line is a plain
line, not a bullet, so the BRF-007 trim keeps it:
`Budget forecast for lane <lane>: <spent> spent of <cap>
cap, projected <n> by end of day, based on <h> hours of
ledger in a 24-hour day (<confidence> confidence) -
breach expected before end of day` (or `within cap`).
Preemption is pause, never kill: a running low-priority
job in a lane at the OS-085 warning threshold pauses with
its progress untouched, a high-priority job is never
touched, and a paused job resumes to running with its
progress exactly as it was once the lane drops back below
warning. The module judges caller-supplied figures only;
it reads no live ledger, pauses no live worker, and posts
nothing. Drill: `intel/drills/budget_forecast.py`.

### The baton pass (OS-125)

When the ladder reaches reassign, the job does not
restart from zero (`intel/baton.py`). `compose_baton(job)`
builds the continuation from the job record: goal (the
goal field, else the Goal line of the spec), deposited
progress notes (progress_notes list, else the latest
note), files already changed, files still to touch
(files minus completed, in order, so a completed file
never appears as remaining), what remains (the
remaining list, else steps minus completed steps), and
acceptance checks (acceptance_checks list, else the
accept string split on lines). The prompt names what
remains instead of restating the whole job, and a job
with nothing deposited says so plainly rather than
claiming work done. The module composes only: it never
moves a claim, has no push path, and never contacts
Dale. `baton_pass_tick` journals one baton-pass record
(dedupe `baton:<job>`, so a second pass journals
nothing new); the overseer moves the claim from that
record, worked mechanically by the watchman (Pax
OS-118). Brief line: `Baton passed job <id> from <old>
to <new>: <n> file(s) still to touch`. Drill:
`intel/drills/baton_pass.py`. In-window proof is
same-program; the cross-program pass (Muse to Freebuff)
is the named stretch line, not claimed here.

### Watchman state after reboot (OS-129)

At boot the watchman rebuilds its picture purely from
queue claims and leases (`intel/watchman_boot.py`), and
this module is the verification half of that claim.
`post_boot_rings(jobs, down_since, boot_at, rung_ledger)`
returns the first post-boot ring set: open jobs posted
inside the downtime window ring as
arrived_during_downtime, claimed jobs whose leases died
inside the window ring as lease_expired_during_downtime,
and nothing else rings (pre-window open jobs were
already visible, live leases may still have a live
worker, done jobs never ring, malformed records never
ring and never crash). Each job id rings at most once
per cycle, and a job id already in the rung ledger never
rings again. No function takes a counter argument and
none reads one, so a corrupted stored counter value
changes nothing: the stale-counter drift failure mode is
designed out, not patched. `verify_boot_cycle` checks
the ring set against the lease sweep record and reports
reconciled True only when the lease-expired ring ids
equal the sweep's requeued ids, naming any missing or
extra ids instead of fudging a count; `boot_brief_lines`
renders the note for the next brief. The module rings no
bell and moves no claim, and it has no push path, so
verification alone can never contact Dale. Drill:
`intel/drills/watchman_boot.py` (15 PASS). The
mechanical half (the resident watchman that actually
rings) is Pax OS-118, and a live boot on a booted test
image is not claimed here: no test image runs in this
repo. Milo's verification note is
`intel/evals/watchman_boot.md`, filed separately from
Buffy's OS-126 run log.

### Timer fallback sweep (OS-121)

Every agent runtime also wakes on a slow timer to sweep
the board and claim anything the bell missed, so a
missed wake delays work by minutes, never forever.
`intel/timer_sweep.py` computes one sweep tick from
fixture queue state: while the watchman is healthy the
tick runs but claims nothing, because the bell owns
claiming while it lives and a sweep that also claimed
would double claim; when the watchman is dead the sweep
claims open jobs addressed to the local roster, and a
job posted at time t is claimed by the first tick at or
after t, so with ticks every
`TIMER_SWEEP_INTERVAL_SECONDS` (thresholds, default
300) every claim lands within one interval of posting.
When watchman state is unknown the sweep holds and
claims nothing, because missing evidence is never read
as a dead watchman. Lease discipline holds across both
paths: claimed and done jobs are never re-claimed, and
a job id in the sweep ledger is never claimed again.
Outsider-addressed and unaddressed jobs are never
claimed and are reported in skipped, never silently
dropped: routing an unaddressed job would invent a
worker. A tick before last sweep plus interval does not
run, and inputs are never mutated. The module is
decision only: it never wakes an agent, rings a bell,
or posts to the bus, and it has no push path. Drill:
`intel/drills/timer_sweep.py` (20 PASS). The runtime
timer that actually wakes an agent is outside this
repo's fixture layer, and a live sweep on a booted test
image is not claimed here: no test image runs in this
repo.

### Seven-day soak journal review (OS-074 prep)

OS-074 asks for a seven-day soak reviewed end to end:
every silent failure in the log has an alert or a filed
bug, and zero unexplained gaps remain. The soak itself
is not run here: no booted Meta OS image runs in this
repo, so OS-074 stays OPEN and this is only the review
tool its acceptance will use. `intel/soak_review.py`
reviews a fixture journal: a failure is covered when
at least one alert or one filed bug names its id,
covers naming a failure that never appears are orphans
reported and never counted, duplicates still count as
one coverage, malformed entries are skipped and never
a crash, and a failure without a usable day 1 to 7
still counts and is listed undated. Days present and
days missing are reported separately from the verdict,
so a partial journal is visible as partial instead of
silently passing as a full week. The report carries no
push path. Drill: `intel/drills/soak_review.py`
(20 PASS). A real soak report is not claimed here: no
live watchdog journal was reviewed, the journals are
fixtures written for the drill.

### Who watches the watchman (OS-122)

A dead watchman is a first-class failure, not a job
alert: crew-dark means the machine's agents are asleep
and its jobs are invisible to them. `intel/watchman_watch.py`
judges fixture watchman records per machine: a flag of
False reads dead, a flag of True with a bell older than
`WATCHMAN_STALE_MINUTES` (thresholds, default 5) reads
dead, a fresh bell reads alive, and no flag and no bell
reads unknown and yields nothing, because missing
evidence is never claimed as a dead watchman.
`watchman_watch_tick` journals a crew-dark record and
a restart record for a dead machine with no open dark
episode; when the fixture restart cannot revive it,
the same tick adds the episode's one escalation, a
blocked-push payload built through `intel/push.py`
and never sent (sending belongs to the Web Push
worker, Hana OS-097). A revived machine yields a
recovered record on the next tick and no escalation
at any point. Dedupe is per dark episode, so a
machine that recovers and dies again re-alerts.
`current_states` publishes one state record per
machine for the board's machine groups, and
`board_lines` renders them, so a dark machine reads
watchman-dead while the darkness lasts.
`watchman_brief_lines` renders the journal records
for the next brief. Drill:
`intel/drills/watchman_watch.py` (6/6 phases PASS).
Eval: `intel/evals/watchman_watch.md`. Not proven
here: a live watchman killed and restarted by
systemd (the OS-034 contract half), the resident
watchman actually ringing (Pax OS-118), a phone
actually ringing (Hana OS-097), or Rowan's
dashboard rendering of the board lines.

Follow-up to Pax OS-118: `intel/watchman_bridge.py`
folds a real relay_watchman tick into a watchman_watch
record (tick proves alive, a wake event proves the bell,
the rung state file is never read as liveness, a tick
with no wake event keeps last_bell None and reads
UNKNOWN, not ALIVE). Eval:
`intel/evals/watchman_bridge.md`. Drill:
`intel/drills/watchman_bridge.py` (4/4 PASS).

Service-loop entry point: `watchman_tick(
events_by_machine, now, priors, journal, restart_ok)`
folds every machine's events and judges them in one
call, returning (records, new_journal). A machine
missing from the mapping is not judged at all; a
machine that stops reporting must be folded explicitly
with an empty event list and its prior record, so its
bell ages honestly into crew-dark. `restart_ok` is
always a caller-supplied fact; a dark machine with no
restart fact supplied escalates once, fail closed
toward Dale, rather than assuming a restart the caller
never ran. Drill:
`intel/drills/watchman_bridge_tick.py` (5/5 PASS).
Eval: `intel/evals/watchman_bridge_tick.md`. Not
proven here: the production loop that will call
watchman_tick() does not exist yet in this repo, and
the live queue reader OS-118 still owes is the
interface it will read from.

Service-loop caller and runner (OS-122 follow-ups):
`intel/watchman_loop.py` `loop_cycle()` takes one
cycle's runs as {machine: (ok, stdout)} pairs, folds
successful runs through watchman_tick(), and carries
a failed run's prior record forward with restart_ok
stripped so its bell ages honestly into crew-dark,
while a machine with no prior stays unjudged and the
failure lives only in diagnostics. Drill:
`intel/drills/watchman_loop.py` (5/5 PASS). Eval:
`intel/evals/watchman_loop.md`.
`intel/watchman_cycle.py` `run_cycle()` collects those
runs from a caller-supplied runner, containing a
raising runner (exception type in diagnostics
runner_errors) and a garbage return (bad-return; only
exactly True counts, truthy 1 fails), and never
mutating its inputs. Drill:
`intel/drills/watchman_cycle.py` (6 phases PASS).
Eval: `intel/evals/watchman_cycle.md`.
`intel/watchman_runner.py` supplies the real runner
those adapters were waiting for: it runs Pax OS-118
`os/watchman/relay_watchman.py --once` once per
machine against per-machine snapshot files under a
snapshot directory (production default /run/metaos),
and `run_cycle_with_subprocess()` wires it straight
into run_cycle() with no judgment changed. Only exit
0 counts as success and a failed run's stdout is
discarded even when partial; a timeout (default 30s)
kills the run; a missing program, bad argv, bad
machine, or raising command_for yields a failed run,
never a raise; a missing snapshot file is a quiet
success per OS-118 (empty snapshot, no bell
invented), while a malformed file exits 2 and fails
the run. The runner runs the CLI locally and invents
no network transport to machines whose snapshots are
not on this host. Drill:
`intel/drills/watchman_runner.py` (6/6 phases PASS).
Eval: `intel/evals/watchman_runner.md`. Not proven
here: a live watchman on a booted test image, the
running service, a systemd restart, or the live queue
reader OS-118 still owes.

The repeating production loop (OS-122 follow-up):
`intel/watchman_service.py` `serve_cycles()` runs those
cycles again and again: each cycle's records become the
next cycle's priors and each cycle's new journal entries
accumulate, so episode dedupe holds across cycles; by
default the cycle function is `run_cycle_with_subprocess()`
against the snapshot directory, so the production loop
runs the real program once per machine per cycle with no
judgment changed. A cycle function that raises yields a
cycle_error diagnostic with priors carried, never a crash;
a raising callback or stop predicate is contained the
same way, and sleep happens between cycles only. The
`__main__` entry point is the command a unit would exec:
`python3 intel/watchman_service.py --machines alpha,beta`.
Drill: `intel/drills/watchman_service.py` (7 phases PASS).
Eval: `intel/evals/watchman_service.md`. Not proven here:
a live watchman on a booted test image, the running
service as a systemd unit, a systemd restart,
or the live queue reader OS-118 still owes.

The watchman watcher as a systemd unit (OS-122 follow-up):
`os/services/relay-watchman-watch.service` runs that
`__main__` entry point as the relay user, ordered after
relay-watchman.service, Restart=on-failure per the OS-034
contract (systemd owns the watcher process dying; the
crew-dark judgment stays with the loop). The machine list
comes from WATCHMAN_WATCH_MACHINES in
/etc/metaos/watchman-watch.env because no machine-naming
convention exists in this repo yet; with no list the loop
cycles empty and judges nothing, which the unit header
calls a configuration gap, not a passing watch. Tests:
`tests/test_intel_watchman_service_unit.py`. Eval:
`intel/evals/watchman_service_unit.md`. Not proven here:
service active at boot (the unit is not wired into
relay.target wants or any image enablement list yet;
that wiring is Pax's OS-101 integration), a systemd
restart on the test image, a live watchman on a booted
test image, or the live queue reader OS-118 still owes.

The unit command actually runs (OS-122 follow-up): the
`__main__` entry point above had never run as a process,
and running it failed at import time, because Python
puts the script's own directory (intel/) first on
sys.path, not the repo root, so "from intel import ..."
raised ModuleNotFoundError no matter what
WorkingDirectory the unit carried; the unit would have
died at startup. `intel/watchman_service.py` now
bootstraps its own package path (repo root, /opt/relay
on the image) with no PYTHONPATH set, the same
bootstrap the intel/* script entry points already use.
Drill: `intel/drills/watchman_service_cli.py` (5 phases
PASS: plain command, empty machine list, the unit's own
ExecStart line with paths substituted, bad flag exits 2,
and the no-env-file shape: a bare --machines, what the
ExecStart becomes when systemd expands an unset
${WATCHMAN_WATCH_MACHINES} to nothing, cycles empty
instead of failing argparse with exit 2 and
restart-looping under Restart=on-failure; --machines
takes nargs="?" with const="" for exactly that shape).
Tests: `tests/test_intel_watchman_service_cli.py`. Eval:
`intel/evals/watchman_service_cli.md`. Not proven here:
a booted service, a systemd restart, or the live queue
reader OS-118 still owes; the command the unit execs
is proven, the service itself is not.

### Morning-brief status line

`store.build_watchdog_status(records)` (WDG-028) renders
one frozen line for the morning brief: unresolved counts
by severity plus the top alert. The template brief prints
it at the head of Watch items, but only when the snapshot
alerts carry severities - severity-less snapshots keep
their exact existing shape. INT-020 wires the same ids
and severities into the brief and the dashboard so all
three surfaces agree.

### Boot-screen status line

`store.build_boot_status(units, workers, alerts)` (OS-041)
renders one frozen line for Rowan's boot checklist
(OS-043): units up, workers alive, latest open alert (a
healthy boot reads "Boot: 3/3 units up, 2 workers alive"
with a "no open alerts" tail).
It is live health, not the brief line above: "last alert"
means latest created, where WDG-028's top alert means
highest severity. The record lives at
`muse-bus:intel:wd:bootstatus:<room>:<ts>`; freshness is
`boot_status_is_stale()` at 30s, so a killed unit can hide
behind an old green line for at most 30 seconds. Drill:
`intel/drills/boot_status.py`.

### Drills: the cold-reader runbook

Each drill runs unattended on fixtures - no network, no
Redis, no bus posts - and exits 0 with a PASS line per
phase, 1 on failure. This is the exact sequence a cold
reader runs to prove the watchdog works:

    python3 intel/drills/kill_worker.py   # WDG-020
    python3 intel/drills/collision.py     # WDG-021
    python3 intel/drills/dead_dep.py      # WDG-022

INT-021 runs all three back to back in one timed session
and writes the combined log (total under 360s required):

    python3 intel/drills/tournament.py   # INT-021

Kill-a-worker: a fake worker claims a job, posts one
progress note, keeps heartbeating, then dies mid-job.
The watchdog must raise exactly one presence-stall alert
naming the nick, the job, and the last-progress age, with
its announcement line held, not posted. While the lease
is unexpired the job stays claimed (no early requeue);
once the lease expires the sweep rule requeues it and a
re-tick yields zero alerts, the job open for the next
worker. Collision: two fake workers claim
overlapping-files jobs; the collision alert fires before
either finishes and keeps firing with the same dedupe
key while both stay claimed, then stops when one job
finishes. Dead-dep: post A and B (B depends on A), block
A with a reason, age the clock; the watchdog raises
exactly one critical dead-dep alert naming both jobs
and A's reason verbatim, keeps firing while A stays
blocked, and stops when A unblocks. The combined
tournament (INT-021) runs all three back to back as the
demo will do, timed, under 6 minutes wall time.

### What is not claimed here

The live snapshot producer (`intel/ingest.py`, FND-014)
does not yet stamp `server_time`, so a live tick runs on
the wall-clock fallback until FND-014 lands - see the
WDG-026 section above. The watchdog state keys (`muse-bus:intel:wd:<nick>`, hash
fields last_seen / last_progress / claimed_jobs) are FND-029:
the key name and fields come from Pax's Day 1 FND-004 commit
(f5fbb3d), and the alert dedupe key shapes are documented in
the intel/store.py docstring and pinned by
tests/test_intel_fnd029.py (one tick per detector family
yields exactly the documented key). No separate Pax sign-off
message exists; this is definition by shared code, not a
handshake, but both lanes reference the same names, which
is what the acceptance asks for. The demo thresholds profile
(DEM-013) and the systemd service (OS-033) are separate
tasks; nothing here claims they are landed.

## Status

FND-032 schema written 2026-10-26, Hana lane. Pax sign-off on
this schema is still owed (the task says "with Pax"); until Pax
confirms it, treat this schema as Hana's draft, not a freeze.
The dashboard payload freeze (BRF-039, Pax+Hana+Rowan) is also
still owed and must not be claimed from this file alone.

## Integration environment: INT-001 (Pax, 2026-10-27)

This section alone reproduces the integration environment. One
room, one job namespace, one capability namespace, all disjoint
from production and from the unit-test prefixes, so an integration
run can never read or clobber production state or test state:

- Room: `build-int`. Integration job announcements land on
  `muse-bus:room:build-int` (relay_common.bus_key), never on the
  main bus `muse-bus`.
- Job namespace: `muse-bus:int-job` (production default is
  `muse-bus:job`; the unit-test prefix is `muse-bus:tjob`).
- Capability namespace: `muse-bus:int-cap` (production default is
  `muse-bus:cap`; the unit-test prefix is `muse-bus:tcap`).
- Intel room for intel.py commands: `build-int`, via
  `MUSE_RELAY_INTEL_ROOM` (relay_common.intel_config).

Setup (paste this block, in this order, before running anything):

```
export MUSE_RELAY_JOBNS=muse-bus:int-job
export MUSE_RELAY_CAPNS=muse-bus:int-cap
export MUSE_RELAY_INTEL_ROOM=build-int
```

The block is generated by `intel/integration.py` (`env_for` /
`export_lines`); the test in `tests/test_intel_integration.py`
pins this section to that output, so the documented block and the
code cannot drift apart silently.

Import-order rule (load-bearing): jobs.py reads
`MUSE_RELAY_JOBNS` into `jobs.NS` at import time, and
mos/capabilities.py reads `MUSE_RELAY_CAPNS` into
`capabilities.CAPNS` at import time. Setting the variables after
those modules are imported does nothing to the prefixes already
read. Export first, then import or run. `intel/integration.py`
`apply_env` does the same thing inside a process, with the same
ordering requirement.

Verify (from a clean checkout, after the export block):

1. `python3 -m unittest discover -s tests -p "test_intel_integration.py"`
   passes: defaults, export block, import-order probe, namespace
   isolation, and this README pin.
2. Post one job with the integration environment active and read it
   back; then, with the variables unset, confirm the same job id
   reads back empty under the production default namespace. The
   isolation test does exactly this on the fake backend; on a live
   backend the same two reads prove the same separation.
3. Confirm the post announcement went to `muse-bus:room:build-int`
   and nothing went to `muse-bus`.

Rules: integration runs never post to the main bus, never use the
production namespaces, and never carry real credentials. These
values are key prefixes and a room name, not secrets, and no secret
belongs in this environment or in any fixture built on it.

Open gaps (not claimed here): a live-backend run of the verify
steps above (the suite proves them on the fake backend only).
The INT-002 scripted end-to-end loop has landed in this
environment; see the INT-002 section below. The INT-003
scripted end-to-end loop has landed in the same environment;
see the INT-003 section below.

## End-to-end test 1: INT-002 (Pax, 2026-10-27)

Script: `intel/e2e1.py`. Transcript: `intel/evals/e2e1.log`.
Tests: `tests/test_intel_e2e1.py`.

Run it (from the repo root):

```
python3 intel/e2e1.py
```

The loop, in order: dispatch dry-run of a hand-authored plan,
approval gate, post through the DSP-008 poster, worker claim /
progress / done of both jobs in posting order, then a boot brief
reporting both jobs done. The plan has two jobs: probe (writes the
e2e probe note) and report (records the result in the e2e log),
with report depending on probe, so the posting order is probe
then report and the report job carries the real probe job id as
its dep.

What it proves, and what it does not:

- Proved: the full loop from a validated plan onward, on the
  INT-001 integration namespace and build-int room, against the
  in-memory fake surface. The dry-run posts nothing, approval
  without a human denies, the poster stores one dispatch record
  with real job ids, the worker path moves both jobs open to
  done, and the boot brief reports "2 jobs completed" with both
  titles via the OS-051 previous-session digest.
- Not proved: the live goal to plan Spark call (GOV-001 leaves
  the live transport blocked; the plan here is hand-authored,
  and DSP-017 owns that seam), a live bus run, a live Redis
  backend (the suite proves the loop on the fake backend only),
  or the mos worker loop itself (DSP-019 proved that chain;
  this loop uses the jobs.py claim path the worker uses).

Rules carried over from INT-001: the loop never posts to the
main bus, never uses the production namespaces, and never
carries a real credential. The done markers in the loop carry
the label e2e1-no-real-commit, not a git commit hash, because
the fixture jobs produce no code.

## End-to-end test 2: INT-003 (Pax, 2026-10-27)

Script: `intel/e2e2.py`. Transcript: `intel/evals/e2e2.log`.
Tests: `tests/test_intel_e2e2.py`.

Run it (from the repo root):

```
python3 intel/e2e2.py
```

The loop, in order: one job posted, worker-a claims and
progresses it, worker-a dies (stops beating and renewing),
the watchdog raises exactly one presence-stall alert, the
real jobs.py sweep requeues the job, a re-tick yields zero
alerts (the alert auto-resolves), worker-b claims and
finishes the job, and a final tick stays quiet. The job is
a single stall note job with max_attempts 3; worker-a
registers caps and beats presence before claiming, so the
alert names a registered worker that went dark, not a
walk-on worker.

What it proves, and what it does not:

- Proved: the death to recovery chain on the real command
  path, against the in-memory fake surface and the INT-001
  integration namespace and build-int room. The alert fires
  on a real ingest snapshot (not a hand-built dict, which is
  what the WDG-020 kill drill already covers), the sweep
  command itself does the requeue (REQUEUED printed, job
  open, claim and lease cleared), and the second worker
  finishes the same job id the first worker died on.
- Proved along the way, and fixed in the same batch: the
  stall detectors used to read only hand-snapshot timestamp
  fields (last_progress, claimed_at), while real snapshot
  rows carry last_progress_at. intel/watchdog.py now accepts
  last_progress_at as an activity timestamp, and the loop
  plus tests/test_intel_e2e2.py pin that behavior. Without
  the fix, no stall alert could ever fire on a real
  snapshot.
- Not proved: a live bus run, a live Redis backend (the
  suite proves the loop on the fake backend only), a real
  wall-clock death (time passes on the fake clock only:
  the loop advances it past the 120s presence TTL and the
  1800s lease, and the fake lapses both by its own expiry
  rules), or the mos worker loop itself (DSP-019 proved
  that chain; this loop uses the jobs.py claim path the
  worker uses).
- Known gap, unchanged by this batch: snapshot rows carry
  no max_attempts, so the attempt-exhaustion detector
  cannot fire on a real snapshot either. That detector is
  pinned on hand snapshots today; wiring max_attempts
  through the list shape is a separate task, not smuggled
  into this one.

Rules carried over from INT-001: the loop never posts to the
main bus, never uses the production namespaces, and never
carries a real credential. The watchdog announcement line is
held, never posted: the loop asserts the room message list
never gains the ALERT line. The done marker carries the
label e2e2-no-real-commit, not a git commit hash, because
the fixture job produces no code.

## End-to-end test 3: INT-004 (Pax, 2026-10-27)

Script: `intel/e2e3.py`. Transcript: `intel/evals/e2e3.log`.
Tests: `tests/test_intel_e2e3.py`.

Run it (from the repo root):

```
python3 intel/e2e3.py
```

The loop, in order: two jobs posted (a release note job and
a stall note job), worker-b claims the release job and marks
it blocked with a reason, worker-a claims and progresses the
stall job, a healthy tick yields zero alerts, worker-a dies
(stops beating), a tick yields exactly one presence-stall
alert which is stored through the real store path and reads
back by id, a fresh nick with no prior message beats
presence and is offered an onjoin brief (offer only, no
brief yet), the generated onjoin brief names the blocked
job id and title in its Blocked section and the stored
alert id with its explanation in its Watch items section,
and the room message list is unchanged by the brief step
(no auto-post, no ALERT line).

What it proves, and what it does not:

- Proved: the on-join content path on the real command
  path, against the in-memory fake surface and the INT-001
  integration namespace and build-int room. The blocked
  job is blocked by a real jobs.py blocked command (claim
  released, BLOCKED announcement on the room list), the
  alert fires on a real ingest snapshot, the alert is a
  stored WDG-010 record the brief reads (not the raw
  detector dict), and the offer-before-generate order of
  BRF-029 is enforced: list_briefs is empty until the
  offer is invoked.
- Proved along the way, and fixed in the same batch:
  extract_watch_items used to read only a summary field,
  while stored WDG-010 records carry explanation instead,
  so a brief built from stored records named each alert id
  with nothing after it. The extractor now falls back to
  the explanation's first line, and generate_brief's stored
  record sections use the same extractor, so brief text
  and brief record agree. Without the fix, the on-join
  brief's Watch items line for the drill alert would have
  been an id followed by nothing.
- Not proved: a live bus run, a live Redis backend (the
  suite proves the loop on the fake backend only), a real
  wall-clock death (time passes on the fake clock only),
  or a Spark-composed onjoin brief (the brief here is a
  template brief: GOV-001 leaves live Spark transport
  blocked, so the template path is the honest path).
- Known gap, unchanged by this batch: snapshot rows carry
  no note field, so the brief's Blocked section names the
  blocked job's id and title but cannot quote its reason
  verbatim. The reason still reaches the brief one way:
  the BLOCKED announcement is a message marker, so the
  Decisions section carries it verbatim. Carrying note
  through the snapshot row shape is a separate task, not
  smuggled into this one.

Rules carried over from INT-001: the loop never posts to the
main bus, never uses the production namespaces, and never
carries a real credential. The watchdog announcement line is
held, never posted, and the brief step adds no room message
at all: the loop asserts the room message list is identical
before and after generating the brief.

## Load check: INT-006 (Pax, 2026-10-27)

Script: `intel/load_check.py`. Timings table:
`intel/evals/load.md`. Transcript: `intel/evals/load.log`.
Tests: `tests/test_intel_load.py`.

Run it (from the repo root):

```
python3 intel/load_check.py
```

The check, in order: 200 jobs posted by real jobs.py post
commands, 10 claimed and progressed by a real worker
(190 left open), the room list cleared and seeded with
2,000 plain messages, then three timed operations on the
same state: an ingest snapshot, a morning template brief,
and one watchdog tick. The snapshot must read 2,000
messages and 200 jobs, the brief must stay inside its
220-word morning budget, and the tick must yield zero
alerts, because every claimed job is healthy on a clock
that never advances.

What it proves, and what it does not:

- Proved: the read path at this scale on the in-memory
  fake surface, each operation inside its adopted 5
  second budget (15 seconds for the three together).
  Timings differ run to run; the table records the
  run's own numbers, and the tests re-assert the budgets
  on every suite run.
- Found, not assumed: the 2,000-message room is a
  beyond-cap stress state, not a live-reachable room.
  Every jobs announcement runs bus_trim, which keeps
  only the newest 500 messages, so the room list is
  seeded directly after the queue. A live room fed by
  announcements holds at most 500 messages, and the
  brief path caps to 500 anyway (BRF-023), which is why
  brief cost stays flat as the room grows.
- Close call, named: at 200 in-flight jobs the morning
  template brief lands at 218 words against a 220-word
  budget. The trim is doing real work at this scale; a
  longer job list would push the brief against the cap
  harder, and that is a tuning note for the brief path,
  not a failure here.
- Not proved: a live Redis round trip (the fake backend
  has no network cost, so live timings will be higher),
  a Spark-composed brief (the brief here is a template
  brief: GOV-001 leaves live Spark transport blocked),
  or alert behavior under load (the tick yields zero
  alerts here by design; alert counts under a loaded,
  failing room are Milo's INT-023, not this check).

## Cost check: INT-007 (Pax, 2026-10-27)

Script: `intel/cost_check.py`. Cost table:
`intel/evals/cost.md`. Transcript: `intel/evals/cost.log`.
Tests: `tests/test_intel_cost.py`.

Run it (from the repo root):

```
python3 intel/cost_check.py
```

The check, in order: it builds the demo-day call
inventory from plan/DEMO.md (morning brief Shot 2,
dispatch plan Shot 5, closing brief Shot 11, alert
polish Shots 8/8b, boot brief Shot 0 only if OS-004
rules go), measures each call's input from repo files
and code (brief prompts built exactly as compose_brief
builds them, dispatch input as dispatch.md plus the
locked demo goal), prices them at the client's estimate
rates, and asserts the worst case with boot brief stays
under the $75 reserved half and the $150 credit.

What it proves, and what it does not:

- Proved: the headroom shape. Expected demo day
  $0.0213, worst demo day $0.1279, worst with boot brief
  $0.1440, headroom $74.8560 against the reserved half.
  Real rates would have to exceed placeholder rates by
  520x before the reserved half is breached. On the
  primary agent transport the API spend is $0 by the
  client's own rule; the dollar totals are the HTTP
  fallback case.
- Not proved: that demo day fits the credit as a fact.
  The rates are planning placeholders, not pricing
  facts (the client source says so verbatim), no live
  Spark call was made, the ledger holds no live spend
  to project from, and GOV-001 (endpoint and key)
  stays unnamed. Re-check against real pricing the day
  a real endpoint and key exist.

## Spark-down drill: INT-008 (Pax, 2026-10-27)

Script: `intel/spark_down_drill.py`. Drill table:
`intel/evals/spark_down.md`. Transcript:
`intel/evals/spark_down.log`. Tests:
`tests/test_intel_spark_down.py`.

Run it (from the repo root):

```
python3 intel/spark_down_drill.py
```

The drill, in order: the shipped SparkClient over the
shipped HTTP transport is pointed at a closed localhost
port, and every Spark-touching feature runs against that
dead endpoint on one fixture snapshot (2 messages, 1
stalled claimed job, 1 blocked job). The precondition
stage proves the endpoint is really down: the real
transport raises SparkError (connection refused), not a
stubbed failure.

What it proves, and what it does not:

- Proved: with the endpoint dead, briefs fall back to
  the template (TEMPLATE first line, inside budget),
  the Spark-only brief path returns the canned
  spark_down line verbatim, dispatch returns the
  FALLBACK plan with an endpoint-down warning, the
  watchdog keeps its template explanations, the CLI
  brief exits 0 with a template brief, and nothing
  crashes, posts, or spends.
- Changed to make it pass: dispatch previously let a
  transport error propagate (DSP-017 as pinned); INT-008
  amends that rule so a transport error returns the
  FALLBACK plan, and the brief record now says template
  when the template wrote the text instead of saying
  spark whenever a client was passed. A structured plan
  that fails a guard still raises with no fallback.
- Not proved: other failure shapes (slow responses,
  500s, malformed bodies) and browser rendering of the
  dashboard panels. The Redis-outage drill is INT-009,
  landed below and separate from this one.

## Redis-outage drill: INT-009 (Pax, 2026-10-27)

Script: `intel/redis_down_drill.py`. Drill table:
`intel/evals/redis_down.md`. Transcript:
`intel/evals/redis_down.log`. Tests:
`tests/test_intel_redis_down.py`.

Run it (from the repo root):

```
python3 intel/redis_down_drill.py
```

The drill, in order: the shipped CLI is pointed at a
closed localhost port, and every intel command runs
against that dead store. The precondition stage proves
the store is really down: the shipped
relay_common.api_get raises RuntimeError (curl rc=7,
connection refused, after 4 attempts), not a stubbed
failure.

What it proves, and what it does not:

- Proved: with the store dead, every Redis-dependent
  command (snapshot, brief generation, brief list and
  show, dispatch show and undo, dispatch posting,
  alerts show and query) fails loudly with RELAY_ERROR
  and exit 2, with empty stdout and no traceback, and
  the posting failure names that no dispatch record was
  stored.
- Changed to make it pass: five CLI paths used to let
  a store failure escape as a traceback (brief
  generation, brief list, brief show, dispatch show,
  dispatch undo), because each caught only its own
  narrow error type. INT-009 adds a generic Exception
  handler after the narrow ones on each path, matching
  the snapshot and alerts paths, which already had it.
  No engine changed: engines raising is correct, and
  the CLI is the surface that must never trace.
- Correctly still succeeding: a dry-run morning brief
  (the BRF-028 guard fails open and a dry run stores
  nothing) and a dispatch dry-run (pure validation,
  DSP-006) both exit 0 during the outage, because
  neither needs the store. The drill asserts both, so
  a future change that makes either one depend on the
  store fails the drill instead of failing silently
  in an outage.
- Not proved: the watch route under a real outage.
  The watch subcommand is still the unimplemented stub
  (FND-016), so its RELAY_ERROR is the stub reporting
  itself, not a Redis failure. Other failure shapes
  (slow responses, partial reads, a store answering
  garbage) are also not covered; this drill exercises
  the unreachable case only.

## Spoofed-dispatch drill: INT-010 (Pax, 2026-10-27)

Script: `intel/spoof_dispatch_drill.py`. Drill table:
`intel/evals/spoof_dispatch.md`. Transcript:
`intel/evals/spoof_dispatch.log`. Tests:
`tests/test_intel_spoof_dispatch.py`, plus the
rejected-dispatch cases in `tests/test_intel_watchdog.py`
(registry count, coverage, severity mapping).

Run it (from the repo root):

```
python3 intel/spoof_dispatch_drill.py
```

The drill, in order: the overseer posts a job signed
with the shipped HMAC signer (v2) on the suite's
in-memory fake store, an attacker rewrites the spec in
the store directly, a worker claims with the crew
keyring and is refused, and a watchdog tick on a
snapshot carrying the refusal line yields the alert.

What it proves, and what it does not:

- Proved: before the tamper, verify reports OK; after
  it, the shipped verifier reports BAD. The claim is
  refused (exit 1, "signature BAD" on stderr), the job
  stays open and unclaimed, and the fake bus carries
  the REJECTED line naming the poster and the refuser.
  The new rejected-dispatch detector turns that line
  into one critical alert (dedupe key
  rejected-dispatch:1:BAD), the emit callback receives
  it, the WDG-015 announcement line names it, and the
  detector dict validates into a WDG-010 record (id =
  dedupe key, subjects = the job, open).
- Changed to make it pass: nothing in jobs.py needed
  changing; claim refusal and the REJECTED announce
  already existed and were already tested. What was
  missing was the watchdog half: no detector turned a
  refusal into an alert record, so a refused dispatch
  was visible only while the chat line scrolled past.
  INT-010 adds detect_rejected_dispatch to
  intel/watchdog.py (registered, severity critical in
  SEVERITY_BY_KIND), plus its explanation template in
  intel/explanations.py. The detector verifies nothing
  itself: the watchdog holds no crew secret, so it
  reports the refusal the worker computed and must not
  invent a verdict for a job no worker refused.
- Correctly still allowed: an unsigned job claims fine
  with the keyring (warning only) and fires no rejected
  alert. Unsigned is allowed by design, and alerting on
  it would contradict that rule.
- Fixture note: Buffy's FND-027 spoof fixture (a job
  with a BAD HMAC in a dump) is still unlanded, so the
  drill builds its spoof job with the shipped signer
  plus a real tamper instead of a static dump. The BAD
  verdict comes from the shipped verifier recomputing
  the HMAC, which is stronger evidence than a
  pre-written bad string.
- Not proved: a live-room refusal. The drill runs on
  the fake store, so the REJECTED line reaching a real
  room, and the dashboard rendering the alert record
  in a browser, are both still unproved. The detector
  also reads only the snapshot window: a refusal line
  older than the tick cap is not re-reported by a
  capped tick, though the record written from the first
  tick persists in the store.

## Security pass: INT-011 (Pax, 2026-10-27)

Script: `intel/security_pass.py`. Pass table:
`intel/evals/security_pass.md`. Transcript:
`intel/evals/security_pass.log`. Tests:
`tests/test_intel_security_pass.py`.

Run it (from the repo root):

```
python3 intel/security_pass.py
```

The pass scans the whole tree for provider token
shapes, private key headers, quoted credential
assignments, and secret filenames, and prints only
file, line, and kind for each hit, never a value.
Verdict at this tip: 0 findings. The 7
shape-shaped hits in the tree are all documented
fixtures (repeated-character fakes, drill-marked
values, sequential filler, a test-labeled value),
each classified by file, line, and kind in the
pass table. Keyring lines are not content scanned
on purpose: a line carrying the word secret is a
label, and a line with a random secret part is
indistinguishable from namespace strings, so the
keyring controls are the filename rule, the
.gitignore entries, and the drill generating a
fresh secret per run. This batch removes the one
committed keyring literal the tree had (the spoof
drill's dummy secret) and adds the missing
.gitignore entries (*.env, .env*, *.keyring,
job-secret, admin_secret, *.pem, *.key), verified
with git check-ignore and with no tracked file
colliding. Not proved: git history still holds the
old drill literal (a dummy, so no rotation is
owed), and a shape scan cannot prove a
random-looking string is not a real credential,
only that no shaped secret exists in the tree.

### Signed-job trust list enforcement (OS-112)

Before any local agent may claim a job, the overseer
verifies the job's HMAC-SHA256 v2 signature against
the local trust list (`intel/trust.py`). A job signed
by a trusted crew with a valid v2 signature is
claimable; the same job unsigned, signed by an
untrusted kid, carrying a bad, expired, or legacy v1
signature is refused at claim time. The refusal is a
logged, board-visible event, never a silent skip:
`trust_tick` journals one trust-refusal record per
refused job (dedupe `trust-refusal:<job>`), so a
second tick journals nothing new, and `refusal_note`
gives the overseer the exact text for the job record.
Badge claims clamp to local policy in the same
decision, and every dropped badge is named; when no
badge policy is stated, claims pass through and the
decision says the policy is unset instead of
inventing one (OS-115, Dale's ruling, is the decision
that fills it in). A nick is never authority: a job
under a spoofed crew nick is judged by its signature
alone. The module is judgment, not hands: it never
moves a claim, never writes a job record, never posts
to the bus, and has no push path, so a refusal judged
here can never ring a phone. Its refusal records also
render as Hana's OS-117 federation trust events, so
the board and the brief surface them through the
existing federation section. Drill:
`intel/drills/trust_enforcement.py` (9 PASS, real v2
signatures over label-derived fixture secrets).
Not proved here: a refusal landing in a live job
record on a booted test image (no test image in
repo), a trust list fed by the OS-110 join (not
landed), or the OS-113 two-machine drill. The OS-114
room-level negative test has since landed (next
section); the spoofed-nick case is now proven at
room level as well as at the decision level.

### Trust negative test (OS-114)

The OS-112 gate, run at room level. An untrusted
machine joins the fixture room and posts a job, and
the same job is re-posted under a spoofed crew nick;
the trusted machine's overseer refuses both
attempts, logs both, and surfaces both, and no work
is exchanged. The two attempts earn the two reasons
the acceptance names: the outsider's own signed post
is refused as "untrusted signer", and the spoofed
re-post with no signature is refused as "signature
absent". A guard phase proves the signed variant of
the spoof is refused as "untrusted signer" too, so
no spoof shape slips through; the guard is
decision-level only, so the room log holds exactly
the two attempts. Across the test window (3 ticks,
3 trusted agents attempting claims at each tick),
zero hostile jobs are claimed; the first tick
journals exactly 2 refusal records and later ticks
journal nothing new. Both refusals appear on the
brief lines and the OS-117 federation feed naming
the outsider machine, and the end state has no claim,
progress note, or artifact for any hostile job while
the trusted control job stays claimable, so the room
is clean, not empty. Drill:
`intel/drills/trust_negative.py` (8 PASS, real v2
signatures over label-derived fixture secrets).
Not proved here: a refusal landing in a live job
record on a booted test image (no test image in
repo), a trust list fed by the OS-110 join (not
landed), the OS-113 two-machine drill, or the
OS-115 policy ruling; the room in this drill is a
fixture room, not two live machines.

### Muse wake adapter (OS-119)

When the bell rings for a sleeping Muse instance
(the Hana and Rowan class of runtime), the adapter
(`intel/wake.py`) starts the agent's session with
the job already in its hands: goal, spec text,
acceptance checks, files, and the mind image
reference when the job carries one. The agent's
first act is the job, never a poll: the session's
first bus action is the claim of the bundled job
or progress on it, and a session started with no
bundle polls status instead, which is exactly the
shape the drill fails on purpose. The wake rule is
a pure function: the agent must be asleep with a
muse runtime, the job must be addressed to that
agent and only that agent, and the job must have
an id. Awake agents, other runtimes, wrong
addressees, and anonymous jobs all yield no wake,
and malformed records yield no wake and no crash.
`wake_tick` journals one wake record per job and
agent pair (dedupe `wake:<job>:<agent>`), so a
second tick journals nothing new while a second
job wakes again. A bundle whose job carries no
mind image reference carries mind_image None plus
a note naming the OS-102 loader as pending, rather
than inventing a reference. The module is decision
and bundle, not hands: it never starts a session,
never touches a process, never posts to the bus,
and has no push path. Drill:
`intel/drills/wake.py` (6 PASS, fake Muse runtime
applies the start). Not proved here: a live Muse
session actually started through a live runtime
(the session mechanism belongs to the runtime
itself), the bell actually ringing (the resident
watchman is Pax OS-118), a mind image actually
loaded (OS-102 has not landed), or a wake on a
booted test image (no test image in repo).

### Measured A/B run + image-defect attribution (OS-106)

The demo's one comparison, bare launch vs mind image,
recorded side by side (`intel/abrun.py`): the same
fixed job suite under both versions, with completion
time and acceptance outcome per job per version, and
every observed stall attributed from its journal
evidence as an image defect or a worker failure. A
stall naming a skill the image lacks is a
missing-skill defect, a stall naming a carried bad
instruction is a bad-instruction defect, a stall for
want of context under a thin brief is a thin-brief
defect, and a dead worker under a complete image is
a worker failure, never an image defect. A stall
naming neither an image layer nor a worker cause is
unattributed, never guessed, and a stall naming a
fault the image does not carry is no defect. The
comparison's defects feed a revision note that
proposes the next version's layer changes and
applies nothing. Drill:
`intel/drills/ab_run.py` (6 PASS: bare 1100 seconds
and 1 pass, mind-v1 470 seconds and 3 passes, one
missing-skill and one thin-brief defect with journal
evidence, worker-death control clean). Not proved
here: the real OS-105 harness (Buffy, not landed),
so this run is the harness shape on fixtures; a live
agent under either version; a result on a booted
test image (no test image in repo); or the board
view of the result (Rowan OS-107).

### Capability refusal enforcement (OS-081)

A process that attempts an action outside its grant is
refused, the refusal is written as an alert record with
a plain-English explanation, and the watchdog surfaces
it like any other alert (`intel/capability.py`). The
four actions are the four OS-080 grant fields: bus_post,
spend, network, and write_file, whose subject is the
path. A write is allowed only inside one of the grant's
write_paths, matched on whole path segments, so
crew/milo/ never authorizes crew/milo2/x, and a dot-dot
escape is refused naming the normalized path. Default
is deny: a process with no grant file is refused, and
the refusal still names the attempting process, because
the OS layer passes the process identity in. The
explanation names the identity, the action, and the
missing capability (write refusals name write:<path>),
rendered through the WDG-011 template. `capability_tick`
journals one refusal record per refused attempt (dedupe
capability-refusal:<identity>:<action>:<subject>), so a
second tick journals nothing new, and allowed attempts
journal nothing. The module is judgment, not hands: it
never performs the action, never moves a claim, never
writes a job record, never posts to the bus, and has no
push path; the caller persists the alert through
intel.store.write_alert, which gives it its id, status,
and lifecycle. Drill:
`intel/drills/capability_refusal.py` (5/5 phases PASS).
Not proved here: a refusal on a booted test image (no
test image in repo), the OS layer refusing a live
process action (the grant-file loading half is Pax
OS-080, first light below), the dashboard banner (Rowan
OS-084, not landed), the policy defaults (Dale OS-082,
not landed), or the DEMO.md Shot 8b staging itself.

### Capability files (OS-080)

Every crew process runs as a named identity with an
explicit capability file (`intel/capability_files.py`).
One JSON file per identity lives in
`intel/capabilities/`, named `<identity>.json`, carrying
exactly identity, bus_post, spend, network, and
write_paths: the grant shape `intel/capability.py`
(OS-081) judges. A launcher loads the grant at process
start with `load_grant_for`: a missing file is not a
grant (OS-081 refuses that process), and a present but
invalid file raises instead of starting the process
ungranted. Unknown or missing keys, non-boolean flags,
and absolute, empty, or root-escaping write paths all
fail validation, so a typo can never silently narrow or
widen a grant. `load_crew_grants` loads a whole
directory and reports bad files and filename-identity
mismatches as errors instead of raising. Shipped files
cover all five crew nicks with provisional flags
(network on so a process can reach the bus and queue,
bus_post and spend off under Dale's standing rules,
writes inside crew/<nick>/ only). This file format is
not the mind-image bundle grants.json layer, which
names an actions list, not these four policy fields.
Not proved here: a launcher actually calling
load_grant_for at process start (no launcher wiring
yet), a process on a booted test image running under
its file, or Dale's approval of the defaults (OS-082,
not landed). Pinning tests in
tests/test_intel_capability_files.py.
