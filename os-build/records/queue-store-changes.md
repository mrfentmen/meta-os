# Changelog — `crates/queue-store`

What changed since the port began, assembled on 2026-11-02 from the
committed records in this repo. **This worker had no terminal**, so
`git log --oneline -- crates/queue-store` was not available; the
entries below are the ones the repo states, with their source. A
terminal pass should append the exact commit list and keep this file
current.

## 1. Skeleton (B00)

- The crate was created as one of the workspace members in
  `Cargo.toml:24`.
- `BATCHES.md:36` assigns B02 "Queue store (Upstash store + repo
  layer)" to `crates/queue-store`, owner Rowan.
- `batches/B00.md:10` lists `queue-store` among the B00 skeleton
  crates.

## 2. Port (B02)

- Source of truth: `server/queue/trio_repo.py` and
  `server/queue/trio_store.py`, both untouched (`batches/B02.md:9-12`).
- `batches/B07-report-wave1.md:9` records `queue-store` as coming
  "from `batch/B02` 1d8bf1e".
- `OPENCODE_FINISH_REPORT.md:56` reports **queue-store 5** tests, and
  `:117` repeats `queue_store 5` in the suite count. Those are the five
  unit tests currently in `src/lib.rs` (`mod tests`).

## 3. Known architectural note raised after the port

- `OPENCODE_FINISH_REPORT.md:50-56` and `:130` name the duplication
  between `queue-core` and `queue-store`: both define key functions and
  a `JobStore` over their own backend trait, and nothing depends on
  the other. `queue-core/README.md:20-23` still claims B02 builds on
  B01; the code does not.

## 4. Task list (2026-11-02)

- `os-build/BOND_TASKS.md:161-174` adds Section 11, B121-B132, the
  twelve tasks this file is part of.

## 5. This pass (B121-B132)

- Added the behaviour record, gap list, worked records, callers,
  config, drill, surface, and this changelog under
  `os-build/records/queue-store*.md`.
- Added `crates/queue-store/tests/error_paths.rs`,
  `edge_cases.rs`, `gap_close.rs`.
- Doc corrections in `src/lib.rs` where the code is right:
  - header now names the Rust struct `SqliteStore` (it said
    `LocalSqliteStore`, the Python class) and states the integer-second
    expiry difference;
  - `namespace()` now documents that it re-reads `TRIO_JOB_NS` per call
    and accepts an empty value.
- No production logic was changed by this pass.

## Commit history (appended by coordinator, from git)

- 5d7ec68 2026-10-30 B07: wave-1 integration (B02-B05 ports over main B01+B06) + parity-tests E0119 seam fix — UNCOMPILED (gate 2 pending)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
