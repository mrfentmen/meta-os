# Round 3 running report (Mac side)

## Section A — Close round 2 properly (NC-001..NC-012) — DONE

- NC-001: oc-proofs/ROUND2_GAPS.md written (G endurance + I sweep: what each
  was to prove, replacements K and Q).
- NC-002: review tests re-run on this branch: 2/2 pass.
- NC-003: molecules + music3d validation re-run: 6/6 and 3/3 pass.
  Combined labs total: 11/11.
- NC-004: all 7 footage files present, byte sizes tabled (636149, 511369,
  1380909, 200377, 563149, 378359, 1802947).
- NC-005: ffprobe durations match the index exactly (20/20/20/10/15/10/30 s).
- NC-006: verification re-run from pushed code: analytic 181.659 W/m at
  h=55.8; sim 180.139 (0.84%) and 180.916 (0.41%); balance 2e-3 both.
  Matches RUNG3_CLOSEOUT.md.
- NC-007: champion coarse case re-run 3x: byte-identical
  (183.545700 W/m, 9966 iters) — matches round-2 claim.
- NC-008: proof-artifact audit: every labs/oc-proofs path cited in the
  round-1/2 reports exists on disk. Zero offenders. (Soak log still
  growing; excluded from the audit until Section K closes it.)
- NC-009: oc-proofs/BASELINES.md written (node 1999/1943/56 exact,
  cargo 1412/0, custos 48/48, officina 49/49, queue-throwaway 110/110).
- NC-010: files over 10 MB (excluding .git/target/node_modules): exactly
  one, the Swift build cache ModuleCache .swiftmodule (untracked build
  output, expected). All film clips under 2 MB each.
- NC-011: status at section start was NOT clean: OPENCODE_TASKS_100_REPORT.md
  modified (in-progress Section G notes), plus untracked soak artifacts
  (soak-mem.log, nb-076-concurrency.txt) and target/ build output.
  Reason: endurance work in flight; committed at section boundaries only.
- NC-012: this summary.
