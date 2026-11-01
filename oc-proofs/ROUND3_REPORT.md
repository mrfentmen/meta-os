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

## Section B — Queue suite on the Mac, endgame (NC-013..NC-024) — DONE

- NC-013: v3 patch in oc-proofs/queue-mac-optional-import.diff (unapplied).
- NC-014: throwaway of origin/main: pytest 110/110; unittest 110 OK.
- NC-015: stub-module run 110/110 — and it caught a real v2 bug (NameError
  on the importable-module path); v3 fixes it, all three legs green.
- NC-016/017: queue-sparkgen-optional-path.diff (conditional PYTHONPATH);
  throwaway with both diffs: 110/110 with and without stub.
- NC-018/019: table in queue-fix-final.md — 2 fixed, rest harmless/clean.
- NC-020: oc-proofs/queue-fix-final.md with apply order + proofs.
- NC-021: the 4 collection-error modules (test_queue, test_crew,
  test_evidence, test_supervisor) all collect and run under the fix.
- NC-022: node v24.21.0, python3 3.9.6, pytest 8.4.2 (in final doc).
- NC-023: throwaway-r3 removed (worktree list verified clean); scratch
  diff trees and stub module deleted.
- NC-024: this summary.

## Section C — Hortus rung 4, preparation only (NC-025..NC-036) — DONE

- NC-025/026/027/028: hortus-rung3/RUNG4_PROTOCOL.md — unit under test,
  parts (specs only), CSV log template with marked EXAMPLE row, pass/fail
  rule with the threshold left BLANK for the boss.
- NC-029: nc-029-prediction-sheet.md — 489.7 / 734.2 / 1025.0 W at h=30 /
  55.9 / 100; k=167→712.6, k=237→814.0 W. Raw log kept.
- NC-030: uncertainty table in the protocol, all sizes measured (grid
  0.4%, stair-step 0.6%, k -3%/+11%, h bracketed, sensors stated).
- NC-031: COMMERCIAL_COMPARE_PLAN.md — plan only, no accounts/installs.
- NC-032/033: champion-fin.txt geometry export; fresh-parser re-read
  diffs IDENTICAL in the same run.
- NC-034: falsifiability paragraph in the protocol (either sign counts;
  profile-shape falsifier included).
- NC-035: h cross-check — protocol central 55.9 matches closeout primary;
  closeout's flat-50 was sensitivity-only and stays there. No mismatch.
- NC-036: this summary.

## Section D — Scientia cross-checks (NC-037..NC-048) — DONE (CSV tasks recorded not-run)

- NC-037 DONE. labs/delaney-xcheck/xcheck.py: Delaney-2004 equation from
  the paper (0.16 -0.63*cLogP -0.0062*MWT +0.066*RB -0.74*AP), from scratch.
  Gate code never read (doesn't exist in this checkout anyway).
- NC-038 DONE as a negative: no archived Delaney CSV anywhere (searched).
  NC-040 (run), NC-041 (compare vs gate 0.725/1.099/0.844), NC-042 (sha256
  check) recorded NOT-RUN, not skipped-silently. Runner + selftest + OLS +
  mol-audit below all proceed.
- NC-039 DONE. --selfcheck 5/5 (benzene hand-verified term by term;
  tolerance 0.05; worst |err| 0.005).
- NC-043/044 DONE. Live PubChem re-fetch of all 5 round-2 structures:
  atom/bond counts, element lists, formulas, weights ALL MATCH. Nothing
  stale on either side.
- NC-045 DONE. --ols mode, every output line labelled "NOT Delaney".
- NC-046 DONE. Edge contract (empty→ValueError, salts/charged compute
  with documented behavior); an empty-SMILES hole found by the contract
  itself and fixed in the runner. Node bridge test 2/2.
- NC-047 DONE. labs/delaney-xcheck/README.md with the gate-is-Milo's
  sentence first.
- NC-048: this summary.
