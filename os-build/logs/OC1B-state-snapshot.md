# OC1B-459/460/461/472 — submission-day state snapshot (DRAFT)

With Milo: rows Milo owns are marked MILO-OWNED with the source named; this
lane filled only what its own runs prove. Converts the FREEZE_CERT shape into
a snapshot — Del's no-freeze ruling stands (this is a state record, not a
freeze).

## Snapshot facts (OC1B-459; this lane's runs only)

- Lane tree: 94010c76 (opencode/500-s17 worktree of opencode/500 tip).
- Node suite (this lane, OC1B-401): 2071 run / 2015 pass / 56 fail.
- Queue suite (this lane, OC1B-490): 296 tests, OK, 4.2s.
- Closeout gate.sh (OC1B-488): RUNNING at snapshot time — result appended
  when the run completes; lineage row below marked accordingly.
- Final tip hash / gate result at SUBMIT time: MILO-OWNED (Pax assembles the
  final combined tree after merge waves; this lane's tree is not that tree).

## Claim-clause map (OC1B-460; sentence from FREEZE_CERT, Del-adopted 2026-11-01)

| Clause | Verdict | Committed log path |
|---|---|---|
| Boots on x86_64 in QEMU | UNPROVEN in this lane | gate run owned by §1/§8 lanes; this lane's closeout gate (OC1B-488) pending at snapshot time |
| Drops to ring 3 | UNPROVEN in this lane | same as above |
| Runs three userspace programs | UNPROVEN in this lane | same as above |
| Isolates a fault to one task | UNPROVEN in this lane | same as above |
| Shell reports the machine's real state | UNPROVEN in this lane | same as above |
| Reproduced from a clean checkout by one command | UNPROVEN in this lane | clean-clone rehearsal BLOCKED (OC1B-465, runbook missing) |
| Every claim backed by a committed boot log | UNPROVEN in this lane | boot-log evidence owned by §1/§7/§8 lanes |

## UNPROVEN reasons, one line each (OC1B-461)

- Kernel-clause rows: this lane ran no kernel boot (gate.sh was still
  running at snapshot time; kernel gates belong to §1/§5/§6/§8) — a lane
  outside its evidence must not mark kernel clauses PROVEN.
- Clean-checkout row: §11's runbook path does not exist, so no honest
  rehearsal could run in this lane.
- Boot-log row: committed-log coverage is tallied by the lanes that own the
  boots.

## Gate lineage (OC1B-472)

Last kernel word in this lane: OC1B-488 gate.sh run on 94010c76 (result to
be appended to os-build/logs/OC1B-closeout-gate.log). Submission stands on
the LAST §8 re-proof wave + §1 baseline lineage — owned by the coordinator/
Pax at merge time, not by this lane. This snapshot records the lane's own
state only and must not be cited as the submission's gate.

## Coordinator addendum 2026-11-02 (OC1B-459/460/472 upgrades; lanes merged)

- OC1B-488 result: GREEN (s17 lane report + os-build/logs/OC1B-closeout-gate.log on the merged tree). The "RUNNING" note above is superseded.
- OC1B-472 gate lineage (submission stands on this): §1 baseline @main-3452d244 GREEN 8/8 twice, panic 0 (OC1B-baseline-gate.log, OC1B-baseline-gate2.log); §8 combined-tip @94010c76 GREEN 8/8, serial 1086 lines panic 0 (OC1B-reproof-combined-gate.log); §17 closeout gate GREEN same tree (OC1B-closeout-gate.log); §11 film serials K1/K2 panic 0 (oc1b-beat1-serial.txt, OC1B-demo-beat5-serial.txt).
- OC1B-460 clause upgrades (coordinator, evidence merged): Boots/ring-3/three-programs/fault-isolation/shell-state → PROVEN via §1 + §8 logs above. Boot-log coverage → PROVEN (§1/§7/§8 committed serials). Clean-checkout → PENDING rehearsal (runbook exists, background run in flight, result to be appended).
- OC1B-461: kernel-clause reason retired (evidence now merged); clean-checkout reason updates when rehearsal lands.
