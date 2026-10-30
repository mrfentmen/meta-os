# OS-085: budget config + pre-limit warnings (Milo, 2026-10-27)

OS-085's acceptance, proven on fixtures: a fixture lane driven
to its warning threshold produces a budget warning alert; at
cap, the queue holds new claims for that lane; and the hold is
visible in the brief's budget line (OS-079).

## What landed

- `intel/budgets.py`: the budget config and gate. Warning
  threshold 80% of cap, env-overridable through
  WATCHDOG_BUDGET_WARN_PERCENT (same fallback discipline as
  intel/thresholds.py: bad values fall back, never crash).
  `claim_allowed` is the queue gate: False only at cap.
  `hold_entry` builds the OS-079 budgets entry with its hold
  flag. A lane with no usable cap is unbudgeted — claims
  allowed, no warning — because an absent budget is not a
  zero budget. Per-process caps use the same functions with
  the process name as the lane; the watchdog detector today
  watches lanes, per the acceptance.
- `intel/watchdog.py`: `detect_budget_warning`, in DETECTORS,
  kind `budget-warning`, severity `warning` (WDG-024 mapping
  extended, table in intel/README.md). One alert per lane per
  tick, dedupe key `budget-warning:<lane>`. A lane at cap
  yields no warning: the hold is the louder signal, and
  warning about an already-held lane would double-report
  the same condition. Warnings never announce (WDG-015:
  only critical alerts announce).
- `intel/brief.py`: `memory_budget_lines` prints "new claims
  held" on entries with held True. Entries without the flag
  render exactly as before, so OS-079's existing lines are
  untouched.
- `intel/explanations.py`: the `budget-warning` template
  (WDG-011 pattern): plain-English one-liner plus suggested
  fix, filled from lane, spent, cap, remaining, threshold.
- Drill `intel/drills/budget_gate.py`, transcript
  `intel/evals/budget_gate.log`, pinning tests
  `tests/test_intel_budget_gate.py` (14 tests) plus the
  budget fixture added to SeverityMappingTest's POSITIVES
  in `tests/test_intel_watchdog.py` (the new detector kind
  had to join the table-or-emitted equality, like any new
  detector).

## Drill result (transcript: `budget_gate.log`)

- Phase 1, 70 of 100: no warning, claim granted.
- Phase 2, 80 of 100: exactly one budget-warning alert
  (spark, 80 of 100, remaining 20), claim still granted —
  the lane is at risk, not stopped.
- Phase 3, 100 of 100: no warning, claim held, job stays
  open, brief line reads "Spend: spark lane: 100 of 100
  budget (0 remaining) — new claims held".
- Phase 4: unbudgeted lane and malformed entries — no
  warning, no hold, no crash; the tick survives bad input.

## NOT proven here

- The live jobs.py claim path does not read the gate yet:
  there is no spend ledger in Redis for it to read from, and
  a gate wired to a ledger nobody writes would refuse or
  allow claims on stale figures. The drill's fake queue
  proves the gate function; wiring it into jobs.py
  cmd_claim against a real ledger is owed on the ledger.
- A live budget config feeding the brief: the brief line
  here is rendered from a hand-built memory_budget record,
  not from a live spend service (OS-079's own caveat stands:
  no caller yet fills memory_budget from live state).
- Per-process warnings on a live lane: the functions support
  them, but no process entry flows through the detector yet.
- The 80% threshold is a starting default, not a tuned
  value: no lane has yet been driven to its cap in
  production, so there is no spend history to tune against
  (compare WDG-027/INT-022 tuning for stall thresholds).
