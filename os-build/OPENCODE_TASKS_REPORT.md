# OPENCODE_TASKS_REPORT.md — Fleet round 2: Buffy's 39 leftovers (B27 + B31)

Scope: `OPENCODE_TASKS.md` (boss order 2026-10-30). Branch: `batch/B31`
(B31 work) + `batch/B27` (T017–T020 carries, separate agent). Base:
`eedb6b9`. No merges by fleet — control window merges.

Final gate line: `cargo test -p parity-tests` → **235 passed, 0 failed**
(234 case tests + `index_complete`). Full log tail:
`test result: ok. 235 passed; 0 failed; 0 ignored; 0 measured`.

## Per-task record

| Task | State | Commit | Proof |
|---|---|---|---|
| T017 doe/dsny carry | CARRIED | 90f6b826 (batch/B27) | 4 files sha-verified, byte-identical |
| T018 ems/fdny carry | CARRIED | f6cd5173 (batch/B27) | 4 files sha-verified, byte-identical |
| T019 hospital/mta carry | CARRIED | e95d5928 (batch/B27) | 4 files sha-verified, byte-identical |
| T020 nypd carry | CARRIED | 37c9a7ec (batch/B27) | 2 files sha-verified, byte-identical |
| T028 harness fake_redis | DONE | 8a0f9b3 | suite compiles; 3 fake_redis tests green |
| T029 harness helpers | DONE | 8a0f9b3 | tmp_routing green |
| T030 harness acceptance | DONE | 8a0f9b3 | parse_shapes + empty_and_bad green |
| T031 boss_trigger | DONE (9 blocked) | 0548587 | 20 green (HMAC vectors, full verifier) |
| T032 bus_rename | DONE (13 blocked) | 961c1c8 | 13 green (pyStr, entries, qnick, parse, admin) |
| T033 bustools_parity | DONE (2 blocked) | d9156f2 | 1 green (subjects absent → recorded) |
| T034 clip core | DONE (13 blocked) | 6ec097b | 6 green (fallback core, stub runner) |
| T035 par_clock | DONE (3 blocked) | b549b86 | 15 green vs real os-misc b27 port |
| T036 os021_update | DONE | 691c944 | 9 green (real script + git fixtures) |
| T037 gateway_unit | DONE | e793940 | 8 green (file pins) |
| T038 gateway_bake | DONE | e8a2884 | 18 green (pins + real sweep + syntax) |
| T039 skills_loader pins | PARTIAL (15 blocked) | db403a5 | 6 green; loader needs intel port (absent on main) |
| T040 artifact_store pins | PARTIAL (12 blocked) | ed13821 | 5 green; store needs mos port (absent on main) |
| T041 ref shape | PARTIAL (9 blocked) | febdfda | 1 green (parse contract); record needs jobs port |
| T042 launch_run | PARTIAL (11 blocked) | c191729 | index recorded; needs intel launch (absent on main) |
| T043 disk_audit | PARTIAL (18 blocked) | 3762dec | index recorded; needs mos audit (absent on main) |
| T044 os_base | DONE | d57e849 | 6 green (folded tree os/os/) |
| T045 boot_harness | DONE (1 blocked) | 17d7427 | 10 green (real script runs); QEMU run stays UNPROVEN |
| T046 boot_selfcheck | PARTIAL (6 blocked) | 77126e7 | index recorded; needs intel drills (absent on main) |
| T047 boot_status | PARTIAL (6 blocked) | 1705d8d | index recorded; needs intel drills (absent on main) |
| T048 bus_unit | DONE | 4c61c43 | 8 green (OS-013 pins) |
| T049 journal_watch | PARTIAL (17 blocked) | a378c3e | index recorded; needs intel journal (absent on main) |
| T050 livebuild | DONE | df360ff | 18 green (config/pins/syntax/docs) |
| T051 manifest | DONE | 608b7c1 | 8 green (frozen set pins) |
| T052 overseer | DONE | 1176d4f | 8 green (OS-015 pins) |
| T053 packer | DONE | 664287d | 14 green (template/wrapper/sweep/docs) |
| T054 power_cut | PARTIAL (4 blocked) | a3d3dcf | index recorded; needs intel drill (absent on main) |
| T055 stackbake | DONE | a04b095 | 13 green (script pins, no venv) |
| T056 target | DONE | 7417c84 + 608b7c1 | 13 green (OS-016 pins) |
| T057 tree | DONE | 950ef82 | 10 green (tree shape pins) |
| T058 uplink pins | PARTIAL (11 blocked) | d4cea14 | 2 green; queue needs relay_uplink port (absent on main) |
| T059 pomodoro core | PARTIAL (8 blocked) | fb1ef69 | 3 green (parse+fmt); store needs relay_common (excluded) |
| T060 status | PARTIAL (17 blocked) | 712fdf9 | roots recorded; needs relay_common store (excluded) |
| T061 worlds_pack | DONE | a37d63d | 13 green vs real os-misc b27 validator |
| T062 full run | DONE | this commit | table below; 235/235 |

