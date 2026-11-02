# queue-core — change record (B120)

Provenance: this slice had no terminal, so `git log` was not available.
The timeline below is read from the tree's own records, each cited. A
commit-level changelog should be regenerated with
`git log --follow -- crates/queue-core/` before merge.

## Timeline as the tree records it

| When | Change | Source |
|---|---|---|
| B00 | Crate added to the workspace as a skeleton member | `Cargo.toml:23`, `BATCHES.md:35` |
| B01 (2026-10-30 04:47 bus order) | Ported the Trio queue core: envelope validation, deterministic id, key layout, `Backend`/`JobStore`; Python originals stay as fallback | `crates/queue-core/src/lib.rs:1-24`, `batches/B01.md`, `README.md:1-17` |
| B01 tests | 12 tests: SHA-256 vectors (incl. 1,000,000-byte padding boundary), strict base64, envelope refusals, key layout, store round-trips | `crates/queue-core/src/lib.rs:496-679`, `README.md:47-55` |
| B07 integration wave | queue-core reported 12/12; six wave-1 crates 39/39 together | `batches/B07-report-wave1.md:28-41` |
| assess-server | Its own job-id function replaced by `queue_core::deterministic_job_id` (thin alias) | `OPENCODE_FINISH_REPORT.md:40-41`, `crates/assess-server/src/main.rs:189-192` |
| Current tree | Key functions duplicated in `queue-store` and `os-jobs`; named as a duplication to resolve | `OPENCODE_FINISH_REPORT.md:50`, `queue-core-callers.md` §2-3 |
| This pass (B109-B120) | Added three integration test files (error paths, edge cases, memory-backend gap close); wrote eight records; corrected docs where the code was right | this report set |

## What changed in this pass, precisely

- `crates/queue-core/tests/error_paths.rs` — new (B110).
- `crates/queue-core/tests/edge_cases.rs` — new (B111).
- `crates/queue-core/tests/gap_close.rs` — new (B119).
- `os-build/records/queue-core*.md` — eight new records (B109, B113-B120).
- `crates/queue-core/src/lib.rs` and `README.md` — comment/doc only,
  no behaviour change (B112).

No production logic was edited, no test was deleted, and no dependency
was added.

## Commit history (appended by coordinator, from git)

- 7c9ad8b 2026-10-30 B01: queue-core crate — envelope validation + job-store semantics ported from server/queue (Rust 12/12, workspace green, Node 1906/1906; gates 1+2 pending)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
