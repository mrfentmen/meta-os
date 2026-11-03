# MT-07 in full detail — Hands-Free intake path (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 22:58 EST. This is a fixture/spec, not a
run. No MT-07 case has been executed under MT-07, no case results file
exists yet, and nothing below is a pass. Firing waits on BOTH: (1) Del
tops up Meta API billing (HTTP 402 during Pax's live hunt #3), and (2)
Del picks a key route (Route A: key placed on Milo's VM; Route B: Milo
specs, Pax executes the live run and posts the receipt, Milo verdicts
it). Pax directed 2026-11-02 ~22:57 EST that MT-07 detail comes next as
prep — write the case set; any live-key run inside it stays prep-only
until Del picks a route and credits exist. Spend cap $10 total for the
whole directive, guardrail-tracked; cost for MT-07 is TBD at fire time
from the published Spark rates, never invented here. Nothing dials a
real service from this prep, ever. Dispatch, if any case touches it,
stays simulated loopback only, labelled SIMULATED everywhere.

## What the check is

The text-first intake case set runs against the real intake path in
`handsfree/`, per os-build/MILO_TEST_SLICE.md and
os-build/MILO_TEST_PREP.md. The fixture start is the Buffy R13 intake
cases, R13-376 through R13-400 (25 cases, BUFFY_TASKS_ROUND13_500.md at
the repo root). Each R13 case demands the same proof shape: test output
plus the brief or refusal record; a crash or a silent drop fails the
case, and any dispatch stays simulated and labelled. MT-07 proof is the
case results file: one line per case, failures named, none hidden.

## The real intake path (read on the branch, not assumed)

`handsfree/README.md` states the position plainly: host on this
machine, no kernel service; Node modules with tests; nothing here has
run on Meta OS; not voice (no microphone, wake word, or synthesis —
the modules produce the text a voice layer would say); not a service
(no boot entry, no kernel call, no supervisor row); not approval by
itself (`approval.mjs` records an answer, the caller must still check
`mayAct()` before acting).

The intake path itself is `handsfree/intake.mjs`:

- The inbox is lines a person can type: one line, one order, the
  agent's name before a colon. Blank lines and `#` comments are
  ignored.
- A line with no colon is NOT guessed at: it stays in the inbox and
  is reported, because an order nobody can parse is an order nobody
  should run.
- `MAX_ORDER_CHARS = 4096`. A longer line is refused with its length
  recorded, and the line stays in the inbox for a human to split.
- `parseInbox` returns `{ jobs, skipped }`: a parsed line becomes
  `{ agent, orders }`; a skipped line carries its line number, text,
  and reason (`oversized-order`, or `no agent before a colon`, or
  `empty agent or empty order`).
- `validateOrder` refusal reasons (`ORDER_REFUSALS`): `malformed-no-
  colon`, `empty-agent`, `empty-order`, `not-a-string`,
  `oversized-order`, `empty-inbox`.
- The hosted registry commands (`handsfree/hosted.mjs`) are `intake`
  (`os-build/handsfree/inbox.txt` -> `jobs/`), `brief`
  (`jobs/*.result.json` -> `brief.txt`), and `approval` (one request,
  one answer, appended to the run ledger; a second answer is logged
  as a duplicate and does not count). The approval drill uses its own
  run directory and cannot approve anything real.
- Existing coverage on the branch: `tests/handsfree.test.mjs` (C1
  inbox parsing, C2 brief, C3 approval) and
  `tests/handsfree-r11.test.mjs` (speak, refusals, latency, voice,
  session). Those test files are the starting point for the case set,
  not a fresh MT-07 measurement: no MT-07 test has been run under
  this check yet, and no test count is claimed here as an MT-07
  result.

## The case set (R13-376..R13-400, verbatim case names)

Each case runs one inbox through the real intake path and records one
of three outcomes, exactly as the R13 wording demands: brief produced,
refusal recorded, or fence named. The "intake says" column below is
what `intake.mjs` as read on the branch does with that input shape —
it is the spec's expectation, not a run result. Where intake has no
rule for the case's substance, the table says so outright instead of
inventing one; those rows are questions to Pax, listed again under
"Questions to Pax" — they do not change the case's pass rule, which
is: no crash, no silent drop, outcome recorded.

| Case | R13 name | Input shape | Intake says (spec expectation) |
|---|---|---|---|
| MT-07-01 | R13-376 plain text order intake | `agent: do this` | Job file: one `{ agent, orders }` |
| MT-07-02 | R13-377 multi-line intake | Several `agent: ...` lines | One job per parsed line; blank lines and `#` comments ignored |
| MT-07-03 | R13-378 empty intake | Empty inbox | No jobs; `empty-inbox` refusal reason applies |
| MT-07-04 | R13-379 whitespace-only intake | Blank / spaces-only lines | No jobs; lines trim to empty and are ignored |
| MT-07-05 | R13-380 oversized intake (over the cap) | One line over 4096 chars | Skipped, reason `oversized-order`, length recorded, line stays in inbox |
| MT-07-06 | R13-381 intake with control characters | Control chars in the line | Intake has no control-character rule: a line with a colon parses as a job, a line without one stays in the inbox — QUESTION to Pax whether that is the expected outcome or a refusal is wanted |
| MT-07-07 | R13-382 intake with unicode text | Non-ASCII order text | Parses as a job; intake does not restrict character sets |
| MT-07-08 | R13-383 intake with a URL | Order text containing a URL | Parses as a job; intake does not treat URLs specially |
| MT-07-09 | R13-384 intake with a file path | Order text containing a path | Parses as a job; intake does not treat paths specially |
| MT-07-10 | R13-385 intake naming a loop that is draft | `agent:` naming a draft loop | Intake accepts any agent prefix; loop existence / draft status is NOT an intake check — outcome is a job file, loop resolution out of intake scope (QUESTION to Pax) |
| MT-07-11 | R13-386 intake naming a loop that is real | `agent:` naming a real loop | Same as MT-07-10: job file; loop resolution out of intake scope |
| MT-07-12 | R13-387 intake with an urgent flag | Order text with an urgency marker | Parses as a job; intake has no urgency handling — flag text stays order text |
| MT-07-13 | R13-388 intake with a budget note | Order text with a budget note | Parses as a job; intake has no budget handling — note stays order text |
| MT-07-14 | R13-389 intake with a STOP request | Order text asking to stop | Intake creates a job; STOP semantics belong to the loop drill, not intake — QUESTION to Pax whether the case expects a job file or a named fence |
| MT-07-15 | R13-390 intake with a status question | Order text asking status | Intake creates a job; answering is not intake's job — outcome recorded as job file, answer out of scope |
| MT-07-16 | R13-391 intake with two jobs | Two `agent: ...` lines | Two job files |
| MT-07-17 | R13-392 intake repeating a finished job | Same order as a finished job | Intake has no dedup: a second job file is created — QUESTION to Pax (baton-pass proof covers duplication at the loop level, not intake) |
| MT-07-18 | R13-393 intake contradicting a standing fence | Order text against a fence | Intake does not check fences: job file created, fence check belongs to the caller (`mayAct()` before acting) — outcome recorded, fence named in the record |
| MT-07-19 | R13-394 intake with a dispatch request (must stay simulated) | Order text asking for dispatch | Intake creates a job; any dispatch from it stays simulated loopback only, labelled SIMULATED, never a real service — this is a slice fence, not an intake rule |
| MT-07-20 | R13-395 intake in all caps | Uppercase `AGENT: ORDER` | Parses as a job; intake does no case folding, agent name kept as typed |
| MT-07-21 | R13-396 intake with punctuation only | Punctuation, no colon | No colon, so the line stays in the inbox, reported, not guessed at |
| MT-07-22 | R13-397 intake with a pasted log | Multi-line pasted log | Lines with a colon parse as jobs, lines without one stay in the inbox — noisy input, each line judged on its own, nothing silently dropped |
| MT-07-23 | R13-398 intake with a pasted error | Multi-line pasted error | Same as MT-07-22: colon lines become jobs, others stay in the inbox |
| MT-07-24 | R13-399 intake with a date and time | Order text with date/time | Parses as a job; date/time stays order text, intake has no scheduling rule |
| MT-07-25 | R13-400 intake with no verb | `agent: <noun phrase>` | Parses as a job; intake does not check for verbs |

## Firing steps (when the hold clears)

1. For each of the 25 cases, write the inbox exactly as the case
   names it, run it through the real intake path
   (`handsfree/hosted.mjs intake` or the `parseInbox` path it
   drives), and record the outcome per case: job file(s) created,
   line(s) left in the inbox with reason, or refusal recorded.
2. For every job file created, record whether a brief was produced
   (`brief` command over `jobs/*.result.json`) or why no brief
   exists yet (no result file is not a failure of intake; it is a
   missing step, named as such).
3. Write the case results file: one line per case — case id, R13
   number, input shape, outcome, and the job file / refusal record
   behind it. Failures named, none hidden. A crash or a silent drop
   on any case fails that case and is reported as failed, never
   worked around, never faked.
4. Dispatch check on MT-07-19: if any dispatch is exercised, the
   record must show simulated loopback only, labelled SIMULATED. A
   real service dialled anywhere fails the whole check.
5. Verdict: Milo verdicts from the case results file only. No
   result file, no verdict.

## Questions to Pax (asked with the MT-07 completion post)

1. MT-06 ruling applied? Pax ruled ~22:57 EST that the key-route
   hold does NOT cover MT-06's keyless local check. Does the same
   ruling cover MT-07's keyless local case set — may the 25 cases
   be executed locally as prep (Node modules, no key, no service),
   or does MT-07 stay written-only until Del picks a route AND the
   402 is topped up? Until Pax answers, MT-07 stays written-only.
2. Control characters (MT-07-06): is parse-as-job / stay-in-inbox
   the expected outcome, or should the case expect a refusal?
3. Loop naming (MT-07-10/11): is a job file the expected outcome
   with loop resolution out of intake scope, or should a draft
   loop name refuse?
4. STOP request (MT-07-14): job file, or named fence?
5. Repeat of a finished job (MT-07-17): second job file accepted,
   or should intake dedup? (Loop-level baton proof already covers
   duplication; this asks only about intake.)
6. MT-08 next, or hold the chain at MT-07 until the MT-07 questions
   are answered? Chain closes at MT-08 per Pax's ruling; no extra
   test-layer tasks are invented either way.

## Answers from Pax (room 1, 2026-11-02 23:11–23:12 EST)

All six questions closed. Recorded verbatim in substance:

1. YES, the MT-06 keyless ruling extends: MT-07's 25 cases run
   the local intake path with no Meta API call, so they may
   execute locally now. The route + top-up hold covers only steps
   that call live models. This file's "firing waits on both" line
   is the slice default, superseded here for keyless execution.
   MT-07 local execution is therefore PERMITTED but NOT YET RUN
   as of 2026-11-02 23:13 EST — no case executed, no results file
   yet, sequencing per Pax (MT-08 detail was directed next).
2. Control chars: expected outcome is current behavior — colon
   line parses as a job, no-colon line stays in the inbox; NO
   new refusal wanted at intake; chars recorded verbatim, never
   stripped.
3. Draft loop: job file; loop resolution is out of intake scope,
   the loop drill owns draft vs real.
4. STOP request: job file, not a named fence at intake; STOP
   semantics belong to the loop drill downstream.
5. Repeat job: second job file created, as intake has no dedup;
   dedup lives at loop level (baton-pass). Pass rule stands
   throughout: no crash, no silent drop, outcome recorded.
6. MT-08 detail next as prep — no hold. These answers close the
   MT-07 questions. Full MT-08 detail in MILO_TEST_MT08.md.

## Execution record (2026-11-02 23:33 EST)

EXECUTED, no longer written-only. Pax 23:28 EST confirmed MT-07 local
execution may run now (with the MT-08 register task; neither waits on
the key route or the 402 top-up). Full results in
MILO_TEST_MT07_RESULTS.md: all 25 cases run through the real CLI
(`node handsfree/intake.mjs`) against both branch code
(milo/test-slice-prep @ 26f81bc0) and main code (@ 3142f841), identical
outcomes on every case, 0 crashes, 0 silent drops. Verdict: PASS on
intake outcomes only, under MT-07's pass rule. Named limits: no brief
produced (no `*.result.json` files exist after intake alone — a missing
step, not an intake failure); no dispatch exercised on MT-07-19. The
"firing waits on both" line above remains true for any live-key step
inside MT-07; there is none in this execution.

## What this is not

- Not a run: no MT-07 case has been executed, no case results file
  exists, nothing here is a pass. (Superseded by the execution record
  above for the local intake cases only; the live-key reading of this
  line still stands.)
- Not voice: no microphone, wake word, or synthesis is involved.
- Not approval: a job file is not permission to act; the caller
  must still check `mayAct()` before acting.
- Not a loop run: baton-pass, STOP-drill, budget-drill, death-drill,
  and chaos-drill R13 cases on the handsfree loop (R13-278..R13-373)
  are loop drills, not intake cases, and are NOT part of MT-07.
- Not a category change: no products.js edit, no new intake rule
  invented here. If Pax wants a new refusal (control characters,
  draft loops), that is a code task outside the MT chain, not
  something this spec assumes.
