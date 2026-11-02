# `crates/stack` — changelog record (B204)

What changed since the port began, from what this tree evidences.

**Method note:** this slice has no terminal, so `git log -- crates/stack`
was not readable. No commit hashes or dates are invented below. The
entries are from checked-in batch/report files, and every "needs git"
line names the command that would fill it.

## From the records

| Evidence | What it says changed |
|---|---|
| `batches/B06.md:4-5` | the port target: `crates/stack`, package `stack`, modules mirroring `run-stack.sh`, Rust tests named after the Python/Node roots |
| `batches/B06.md:10`, `23` | scope is `run-stack.sh`; the batch expects the same order/ports/env, and (incorrectly) lists `TRIO_UPSTASH_HOST` |
| `SUPER_PROMPT.md:168-171` | T090 ports the script; T091 is the compile/parity close-out, and states the module is UNCOMPILED until gate 1 |
| `crates/stack/src/lib.rs:1-31` | the crate header: batch B06, owner Rowan, pure planner, "faithful oddities" list |
| `TASKS.md:146` | B06 = stack wiring, one file |
| `MAC_RUN_REPORT.md:132` | commit `9cd59e5` fixes **`run-stack.sh`** for macOS bash 3.2 — a script fix, not a crate change |
| `os-build/records/relay-callers.md:16-21` | the crate's relay service shape was read against the script and matched |

## This pass (2026-11-02, lane B193-B204)

- Added `crates/stack/tests/error_paths.rs`, `edge_cases.rs` and
  `gap_close.rs`. No production logic changed.
- Added records: `stack.md`, `stack-gaps.md`, `stack-records.md`,
  `stack-callers.md`, `stack-config.md`, `stack-drill.md`,
  `stack-surface.md`, this file.
- No `src/lib.rs` edit: the crate's docs match its code. The
  doc-versus-**source** mismatch (three transport states in
  `run-stack.sh` versus two in the crate) is a finding, recorded in
  `stack.md` and `stack-gaps.md`; B197 forbids porting it here.

## To append with git

```
git log --date=short --oneline -- crates/stack
git log --date=short --diff-filter=A --oneline -- crates/stack/src/lib.rs
```

Expected: the B06 port commit(s) and any later header-only edits. Until
those hashes are appended, the timeline above is record-based, not
commit-based.

## Commit history (appended by coordinator, from git)

- 77da722 2026-10-30 B06: stack wiring port of run-stack.sh — UNCOMPILED
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
