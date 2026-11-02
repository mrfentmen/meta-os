# BOND — BOND_TASKS.md execution ledger (2026-11-02)

Source list: `os-build/BOND_TASKS.md` — **252 tasks, 20 sections**.
Base: `main` @ `6d8d54e` (pulled after the first reference base
`4bdf3ef`). Machine rules held: no workspace build, no QEMU, no
model work. Every crate was checked with a single-crate
`cargo test -p <name> -j1`, one at a time.

## Result

- **252 / 252 tasks delivered** — 8 record files per crate section,
  12 Python records, 8 kernel records, and the tests each task asks for.
- **2108 Rust tests pass, 0 fail** across 19 crates.
- **485 Python tests pass** in the suites this lane runs.
- **Kernel records:** `node --test tests/kernel-records.test.mjs` 7/7,
  and `python3 os-build/layer1/abi_check.py` reports the spec and
  dispatch agree.

## Per section

| Section | Tasks | Records | Test files | Crate test run |
|---|---|---:|---:|---|
| 1 crates/os-boot | B001–B012 | 8 | 3 | 59 passed, 0 failed |
| 2 crates/os-supervisor | B013–B024 | 8 | 3 | 426 passed, 0 failed |
| 3 crates/os-jobs | B025–B036 | 8 | 3 | 176 passed, 0 failed |
| 4 crates/os-memory | B037–B048 | 8 | 3 | 67 passed, 0 failed |
| 5 crates/os-identity | B049–B060 | 8 | 3 | 55 passed, 0 failed |
| 6 crates/os-budget | B061–B072 | 8 | 3 | 118 passed, 0 failed |
| 7 crates/os-worker | B073–B084 | 8 | 3 | 131 passed, 0 failed |
| 8 crates/os-workspace | B085–B096 | 8 | 3 | 74 passed, 0 failed |
| 9 crates/agent-runtime | B097–B108 | 8 | 3 | 43 passed, 0 failed |
| 10 crates/queue-core | B109–B120 | 8 | 3 | 42 passed, 0 failed |
| 11 crates/queue-store | B121–B132 | 8 | 3 | 39 passed, 0 failed |
| 12 crates/assess-server | B133–B144 | 8 | 3 (in-src) | 40 passed, 0 failed |
| 13 crates/dashboard | B145–B156 | 8 | 3 + 4 old | 130 passed, 0 failed |
| 14 crates/guardrail | B157–B168 | 8 | 3 | 43 passed, 0 failed |
| 15 crates/intel | B169–B180 | 8 | 3 + 6 old | 257 passed, 0 failed |
| 16 crates/relay | B181–B192 | 8 | 3 + 6 old | 58 passed, 0 failed |
| 17 crates/stack | B193–B204 | 8 | 3 | 40 passed, 0 failed |
| 18 crates/os-misc | B205–B216 | 8 | 3 + 23 in-src | 75 passed, 0 failed |
| 19 Python root | B217–B240 | 12 | 12 | 264 + 47 passed, 0 failed |
| 20 kernel-adjacent | B241–B252 | 8 + 3 existing | — | 7/7 node, ABI check green |

`assess-server` is a binary crate, so its tests live in
`src/main.rs` (40 tests); `crates/assess-server/tests/` is empty by
design, not by omission.

## Files produced

- `os-build/records/<crate>.md`, `-gaps.md`, `-records.md`,
  `-callers.md`, `-config.md`, `-drill.md`, `-surface.md`,
  `-changes.md` — 18 crates, 144 files.
- `os-build/records/python-*.md` — 12 files.
- `os-build/records/{sched-rs,user-rs,display,boot-sequence,framebuffer,syscalls-frozen,claim-audit,kernel-index}.md`
  — 8 files; B241/B242/B245 extend the checked-in
  `memory-allocator.md`, `task-lifecycle.md`, `fault-path.md`.
- `crates/<crate>/tests/{error_paths,edge_cases,gap_close}.rs` — 54
  new Rust test files (61 test files in those crates in total).
- `tests/queue-python/test_*_missing.py` and
  `os/tests/test_python_*_missing.py` — 12 new Python test files.
- All 18 `<crate>-changes.md` files now carry a real
  `git log -- crates/<crate>` appendix.

## Production changes made (all verified by the crate suites)

- `crates/os-budget`: `parse_artifact_ref` now refuses an empty job id,
  matching the Python regex; a private file-read seam makes that
  refusal testable.
- `crates/agent-runtime`: two byte-slicing panics fixed —
  `relay_notify_payload` (short ok result) and `finish_failed`
  (multibyte error text) now cap by characters like the Python.
- Doc-only corrections in `os-boot`, `os-supervisor`, `os-jobs`,
  `os-memory`, `os-identity`, `os-worker`, `os-workspace`,
  `queue-core`, `queue-store`, `guardrail`, `intel`, `relay`,
  `dashboard`: stale "skeleton / no logic yet" headers and wrong
  comments corrected where the code is right (task B004/B016/...).

## Findings filed, not fixed

Every record has its own Findings section; these are the cross-cutting
ones:

- `KERNEL_SPEC.md` K4 says 61660 frames; `K1-boot.txt` and
  `SCOREBOARD.md` say 127199 — a real conflict, recorded in
  `os-build/records/claim-audit.md`.
- `README.md`'s test table is stale (1933/1877/56).
- `kernel/src/tasks.rs` header still says UNWIRED and claims no
  `Cargo.lock`; both false.
- `readkey` wrapper now exists in `lib.rs`, but the bin is not in
  `kernel/build.rs`, so it still does not ship.
- The 55 native/Swift failures measured on clean `main` in the light
  lanes remain pre-existing and untouched.
- Crate-level gaps are listed per crate in `<crate>-gaps.md` (for
  example the missing production backends in `os-boot`, the
  Redis/bus seams in `os-supervisor`, and the unported
  Upstash/relay paths in `queue-store`).

## ABI document reconciliation

Upstream `main` shipped a 57-line `os-build/USERSPACE_ABI.md`; the
lane-3 version was 276 lines with worked examples. They were merged:
the detailed spec is kept and the summary table required by
`os-build/layer1/abi_check.py` was added. Both the upstream checker
and `tests/kernel-records.test.mjs` now pass on the same file.

## How to reproduce

```
cargo test -p <crate> -j1            # per crate, one at a time
python3 -m pytest tests/queue-python -q
python3 -m pytest tests/custos -q
python3 -m pytest tests/officina -q
node --test tests/kernel-records.test.mjs
python3 os-build/layer1/abi_check.py
```
