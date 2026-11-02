# WAVE3 Imperium gaps (tasks 49-58) — verdicts 2026-11-02, wave3 tree

Source gaps list: sec5 proves loops/receipts/judge-routing.
Worked here, in order; skipped nothing proven.

- 51 BOLO + false-positive purge: PROVEN across two runs (one
  system never both builds and purges the same incident —
  purge only fires on false-positive close, BOLO only on
  dispatch; recorded as designed, not a gap).
  BOLO: medicus incident-725c546b990dd1b4 `bolo` step
  (Manhattan, cam-c, person on ground).
  Purge: cleared run `evidence-purged` step
  (files_removed 1, reason closed-false-positive).
- 52 cleared path: PROVEN. Scripted flag -> baseline review ->
  `closed-false-positive`, timeline
  flag,decision,review,decision,evidence-purged.
- 53 inconclusive path: PROVEN. Review FAILED ->
  `flagged-unconfirmed`, status monitoring, verdict
  inconclusive ("review reading failed... judge does not
  confirm on a missing reading"). No dispatch, no spend.
- 54 budget governor: UNPROVEN. Stop rule exists
  (orchestrator STOP_CONDITIONS max_cost_usd 0.50) but $0-spend
  staged runs cannot reach a dollar cap; reaching it needs
  ~125 live judge calls (~$0.50) — flagged for spend approval,
  not attempted.
- 55 budget kill drill: same as 54 — UNPROVEN, same reason.
- 56 STOP file drill: NOT APPLICABLE on this tree. No STOP-file
  mechanism exists in server/queue (only face updater's
  /etc/metaos/STOP, a different system). Nothing to drill.
- 57 supervisor restart: NOT APPLICABLE. supervisor.py is an
  incident-pattern supervisor (pauses feeds), not a process
  supervisor; no hosted-service restart path exists on this
  tree (Buffy Round 11 scope).
- 58 Goose smoke: BLOCKED on toolchain — services/ are 54
  spec dirs (.goose + README), no runner on this Mac. Status
  strings cited instead (e.g. board RUNS per its README).
- 59 ledger audit: agents/gym-ledger.jsonl has 4 entries, ALL
  LACK brief/outcome/receipt fields (schema is
  drill/event/max/run/score/task/ts). Finding: ledger does not
  meet the task's per-run shape — named, not fixed.
- 60 verdicts: this file. Gaps that stay open: 54/55 (spend
  approval), 56/57 (no mechanism on tree), 58 (no runner),
  59 (schema mismatch).
