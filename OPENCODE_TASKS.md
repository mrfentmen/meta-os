# OPENCODE_TASKS.md — Fleet round 2: finish Buffy's leftovers (39 tasks)

**By the boss's direct order (Del / Mrfentmen, 2026-10-30 ~07:25 EDT): the
OpenCode fleet finishes the work Buffy did not finish.** Milo's section
(B16–B23) and Hana's section (B08–B15) are DONE at gate 1. Rowan is finishing
his own section. Your scope is ONLY the 39 tasks below — nothing else.

This file supersedes the fleet scope in `OPENCODE_PROMPT.md`.
Task text is quoted verbatim from `SUPER_PROMPT.md`; the T-ids are
authoritative there. Batch specs: `batches/B27.md`, `batches/B31.md`.
Port behavior, never redesign. The Python originals are the spec and stay
untouched.

## Already done — do not redo, do not touch

- T014, T015, T016 (B27) — DONE, landed on main (validator port c8b2a325,
  par_clock + T016 verify-carried 4c77a60e).
- Buffy's landed work stands: B24 4d6b2107, B25 2d92895b, B26 83f923bd,
  B28 2daef26a, B29 539dbb9f, B30 0015c244, B31 harness 791fda8d.

## HARD BOUNDARIES (an overwrite already happened once — this is the fix)

1. Work in a fresh worktree based on the current main tip. If main moves
   under you, rebase before pushing — never force-push.
2. You may only create or edit files under `crates/parity-tests/` and the
   B27 carry record for T017–T020. Every other path is read-only to you.
3. NEVER overwrite, delete, or "improve" an existing ported file. If a file
   your task needs already exists, STOP on that task and report it.
4. Do not touch: B01–B07 (Rowan), B08–B15 (Hana, done), B16–B23 (Milo,
   done — his `batch/B##-milo` branches are the landing candidates),
   B12a/B12b/B12c (Pax), B24–B26/B28–B30 (Buffy, landed).
5. Claim before coding: push branch `batch/B31` before B31 work and
   `batch/B27` before B27 work. One task, one agent. Commit per task,
   message format: `T### [B##] <what> — <state>`.
6. `opencode run --auto`, stdin closed (`< /dev/null`), stagger agent
   starts 30–60s apart (shared sqlite lock).
7. You can compile locally — use it. Every task ends compiled and tested
   by you, or it is not done.
8. Stall rule: same error class 3 rounds = park the task, write the
   blocker into your report, move to the next task.
9. Honest states only: DONE / PARTIAL / exclusion-blocked (named, never
   dropped, never faked green). Carried files are byte-identical —
   verify by hash, never edit them.

## Order of work

1. **FIRST: T028–T030.** The B31 harness exists (791fda8d) but is RED at
   gate 1: E0119, conflicting `Default` impls for `FakeUpstash`. Fix the
   existing harness — do not rewrite it — until
   `cargo test -p parity-tests` compiles and runs.
2. **THEN: T031–T061, in id order, one at a time.** Port each Python test
   file against the already-ported modules. A case that needs the
   excluded `relay_common`/viewer code is recorded exclusion-blocked
   with its name — never dropped.
   Note: T035's subject (par_clock) and T061's subject (the B27
   validator) are both landed on main, so both are runnable.
3. **IN PARALLEL (separate agent/worktree is fine): T017–T020.**
   Verify-carried only: hash every named file against its source under
   `os/worlds/` and record the group CARRIED with the hashes.
4. **LAST: T062.** Full parity run + the per-batch parity table with
   real counts.

## The tasks (verbatim from SUPER_PROMPT.md)

- T017 [B27] Verify-carried `os/worlds/doe/PACK.md`, `os/worlds/doe/pack.json`, `os/worlds/dsny/PACK.md`, `os/worlds/dsny/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED
- T018 [B27] Verify-carried `os/worlds/ems/PACK.md`, `os/worlds/ems/pack.json`, `os/worlds/fdny/PACK.md`, `os/worlds/fdny/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED
- T019 [B27] Verify-carried `os/worlds/hospital/PACK.md`, `os/worlds/hospital/pack.json`, `os/worlds/mta/PACK.md`, `os/worlds/mta/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED
- T020 [B27] Verify-carried `os/worlds/nypd/PACK.md`, `os/worlds/nypd/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED
- T028 [B31] Port harness file `os/tests/fake_redis.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes
- T029 [B31] Port harness file `os/tests/helpers.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes
- T030 [B31] Port harness file `os/mos/acceptance.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes
- T031 [B31] Port test file(s) `os/tests/test_boss_trigger.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T032 [B31] Port test file(s) `os/tests/test_bus_rename.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T033 [B31] Port test file(s) `os/tests/test_bustools_parity.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T034 [B31] Port test file(s) `os/tests/test_clip.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T035 [B31] Port test file(s) `os/tests/test_fdny_par_clock.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T036 [B31] Port test file(s) `os/tests/test_os021_update.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T037 [B31] Port test file(s) `os/tests/test_os058_gateway_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T038 [B31] Port test file(s) `os/tests/test_os059_gateway_bake.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T039 [B31] Port test file(s) `os/tests/test_os065_skills_loader.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T040 [B31] Port test file(s) `os/tests/test_os083_artifact_store.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T041 [B31] Port test file(s) `os/tests/test_os094_job_artifacts.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T042 [B31] Port test file(s) `os/tests/test_os102_launch_run.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T043 [B31] Port test file(s) `os/tests/test_os128_disk_audit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T044 [B31] Port test file(s) `os/tests/test_os_base.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T045 [B31] Port test file(s) `os/tests/test_os_boot_harness.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T046 [B31] Port test file(s) `os/tests/test_os_boot_selfcheck.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T047 [B31] Port test file(s) `os/tests/test_os_boot_status.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T048 [B31] Port test file(s) `os/tests/test_os_bus_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T049 [B31] Port test file(s) `os/tests/test_os_journal_watch.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T050 [B31] Port test file(s) `os/tests/test_os_livebuild.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T051 [B31] Port test file(s) `os/tests/test_os_manifest.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T052 [B31] Port test file(s) `os/tests/test_os_overseer_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T053 [B31] Port test file(s) `os/tests/test_os_packer.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T054 [B31] Port test file(s) `os/tests/test_os_power_cut.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T055 [B31] Port test file(s) `os/tests/test_os_stackbake.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T056 [B31] Port test file(s) `os/tests/test_os_target_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T057 [B31] Port test file(s) `os/tests/test_os_tree.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T058 [B31] Port test file(s) `os/tests/test_os_uplink.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T059 [B31] Port test file(s) `os/tests/test_pomodoro.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T060 [B31] Port test file(s) `os/tests/test_status.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T061 [B31] Port test file(s) `os/tests/test_worlds_pack.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked
- T062 [B31] Run the full parity suite in `crates/parity-tests` and produce the per-batch parity table — done when: every ported case is reported pass/fail and every case needing the excluded `relay_common`/viewer code is named exclusion-blocked, none dropped


## Finish report (required)

When the list is drained, post a report file `OPENCODE_TASKS_REPORT.md`
in your branch (do not merge it yourself) and stop. It must contain:

- Per task: T-id, state (DONE / PARTIAL / exclusion-blocked), commit SHA,
  and the `cargo test -p parity-tests` line that proves it.
- The T062 parity table: per-batch pass / fail / exclusion-blocked
  counts, exactly as the test run printed them.
- Every parked task with its blocker, in plain words.

Merges to main are done from the control window, not by the fleet.