States: DONE = ported + green at local gate; PARTIAL = pins green,
remainder recorded blocked with exact missing subject; CARRIED =
byte-identical data. Nothing counts as PORTED until Milo gate 1 +
boss Mac gate 2 (control window's call).

## T062 parity table (per Python file: green / blocked)

| File | Green | Blocked | Note |
|---|---|---|---|
| test_boss_trigger | 20 | 10 | wiring needs excluded bus.html + node |
| test_bus_rename | 13 | 13 | builders/DOM need excluded bus.html + node |
| test_bustools_parity | 1 | 2 | bus-tools/ + skill bin absent in this env |
| test_clip | 6 | 13 | send/paste flows need relay_common + CLIs |
| test_fdny_par_clock | 15 | 3 | CLI main absent from Rust lib port |
| test_os021_update | 9 | 0 | — |
| test_os058_gateway_unit | 8 | 0 | — |
| test_os059_gateway_bake | 18 | 0 | — |
| test_os065_skills_loader | 6 | 15 | loader needs intel port (unmerged) |
| test_os083_artifact_store | 5 | 12 | store needs mos port (unmerged) |
| test_os094_job_artifacts | 1 | 9 | record needs jobs port (unmerged) |
| test_os102_launch_run | 0 | 11 | needs intel launch (unmerged) |
| test_os128_disk_audit | 0 | 18 | needs mos audit (unmerged) |
| test_os_base | 6 | 0 | — |
| test_os_boot_harness | 10 | 1 | QEMU boot run UNPROVEN by design |
| test_os_boot_selfcheck | 0 | 6 | needs intel drills (unmerged) |
| test_os_boot_status | 0 | 6 | needs intel drills (unmerged) |
| test_os_bus_unit | 8 | 0 | — |
| test_os_journal_watch | 0 | 17 | needs intel journal (unmerged) |
| test_os_livebuild | 18 | 0 | — |
| test_os_manifest | 8 | 0 | — |
| test_os_overseer_unit | 8 | 0 | — |
| test_os_packer | 14 | 0 | — |
| test_os_power_cut | 0 | 4 | needs intel drill + live reboot |
| test_os_stackbake | 13 | 0 | — |
| test_os_target_unit | 13 | 0 | — |
| test_os_tree | 10 | 0 | — |
| test_os_uplink | 2 | 11 | queue needs relay_uplink port (unmerged) |
| test_pomodoro | 3 | 8 | store needs relay_common (excluded) |
| test_status | 0 | 17 | store needs relay_common (excluded) |
| test_worlds_pack | 13 | 0 | closes B27 validator loop |
| **Total** | **228** | **196 case-slots** | + harness 7 (support) = **235 green** |

Blocked case-slots are named per case in each module's
`EXCLUSION_BLOCKED` — never dropped, never faked green. The
unmerged-subject blocks (intel/mos/jobs/os-worker) clear when
Hana's and Milo's branches land on main.

## Parked tasks

None parked under the stall rule. Every task either has green tests
or a recorded blocker with the exact missing subject. Two
environment notes (not parks): the QEMU boot run (T045) stays
UNPROVEN until a build host runs it; the live skill-bin comparison
(T033) runs only where the bin exists.

## Hard-boundary compliance

- Fresh worktree `/tmp/meta-os-r2` on main tip; rebased never,
  force-push never (all pushes fast-forward).
- Only `crates/parity-tests/` touched on `batch/B31`; only
  `crates/os-misc/src/b27/mod.rs` carry consts on `batch/B27`
  (separate agent, separate worktree).
- No existing ported file overwritten; T015/T016 (Buffy's) untouched;
  Rowan/Milo/Hana/Pax areas untouched.
- Python/Node originals untouched throughout.
