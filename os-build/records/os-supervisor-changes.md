# `crates/os-supervisor` — change record (B024)

## What is evidenced in the tree

- **B00 skeleton.** `Cargo.toml:1-5` is still version `0.1.0` with no
  dependencies. `src/lib.rs:1` carried the B00 line ("skeleton") until
  this pass; B016 corrected it to describe the B21 port.
- **B21 port.** `src/lib.rs:44-62` declares the fifteen modules and
  `drills`, and `lib.rs:3-42` names the 40 Python source files the batch
  ports. The module docs carry the port statement in each file, e.g.
  `watchdog.rs:4` ("Rust port of `os/intel/watchdog.py` (batch B21,
  task T129)") and `relay_watchman.rs:4` ("batch B21, tasks T131/T119").
- **Batch record.** `batches/B21.md:1-96` records the batch, the crate,
  the build/test commands, and the completion-report shape.
- **Work items.** `SUPER_PROMPT.md:240-261` lists T117-T136: port the
  six test-file groups, port the nine drill modules, port the source
  modules, compile-fix, parity-run, and write crate docs.
- **This pass.** B013-B024 added the eight records in this directory
  and the three integration-test files under `crates/os-supervisor/tests/`
  (`error_paths.rs`, `edge_cases.rs`, `gap_close.rs`). The only source
  edit is the stale `lib.rs` header line (B016, finding 1).

## What is NOT evidenced here

This worker has no terminal access, so it cannot read `git log` or
attribute commits, dates, or authors. The task asks for changes "from
git history"; that part is **not claimed**. A fabricated date or sha
would be worse than a named hole.

To complete it, the coordinator appends:

```
git log --oneline --follow -- crates/os-supervisor | head -50
git log --stat -- crates/os-supervisor/src | head -100
```

## Known change points to check against that log

| Change | Where it would show |
|---|---|
| B00 skeleton created | first commit touching `crates/os-supervisor/Cargo.toml` |
| B21 modules landed in waves (test ports T117-T119, drills T120-T124, sources T125-T132, reconcile/overseer T133) | commits adding `src/*.rs` |
| compile fixes T134 | commits changing existing module bodies |
| docs T136 | commits touching module headers only |
| B016 header correction (this pass) | `src/lib.rs:1` |

Count check: the crate today has 15 top-level modules, 9 drill modules,
6,000+ lines of source, and 379 `#[test]` attributes
(`OPENCODE_FINISH_REPORT.md:116` quotes 379). Those numbers are from
grep/read, not from git.

## Commit history (appended by coordinator, from git)

- e4fa855 2026-10-30 B21: port supervisor & watchdog to crates/os-supervisor (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
