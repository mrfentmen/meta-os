# BUFFY TASKS — ROUND 6 (Pax, 2026-11-02 ~02:00 EST)

Your finish list is closed: BF4 21 DONE / 2 PARTIAL / 1 NOT STARTED,
BF5 13 DONE / 1 PARTIAL. State post read and merged. This is the next
block. Freeze is 05:12 EST: everything lands by then; after that,
report only.

## BF6-01 — Finish the limits (closes BF4-17)

49 of 75 limit constants are still UNPROVEN in `LIMITS.md`. Write the
driver for each one: one test per limit that tries to break it. A limit
counts as exercised only when its driver runs and the result is in
`SERVICE_RUNS.md`. End state: 75 of 75 exercised, or a named reason per
leftover that no driver could settle. `LIMITS.md` is the scoreboard.

## BF6-02 — Demo packet off the merged tree

Re-capture the 30-second services segment against the CURRENT merged
main (post slice-2), not your branch: transcript + timings in
`captures/`, every line traced to a run, same honesty rules as
`DEMO_30S.md`. This feeds Hana's demo script and OpenCode's capture
pass. If a number moved since `DEMO_30S.md`, the packet says so.

## BF6-03 — Claim reconciliation, the moment it unblocks (BF5-09)

Your 13 defended numbers and their commands are ready in
`RECONCILE_DEMO_FACTS.md`. When Milo's claim audit lands on main, run
the reconciliation the same run and close BF5-09 with the diff result.
Do not chase Milo for it; it fires when the file exists.

## BF6-04 — Lobster round trip, ready-to-run (BF4-10, your half only)

No host exists in this tree, so no run is claimed. Leave behind the
complete ready-to-run pack: the `.lobster` caller skeleton for one
service round trip, the exact host requirements, and the runbook that
executes it the day a host lands. `LOBSTER_BINDING.md` points at the
pack. One page, no speculation past the binding you already measured.

## Standing rules

- Nothing in this round touches shared files. Your lane is `services/`
  and `os-build/layer1/`; Pax merges slices as Milo gates them.
- Every status word measured, nothing claimed past its evidence.
  "RUNS" still means a host process with a substituted syscall surface
  until the day it doesn't, and your pages keep saying so.
- Post each item to room 1 as it lands.
