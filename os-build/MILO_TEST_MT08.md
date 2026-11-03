# MT-08 in full detail — Gate duty for the loop itself (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 23:13 EST. This is a spec, not a
gate run. No gate-1 is executed by this file, no branch is merged by
it, and nothing below is a pass. MT-08 closes the test-slice chain
per Pax's ruling (chain closes at MT-08, no extra test-layer tasks
invented). Pax directed 2026-11-02 23:11 EST that MT-08 detail comes
next as prep — no hold. Spend: $0. No live-key call is involved in
gate duty at all, so the route pick and the 402 top-up do not block
MT-08's gate work; they block only the live-key runs inside MT-01
through MT-05 and any live-key step inside MT-07. Nothing dials a
real service from this prep, ever.

## What the check is

Per os-build/MILO_TEST_SLICE.md: "Gate duty for the loop itself.
Every agentic-loop branch that lands during this directive gets
Milo's gate-1 in his own words before Pax merges, same discipline
as B10 and the kernel lanes."

Gate-1 means, in Milo's own words on room 1, before Pax's merge
call:

1. The branch builds clean for the crates it touches (a compile
   failure is RED, named, never worked around).
2. The affected crates' test suites run in full, with counts
   reported (lib + parity where the lane has parity tests), zero
   failures for GREEN.
3. Where the lane has a parity or fixture bar, it is reported
   verbatim, not rounded into a pass.
4. Kernel branches carry one more hold that gate-1 alone does not
   clear: the Mac boot log. A kernel branch can be gate-1 GREEN
   and still HELD from merge until Del's Mac lane posts the boot
   log (see ipc2 below).
5. The merge call is Pax's, always. A GREEN verdict is not a
   merge, and this job never merges to main.

## Who runs the gates, and who records them

This is the split that binds MT-08, and it is stated here so the
record does not blur it:

- Gate-1 execution belongs to Milo's rust-work loop (the separate
  5-minute job). That loop runs the builds and tests in its own
  /tmp worktree and posts the verdict to room 1.
- This 5-minute job does NOT run gate-1 and does NOT re-verdict
  a branch. Its MT-08 role is to write this detail, keep the
  register below current from room 1 posts, and relay verdicts
  here with attribution — never as its own fresh verdict.
- A verdict relayed here names its source (the room 1 post and
  the loop that posted it). If the source post is ever unclear,
  the register says so instead of filling the gap.

## Register: branches and gate state relayed from room 1

Only branches with a room 1 gate request or verdict during this
directive window (from 2026-11-02 21:38 EST) are listed. Nothing
is listed from memory or assumption.

- batch/B10 (Hana gate fix) @ 8f92dbb — GATE-1 GREEN, relayed
  from the rust-work loop's room 1 post (254 lib + 53 parity,
  E0277 fixed). Merge call Pax's. Later B10 tip @ cbd15dd3
  (brief_exceeds_budget word-count parity) — GATE-1 GREEN relayed
  from the rust-work loop's room 1 post 23:15 EST (check clean,
  lib 283 + parity 53, 0 failed), not re-run by this job.
- rowan/kernel-k4-ipc2 @ f654ed5 — gate-1 GREEN noted by Rowan
  on room 1 2026-11-02 23:11 EST ("Milo GATE-1 GREEN on ipc2
  noted"), relayed here, not re-run by this job. HELD from
  merge by Pax until the Mac boot log lands, per Pax 22:50 EST.
  GREEN plus held is not a contradiction: the gate passed, the
  boot proof is still owed.
- rowan/kernel-k4-pair-swap @ 0a2d5cd — GATE-1 GREEN relayed
  from the rust-work loop's room 1 post 23:12 EST (userspace
  --bins clean, kernel cargo check clean, 27 warnings, zero from
  new logic), not re-run by this job. HELD from merge pending
  the Mac boot log + Pax merge call (Rowan pump 23:28 EST).
  GREEN plus held is not a contradiction, same as ipc2.
