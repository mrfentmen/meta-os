# OPENCODE_PROMPT.md — Fleet takeover: B27 remainder + B31

**By the boss's direct order (Del, 2026-10-30): the OpenCode fleet takes over
the unfinished remainder of Buffy's section — B27 and B31.** This is the
fleet-note condition in TASKS.md § OpenCode: the fleet works a named
section's tasks on the boss's direct say. This file is that say, in writing.

**Buffy's landed work stands untouched — do not redo it, do not restyle it:**

- B24 `4d6b2107`, B25 `2d92895b`, B26 `83f923bd` — code ports, landed UNCOMPILED.
- B28 `2daef26a`, B29 `539dbb9f`, B30 `0015c244` — CARRIED.

**Source of truth.** Task text below is quoted verbatim from
`SUPER_PROMPT.md` (Buffy block) — the T-ids and wording are authoritative
there; this file adds the verified state of each task and the takeover
protocol. Binding contracts: the rust-port rules in
`docs/RUST_REBUILD_PLAN.md`, and the batch specs `batches/B27.md` and
`batches/B31.md`. Port behavior, never redesign: the Python/Node originals
are the spec, and the Python originals stay untouched.

## The work list

### B27 — World packs (`crates/os-misc`, `b27` subtree)

- T014 [B27] Port `os/worlds/validate_pack.py` into `crates/os-misc` — done when: the validator's behavior matches the source and the workspace build includes it; B27 closes PORTED only when its parity case `test_worlds_pack.py` passes under B31; state left: UNCOMPILED until gate 1 passes

→ **STATE: DONE — skip.** The validator port landed in commit `c8b2a325` (`crates/os-misc/src/b27/validate.rs`, +367 lines, plus `mod.rs` wiring) — marked UNCOMPILED, so it still owes gate 1 / gate 2 like everything else, but the port itself exists. Its parity case `test_worlds_pack.py` is task T061 below and is still OPEN.

- T015 [B27] Port `os/worlds/fdny/runtime/par_clock.py` into `crates/os-misc` — done when: behavior matches the source; its parity case `test_fdny_par_clock.py` lives in B31; state left: UNCOMPILED until gate 1 passes

→ **STATE: OPEN.** Not ported. `crates/os-misc/src/b27/` holds only `validate.rs`; no par_clock module exists at the tip. Port `os/worlds/fdny/runtime/par_clock.py` into the `b27` subtree of `crates/os-misc`. Its parity case is T035 below.

- T016 [B27] Verify-carried `os/worlds/README.md`, `os/worlds/dep/PACK.md`, `os/worlds/dep/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED

→ **STATE: OPEN.** Verify-carried: no B27 carry/verification record exists yet (contrast B28–B30, which landed as CARRIED commits). The originals stay in `os/worlds/`; inventory every file named in the task and verify each is byte-identical to its source, then record them CARRIED in the batch report. Carried means byte-identical — never edit a carried file.

- T017 [B27] Verify-carried `os/worlds/doe/PACK.md`, `os/worlds/doe/pack.json`, `os/worlds/dsny/PACK.md`, `os/worlds/dsny/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED

→ **STATE: OPEN.** Verify-carried: no B27 carry/verification record exists yet (contrast B28–B30, which landed as CARRIED commits). The originals stay in `os/worlds/`; inventory every file named in the task and verify each is byte-identical to its source, then record them CARRIED in the batch report. Carried means byte-identical — never edit a carried file.

- T018 [B27] Verify-carried `os/worlds/ems/PACK.md`, `os/worlds/ems/pack.json`, `os/worlds/fdny/PACK.md`, `os/worlds/fdny/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED

→ **STATE: OPEN.** Verify-carried: no B27 carry/verification record exists yet (contrast B28–B30, which landed as CARRIED commits). The originals stay in `os/worlds/`; inventory every file named in the task and verify each is byte-identical to its source, then record them CARRIED in the batch report. Carried means byte-identical — never edit a carried file.

- T019 [B27] Verify-carried `os/worlds/hospital/PACK.md`, `os/worlds/hospital/pack.json`, `os/worlds/mta/PACK.md`, `os/worlds/mta/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED

→ **STATE: OPEN.** Verify-carried: no B27 carry/verification record exists yet (contrast B28–B30, which landed as CARRIED commits). The originals stay in `os/worlds/`; inventory every file named in the task and verify each is byte-identical to its source, then record them CARRIED in the batch report. Carried means byte-identical — never edit a carried file.

- T020 [B27] Verify-carried `os/worlds/nypd/PACK.md`, `os/worlds/nypd/pack.json` (B27 world-pack data) — done when: every file is inventoried and byte-identical to its source; the batch report lists them CARRIED

→ **STATE: OPEN.** Verify-carried: no B27 carry/verification record exists yet (contrast B28–B30, which landed as CARRIED commits). The originals stay in `os/worlds/`; inventory every file named in the task and verify each is byte-identical to its source, then record them CARRIED in the batch report. Carried means byte-identical — never edit a carried file.

### B31 — Parity test harness (`crates/parity-tests`)

- T028 [B31] Port harness file `os/tests/fake_redis.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes

→ **STATE: PARTIAL.** The harness landed in commit `791fda8d` ("B31: parity test harness — UNCOMPILED"), but Milo's gate-1 sweep found `crates/parity-tests` RED with error E0119 — the harness does not compile yet. First job: fix the existing harness until it compiles at gate 1. Fix it; do not rewrite it.

- T029 [B31] Port harness file `os/tests/helpers.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes

