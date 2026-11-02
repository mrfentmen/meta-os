# OC1B-492/495/496/498/499 — handoff to Pax

Branch: opencode/500-s17 @ 94010c76 base (opencode/500 tip at lane start;
opencode/500 has since advanced — coordinator decides rebase/merge).
Lane: OpenCode 1's closer, Mac, darwin arm64. kernel/src untouched; no
face/web work; no main push.

## Ready to merge (Pax's call, in this order)
1. §17 decision-pack set (OC1B-native-*.txt/.md + NATIVE_55_DECISION_PACK.md):
   evidence only, no test/source changes — safe any time.
2. §19 prep set (OC1B-submission-*, OC1B-state-snapshot.md): drafts and
   scans, no behavior change — safe any time.
3. §20 closeout set (OC1B-gate-ledger/proof-index/unimplemented/unproven/
   closeout-*/demo-inventory/handoff + snippet): record only.

## Must NOT merge / does not exist
- No kernel/src change exists in this lane — nothing to hold back.
- The snippet file (OC1B-s17-STATUS-SNIPPET.md) is coordinator input, not
  status — do not treat it as the status file.
- Do not merge as "fixes": failing tests stay failing; R11-282 stays red.

## Merge order recommendation
§17 first (unblocks Del's tap), §19 second (prep accumulates), §20 last
(closeout records). All three are additive os-build/logs + one os-build/
markdown — no conflicts expected except the snippet (delete or keep at
coordinator's discretion after merging its content).

## OC1B-495 total lane spend: 0
No live model call ran in this lane (no SPARK_API_KEY use; no receipts).
Spend at Spark rates: $0.00. (Node/queue/gate runs are local compute.)

## OC1B-496 Mac-lane wall-clock by section (measured)
- §17 (baseline 3.4s + 8 group/supp runs ~2s + analysis + R11-282 main-tree
  verification + decision-pack writing): ~55 min elapsed (dominated by
  evidence analysis, not suite time).
- §19 (walk, scans, snapshot, timeline, attributions): ~25 min.
- §20 (gate.sh run ~6 min + final suites ~8s + sweeps + index): ~20 min.
Total lane time ≈ 100 min. Suite compute itself: <15 min (gate build+boot
dominates).

## OC1B-498 attestation
Nothing was posted to main and nothing to the bus from this lane. All commits
are on opencode/500-s17; pushes only to origin opencode/500-s17. Pax merges
and posts at the checkpoint. OBEYED.

## OC1B-499 spare time
No section finished early enough to matter (gate.sh ran while §20 files were
written — overlap, not spare time). The lane moved to the next unblocked
section throughout; never idle.