- Retroactive main-cut lines (Pax 23:28 EST: YES, the register
  carries one line per cut; scope and wording below are Pax's,
  relayed here, not this job's fresh verdicts):
  - Cut 1 (Pax's line, verbatim in substance): doc/config N/A,
    loader script GREEN, K4/KF-03 HELD with reasons named.
    Reasons named: K4 (ipc2 @ f654ed5, pair-swap @ 0a2d5cd)
    HELD pending the Mac boot log + Pax merge call; KF-03 HELD
    pending Mac/Buffy re-proof. Loader script GREEN is the
    loader-fix gate-1 GREEN @ b224af4 relayed from the rust-work
    loop, cut to main @ 1b9e2a05 by Pax's cherry-pick.
  - H+2 cut @ 0eddeb5d: Pax's cut, 96/96 blobs (hana/metaos1-base
    + buffy/boot-installer + bond/12h), 0-conflict; audit rows
    Milo's when ready, not holding the cut (Pax 22:58 EST).
  - Main @ 4bef226: Pax lane merges during the directive;
    monitor only, no MT-08 verdict claimed beyond Pax's merge
    calls on room 1.
  - Main @ 3142f841 (2026-11-02 23:28 EST): batch/B10 MERGED by
    Pax — hand-combine of the FND-034 word-count change (brief.rs
    + parity test at branch blobs; everything else already
    identical on main). Pax: Milo GATE-1 GREEN on the branch tip
    covers the combined crate. Relayed, not re-run by this job.

## MT-07 answers recorded here (Pax, room 1, 23:11–23:12 EST)

These close the MT-07 questions; they are recorded in full in
MILO_TEST_MT07.md and summarised here because they change what
MT-07 may do next:

1. The MT-06 keyless ruling extends: MT-07's 25 cases run the
   local intake path with no Meta API call, so they may execute
   locally now. The route + top-up hold covers only steps that
   call live models. MT-07's "firing waits on both" line is the
   slice default, superseded here for keyless execution.
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
   MT-07 questions.

MT-07 local execution is therefore PERMITTED, and as of
2026-11-02 23:33 EST it is RUN: see MILO_TEST_MT07_RESULTS.md
(25 cases, PASS on intake outcomes only). Execution sequencing
for MT-07 is closed by that run plus Pax's 23:28 EST answers
below.

## Answers from Pax (room 1, 2026-11-02 23:28 EST) — questions closed

Recorded verbatim in substance, with the batch/B10 merge note from
the same message:

- batch/B10 MERGED to main @ 3142f841 (see retroactive lines above).
- (a) Scope: MT-08's scope is MT-chain gate duty + relay of
  verdicts. Kernel + B10 lanes keep their own gate loops; MT-08
  does NOT absorb them. This file's register therefore relays
  kernel/B10 verdicts with attribution and never re-verdicts
  them, exactly as the split above states.
- (b) Retroactive lines: YES. The register carries one line per
  main cut — cut 1: doc/config N/A, loader script GREEN, K4/KF-03
  HELD with reasons named (see retroactive lines above).
- (c) Sequencing: BOTH. MT-07 local execution may run now AND the
  MT-08 register task proceeds; neither waits on the key route or
  the 402 top-up. Chain closed: no new test-layer tasks invented
  beyond MT-08.
- MT-07 local execution was run under (c) on 2026-11-02 23:33 EST;
  results in MILO_TEST_MT07_RESULTS.md. The MT-08 register update
  in this file is the register task proceeding under (c).

## Questions to Pax (asked with the MT-08 completion post, now closed)

1. Scope: does MT-08 cover loop branches only, or also the
   kernel lanes (ipc2, pair-swap) and the intel/B10 lane, which
   already follow the same gate-1 discipline?
2. Retroactive lines: do the lane merges Pax already cut to
   main during this directive need MT-08 gate lines in this
   register, or does Pax's merge call cover them?
3. Sequencing: MT-07 local execution is now permitted — does
   it run next, or does the chain close here and new
   layers/tasks come first? Per Del's sleep order, this post
   also asks Pax for more layers/tasks on this layer either
   way; nothing beyond MT-08 is invented until Pax answers.
4. Pair-swap gate: confirmed as rust-work-loop work, monitor
   only for this job — no action asked, noted so the two jobs
   do not duplicate it.

## What this is not

- Not a gate run: no build or test was executed for MT-08 by
  this job, and no verdict here is this job's own.
- Not a merge: nothing here merges to main, and no branch tip
  moves on this file's say-so.
- Not a verdict on pair-swap: requested, pending, Mac gate
  owed; anything else would be invented.
- Not a pass on MT-07: permitted is not run. No MT-07 case
  results file exists yet, and no MT-07 verdict is claimed.
  (Superseded 2026-11-02 23:33 EST: MT-07 executed, results in
  MILO_TEST_MT07_RESULTS.md, PASS on intake outcomes only.)
- Not a new task: the chain closes at MT-08. What comes after
  is Pax's call, not a task this file invents.
