# Endurance drills (NC-135): all results with log files

Harness reality first: the loop driver needed two environment fixes to
run on this Mac at all (both env-only, zero repo edits): GNU sed on
PATH (BSD sed breaks its task-close substitution) and cycle spacing
over 1 s (same-second checkpoint tags collide). Without them, every
cycle rolls back — found by the pre-tests, not assumed.

- NC-125 soak: 60 synthetic incidents, stub agent (55 s think + marker
  line), test gate true, MAX_PER_DAY=200. Result: 59 committed, 1 rolled
  back (the deliberate mid-soak kill, NC-127), 0 gate-red, 0 dirty-tree,
  0 capped, 0 lock contention. Per-incident caps (8 actions / 12 calls /
  $0.50) never approached: each incident took 1 action, 1 test call,
  $0.00 (stub agent, no model). Log: oc-proofs/nc-125-loop-soak.log
  (full), loop state in /tmp/loopsoak (scratch, kept for inspection).
- NC-126 budget trip (local stub ledger): pre-filled $74.99 + one
  $0.135 stub call → "GUARDRAIL STOP: estimated test spend $75.1250
  has reached the $75.00 test budget. No call sent." Exact refusal text.
- NC-127 restart: driver SIGKILLed mid-cycle (stub-sleep phase). The
  cycle rolled back with zero commits; the retry committed the same
  task exactly once (verified: one "committed" line, one commit for
  S-026). No duplicates.
- NC-128 offline: BLOCKED (round-2 finding stands — no sudo, no
  fault-injection path on this Mac). Not re-attempted; nothing to add.
- NC-129 backpressure: the 60-deep queue IS the pressure test — the
  loop drains sequentially (~60 s/cycle with the stub sleep). First
  failure mode observed: none in the driver; the only losses in the
  whole exercise were the two environment issues above (sed, tag
  collision), both outside the driver's logic.
- NC-130 reconstruct: 60 commits, 0 duplicate hashes, fsck silent.
  Append-only log reconstructs fully.
- NC-131 purge on copy: tip-task revert on a scratch copy appends one
  commit and reopens the task line (before N, after N+1, task open
  again). A mid-history revert conflicts (later commits own the same
  lines) — demonstrated, copy deleted. Evidence-purge semantics were
  proven on records data in round 2 (nb-084).
- NC-132 clock skew: skewed-future record fed to the timeline sorts
  purely by timestamp (2031 last), no validation, no rejection.
  Recorded as observed behavior.
- NC-133 disk: repo .git 700 KB at 27 cycles → 1372 KB at 60 cycles
  (~20 KB/cycle, mostly the growing marker file); state dir 16→20 KB.
  Projection at this cadence: ~29 MB/day. Real incidents carry image
  frames, so treat as a floor, not a forecast.
- NC-134 memory: peak loop-process RSS 2768 KB over the full soak
  (30 s sampling). The loop is shell+git; memory is a non-issue.
