# NATIVE decision pack — refreshed with per-group Mac evidence (OC1B-419)

Branch worktree: opencode/500-s17 @ 94010c76 (opencode/500 tip, 2026-11-02).
amac. No test or Swift file changed in this lane
(`git diff --stat -- tests/ native/` empty — OC1B-native-pack.md OC1B-421).
Decision (UPDATE vs CARVE-OUT) is Del's; execution is a separate Pax-assigned
job. This pack is evidence only. (Still-waiting line for OC1B-424: no ruling
had arrived at pack-assembly time; §17 stops at evidence per the task.)

## Settled count: 56 (OC1B-native-baseline.txt, OC1B-native-failures.txt)

Full `npm test`: 2071 tests, 2015 pass, 56 fail, 3.4s wall.
- 31 whole-file failures (Swift slice throws at load).
- 24 named native-mirror failures (stale SwiftUI assertions).
- 1 newcomer: R11-282 boot-log index drift (fails on main too — verified on a
  clean origin/main worktree @3452d244; missing name differs by branch).
README's "55" and wave-3's "55" describe the native-mirror set only (correct
after Pax's logo-color removal 5df78e5f); the suite count on this tree is 56
with the newcomer. Reconciliation in OC1B-native-baseline.txt (OC1B-403);
newcomer reported in OC1B-404.

## Per-group Mac evidence (OC1B-native-g1..g7.txt, OC1B-native-supp.txt)

| Group | Files | Tests | Pass | Fail | Failing shape |
|-------|-------|-------|------|------|---------------|
| G1 ignis-assessment-* (21 files) | 21 | 83 | 83 | 0 | green — no work |
| G2 header + ignis-header | 6 | 6 | 0 | 6 | all whole-file |
| G3 ops-console | 9 | 31 | 20 | 11 | 6 whole-file + 5 named |
| G4 settings/statusbar/footer | 6 | 6 | 0 | 6 | all whole-file |
| G5 camera + capture | 7 | 20 | 13 | 7* | 3 whole-file + 3 named + 1 out-of-suite |
| G6 timeline/latest/still-image/video | 11 | 28 | 23 | 5 | all whole-file |
| G7 logo/input/interval/request/sampler/stepper + 10 leftovers | 21 | 78 | 69 | 9 | 5 whole-file + 4 named |
| SUPP non-native hosts (8 files) | 8 | 150 | 137 | 13 | 12 named + R11-282 |

\* G5's 7th is tests/native-camera-live-tracking.test.mjs, which is NOT in
the npm test script (verified absent from package.json) — it fails standalone
on the removed Label("CAMERA LIVE") but is not one of the 56. Sum check:
0+6+11+6+(7-1)+5+9+13 = 56 — every baseline failure in exactly one group run
(OC1B-native-groups.md OC1B-414).

Per-file counts: OC1B-405. Per-surface (removed-SwiftUI) counts: OC1B-406 —
44 deleted-ContentView panels/states + 5 PanelHeading-composition + 6 deleted
AssessmentView treatments + 1 docs-index newcomer.

## Options, costed from the group runs (OC1B-415/416/417)

- UPDATE (38 failure-units: 30 whole-file + 8 named): strip the dead Swift
  slice/tail in each, keep the live web check (all live contracts verified
  still matching in OC1B-415; one web regex widening at ui:872 for the added
  `frameImage` param). Touches test files only, ~36 files. Re-verify cost:
  full suite 3.4s.
- CARVE-OUT (17 failure-units: 1 whole file + 16 named): delete assertions
  with no live counterpart (header-limitations-corners file + 16 named tests
  across 10 files). Loses only SwiftUI-structure coverage with no live
  target; every live contract stays covered by passing web tests (per-file
  loss table in OC1B-416).
- R11-282 is outside both: one-line docs-index update (name the new *.txt
  logs in os-build/layer1/BOOTLOG_INDEX.md), not performed in this lane.

## Classification agreement (OC1B-418)

Agree with docs/NATIVE_TEST_PREP.md on all 55 native-mirror failures except
four noted adjustments: (1) PREP entry 46 (logo) no longer exists — removed
by 5df78e5f; (2) R11-282 postdates PREP — classified here; (3) ui:872 scope
is one regex wider; (4) live-tracking is out-of-suite, UPDATE-class if added.
Adjusted totals: UPDATE 38 / CARVE-OUT 17 over 55 + 1 docs newcomer.

## Regression screen (OC1B-422): NONE

No failing test asserts behaviour the WKWebView app still ships; web-side
assertions preceding each failing line pass. No live-app regression hiding.

## One-line summary (OC1B-420 proposed status line)

`NATIVE-55(+1): settled 56 = 55 native-mirror (31 file + 24 named, groups
G1-G7+SUPP all run, sum closes) + 1 newcomer R11-282 index drift; UPDATE 38 /
CARVE-OUT 17 costed with per-group Mac evidence; no hidden regression;
awaiting Del's tap — no execution in this lane.`

Proof paths: os-build/logs/OC1B-native-baseline.txt,
os-build/logs/OC1B-native-failures.txt, os-build/logs/OC1B-native-groups.md,
os-build/logs/OC1B-native-g1.txt … g7.txt, os-build/logs/OC1B-native-supp.txt,
os-build/logs/OC1B-native-pack.md, os-build/NATIVE_55_DECISION_PACK.md (this file).
