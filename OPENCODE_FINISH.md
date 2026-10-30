# OPENCODE_FINISH — fleet finish run for the Rust rebuild

Boss order 2026-10-30: the OpenCode fleet finishes the rebuild.
Read this file completely before starting. SUPER_PROMPT.md and
TASKS.md still govern task definitions; batches/B07-report-wave1.md
(on branch batch/B07) is the integration map.

## What is already done (do not redo)

- B27: T017-T020 CARRIED, branch batch/B27 tip 37c9a7e.
- B31: full run filed, branch batch/B31 tip f28e7302,
  OPENCODE_TASKS_REPORT.md on that branch (235 green claimed locally;
  partials are blocked on unmerged subjects, named per case).
- B07 wave 1: branch batch/B07 tip 5d7ec68 — workspace build PASS,
  86/86 tests excluding parity-tests, gate-1 GREEN by Milo.
- Milo's sections B16-B23: gate-1 PASS, landing branches are the
  `batch/B##-milo` branches (NOT the plain batch/B## ones).
- Hana's sections B08-B15: gate-1 PASS on her branches
  (B15 tip ed93561 is the latest; B10 needs the b09_core union below).
- Pax B12a: fixes for the 6 gate-1 errors pushed at 34a37c46 on
  batch/B12a, gate-1 recheck pending with Milo. B12b/B12c carries are
  on batch/B12b (707ba36a) and batch/B12c (36daf0c3).

## The job, in order

Work on ONE integration branch: create `finish/integration` off
current main. One agent merges at a time — merges are serial, never
parallel. Build and test after every merge; a red merge gets fixed
or backed out before the next one starts.

1. Merge the section branches into finish/integration, in this
   order: batch/B27, batch/B31, Hana's B08-B15 branches, the
   batch/B##-milo branches (B16-B23), batch/B12b, batch/B12c,
   batch/B12a (only after its gate-1 pass, or compile it locally
   yourself first and say which), then batch/B07.
2. Union wiring at merge time (known seams):
   - intel lib.rs: B09 wires b09_core, B11 wires b11_spark — the
     merged lib.rs needs BOTH (B10's gate-1 red is exactly this).
   - parity-tests: os-misc must be a real dependency, not only a
     dev-dependency (the E0433 from gate 1).
   - parity-tests fake_redis `lrem_semantics` stack overflow
     (infinite recursion) — triaged to B31, yours to fix. Rowan's
     one-line seam fix for the E0119 Default conflict is on
     batch/B07; keep whichever version compiles, say which.
3. Close the two reviewed quality gaps (Rowan's review, still open):
   - B05 assess-server: main() only prints — implement the real
     HTTP serve loop, queue poll, and 502-on-invalid-answer path
     per the Python original (os/ tree is the spec).
   - B04 agent-runtime: validate_stub is category-only — restore
     the full ok-gating of the Python original.
4. Finish the remaining B07 integration tasks (T246-T259 in
   SUPER_PROMPT.md) that the merges unblock, wave by wave.
5. Run Pax's T217: the B12a parity run against the Python drills.
6. Final verification on this machine (you compile locally — that
   is the point of this run): `cargo build --workspace` clean and
   `cargo test --workspace` with exact pass/fail counts, plus the
   parity-tests suite. No task is done until it compiles and its
   tests pass here.

## Landing rule

- If the FULL workspace build and test run is green on
  finish/integration: merge finish/integration into main, push,
  and say so in the report.
- If anything is still red: do NOT touch main. Leave the branch,
  file the report, name every remaining failure exactly.

## Boundaries

- Merges and seam fixes only in scope above. Never overwrite,
  delete, or "improve" a ported file that a section owner landed;
  if a merge conflict touches ported code, resolve by union, and
  if you cannot, STOP on that merge and report it.
- Carried files stay byte-identical (verify by hash after merge).
- Do not touch: the Trio app (native/), the image lane, B01-B06
  ports beyond the B04/B05 gap fixes named above.
- Stall rule: same error class 3 rounds = park it, write the
  blocker into the report, move on.
- Honest states only: DONE / PARTIAL / exclusion-blocked (named).
  Never fake a green.
- Commit per merge step: `FINISH: merge <branch> - <state>`.

## Finish line

Write OPENCODE_FINISH_REPORT.md on finish/integration (and on main
if you land it): per-merge state + commit SHAs, the B04/B05 gap
closures, B07 task states, T217 result, final build/test counts
verbatim, and every parked item with its blocker. Then stop.