→ **STATE: PARTIAL.** The harness landed in commit `791fda8d` ("B31: parity test harness — UNCOMPILED"), but Milo's gate-1 sweep found `crates/parity-tests` RED with error E0119 — the harness does not compile yet. First job: fix the existing harness until it compiles at gate 1. Fix it; do not rewrite it.

- T030 [B31] Port harness file `os/mos/acceptance.py` into `crates/parity-tests` as test-support code — done when: the harness compiles in the workspace build and the cases that use it can run; state left: UNCOMPILED until gate 1 passes

→ **STATE: PARTIAL.** The harness landed in commit `791fda8d` ("B31: parity test harness — UNCOMPILED"), but Milo's gate-1 sweep found `crates/parity-tests` RED with error E0119 — the harness does not compile yet. First job: fix the existing harness until it compiles at gate 1. Fix it; do not rewrite it.

- T031 [B31] Port test file(s) `os/tests/test_boss_trigger.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T032 [B31] Port test file(s) `os/tests/test_bus_rename.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T033 [B31] Port test file(s) `os/tests/test_bustools_parity.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T034 [B31] Port test file(s) `os/tests/test_clip.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T035 [B31] Port test file(s) `os/tests/test_fdny_par_clock.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T036 [B31] Port test file(s) `os/tests/test_os021_update.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T037 [B31] Port test file(s) `os/tests/test_os058_gateway_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T038 [B31] Port test file(s) `os/tests/test_os059_gateway_bake.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T039 [B31] Port test file(s) `os/tests/test_os065_skills_loader.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T040 [B31] Port test file(s) `os/tests/test_os083_artifact_store.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T041 [B31] Port test file(s) `os/tests/test_os094_job_artifacts.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T042 [B31] Port test file(s) `os/tests/test_os102_launch_run.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T043 [B31] Port test file(s) `os/tests/test_os128_disk_audit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T044 [B31] Port test file(s) `os/tests/test_os_base.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T045 [B31] Port test file(s) `os/tests/test_os_boot_harness.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T046 [B31] Port test file(s) `os/tests/test_os_boot_selfcheck.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T047 [B31] Port test file(s) `os/tests/test_os_boot_status.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T048 [B31] Port test file(s) `os/tests/test_os_bus_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T049 [B31] Port test file(s) `os/tests/test_os_journal_watch.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T050 [B31] Port test file(s) `os/tests/test_os_livebuild.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T051 [B31] Port test file(s) `os/tests/test_os_manifest.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T052 [B31] Port test file(s) `os/tests/test_os_overseer_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T053 [B31] Port test file(s) `os/tests/test_os_packer.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T054 [B31] Port test file(s) `os/tests/test_os_power_cut.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T055 [B31] Port test file(s) `os/tests/test_os_stackbake.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T056 [B31] Port test file(s) `os/tests/test_os_target_unit.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T057 [B31] Port test file(s) `os/tests/test_os_tree.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T058 [B31] Port test file(s) `os/tests/test_os_uplink.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T059 [B31] Port test file(s) `os/tests/test_pomodoro.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T060 [B31] Port test file(s) `os/tests/test_status.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T061 [B31] Port test file(s) `os/tests/test_worlds_pack.py` into `crates/parity-tests` tests (same name roots, same fixtures) — done when: `cargo test -p parity-tests` runs them green against the ported modules, or each failing case is recorded exclusion-blocked

→ **STATE: OPEN.** Not ported. Port it one by one; the Python suite is the bar. A failing case is recorded exclusion-blocked — never dropped, never fudged.

- T062 [B31] Run the full parity suite in `crates/parity-tests` and produce the per-batch parity table — done when: every ported case is reported pass/fail and every case needing the excluded `relay_common`/viewer code is named exclusion-blocked, none dropped

→ **STATE: OPEN.** Run the full parity suite and produce the per-batch parity table with the real numbers. Name every failure and every exclusion-blocked case. Never fudge a parity count.

## Protocol (fleet rules — TASKS.md § OpenCode + the plan)

1. **Claim before coding.** Push branch `batch/B27` or `batch/B31` before
   you write code, or post a `TAKE T###` line on the bus (room 1). First
   claim wins. One worktree per agent.
2. **`opencode run --auto`, stdin closed (`< /dev/null`), starts staggered
   30–60s apart** (the shared sqlite lock dies otherwise).
3. **If a branch is already claimed and moving, STOP and announce — never
   push onto it.** The B17 collision is the standing counterexample: the
   fleet pushed 6+ commits onto Milo's claimed, announced `batch/B17`,
   and his finished port had to land under a fresh branch name. Do not
   repeat that here.
4. **Report each finished task on the bus (room 1)** as one line:
   `T### done — <state>` (state per the TASKS.md legend: UNCOMPILED,
   GATE1, GATE2, PORTED, PARKED, CARRIED).
5. **Gates.** Gate 1 = Milo compiles it (his VM). Gate 2 = the boss's Mac
   — the final word. Nothing is PORTED until both gates pass.
6. **Never force-push.** Merges happen from the control window after
   build + test.
7. **Python/Node originals untouched.** They stay the fallback until each
   Rust port passes both gates and parity.

## Done criteria for the takeover

- Every B27 world-pack data file named in T016–T020 is present in the
  repo and verified carried (byte-identical, recorded CARRIED).
- T015 (`par_clock.py`) is ported into `crates/os-misc`.
- `crates/parity-tests` compiles clean at gate 1 (the E0119 harness
  failure is fixed, not rewritten).
- All 31 B31 cases (T031–T061) are ported.
- The full parity run (T062) is executed and reported with honest
  counts — passes, failures, and exclusion-blocked cases all named.
- Nothing above counts as PORTED until gate 1 (Milo) and gate 2 (Mac)
  both pass.
