# `crates/os-worker` — change record (B084)

## What is evidenced in the tree

- **B00 skeleton.** `Cargo.toml:1-5` is still version `0.1.0` with no
  dependencies. `src/lib.rs:1` carried the B00 "skeleton" line until this
  pass; B076 corrected it to describe the B22 port.
- **B22 port.** `src/lib.rs:1-61` names the nineteen Python test/source
  files the batch ports and the live-behaviour boundary. The section
  markers run from `lib.rs:62` (SHA-256) to `lib.rs:2825` (lease sweep),
  and `lib.rs:3004-4661` holds the 96-test module.
- **Batch record.** `BATCHES.md:56` and `batches/B22.md:1-66` record the
  batch, crate, build/test commands, and the completion-report shape.
- **Work items.** `SUPER_PROMPT.md:263-277` lists T137-T149: port the
  test-file groups, port the source modules, compile-fix, parity-run, and
  write crate docs. `docs/RUST_REBUILD_PLAN.md:240` maps B22 to
  `os-worker`.
- **Test-count evidence.** `OPENCODE_FINISH_REPORT.md:116` reports
  `os_worker 96` tests at that run; the test module in the tree has 96
  `#[test]` functions (`lib.rs:3004-4661`).
- **This pass (B073-B084).** Added the eight records in this directory
  and three integration-test files under `crates/os-worker/tests/`
  (`error_paths.rs`, `edge_cases.rs`, `gap_close.rs`). The only source
  edit is the stale `lib.rs` header line (B076, finding 1).

## What is NOT evidenced here

This worker has no terminal access, so it cannot read `git log` or
attribute commits, dates, or authors. The task asks for changes "from
git history"; that part is **not claimed**. A fabricated date or sha
would be worse than a named hole.

To complete it, the coordinator appends:

```
git log --oneline --follow -- crates/os-worker | head -50
git log --stat -- crates/os-worker/src | head -100
```

## Known change points to check against that log

| Change | Where it would show |
|---|---|
| Skeleton created (B00) | first commit touching `crates/os-worker/Cargo.toml` |
| Port landed (B22) | the commit adding the section markers and tests in `src/lib.rs` |
| Header corrected (this pass) | one-line change at `src/lib.rs:1` and `:25` |
| Records/tests added (this pass) | eight files in `os-build/records/`, three under `crates/os-worker/tests/` |
| Any later fix | `git log -p -- src/lib.rs`; the current tree has no post-port fix markers in the file |

## Commit history (appended by coordinator, from git)

- 309fc60 2026-10-30 B22: port worker runtime & drivers to crates/os-worker (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
