# queue-core — callers and peers (B115)

Search: `queue_core|queue-core` across the tree, excluding `target/` and
lockfiles.

## Real callers

### 1. `crates/assess-server` — deterministic job id

- `crates/assess-server/Cargo.toml:19` depends on
  `queue-core = { path = "../queue-core" }`.
- `crates/assess-server/src/main.rs:189-192`:

  ```rust
  /// Deterministic job id — the single implementation lives in
  /// `queue_core` (owning crate); this is a thin alias, not a copy.
  pub fn build_queue_job_id(product: &str, timestamp: &str, frame: &[u8]) -> String {
      queue_core::deterministic_job_id(product, timestamp, frame)
  }
  ```

  It expects the frozen rule `trio-` + 32 hex over
  `product\0timestamp\0frame` (`lib.rs:181-193`, mirrored from
  `server/queue.mjs:99-136`). The crate delivers exactly that. No
  mismatch.

- `crates/assess-server/src/main.rs:194-209` builds the rest of the
  envelope itself (JSON, hex digest, byte length) and calls the alias
  for the id. It does not call `validate_envelope` or `JobStore`.

## Peers holding copies, not calling the crate

These are flagged because the B01 port rule says shared types live in
the owning crate — "depend on them, never copy-paste types between
crates" (`batches/B01.md`).

### 2. `crates/queue-store`

- `crates/queue-store/src/lib.rs:100-113` re-implements `job_key`,
  `envelope_key`, `claim_key`, `index_key` and `result_key` with the same
  format strings.
- Its `Cargo.toml` has no `queue-core` dependency (verified: no match
  for `queue-core` in that crate), so the duplication is live, not an
  alias.
- Risk: a key-layout change in the owning crate does not reach the
  store that actually talks to Redis/SQLite. This is the same
  duplication named in `OPENCODE_FINISH_REPORT.md:50`.

### 3. `crates/os-jobs`

- `crates/os-jobs/src/lib.rs:392-406` re-implements `job_key`,
  `claim_key` and `index_key` (no `envelope_key`/`result_key`).
- No `queue-core` dependency in its `Cargo.toml`.
- Risk: same drift class as queue-store, for the jobs runtime.

## Non-callers (named so the boundary is clear)

- `server/queue/queue_service.py` and `server/queue/trio_store.py` are
  the Python originals, not callers: they stay untouched as the live
  fallback (`crates/queue-core/README.md`, "What it deliberately does
  NOT do yet").
- `server/queue.mjs` is the Node implementation of the same contract;
  it shares the rule, not the code.
- `BATCHES.md`, `SUPER_PROMPT.md`, `docs/RUST_REBUILD_PLAN.md` and
  `TASKS.md` name the crate in plans; they are not code callers.

## Caller expectations the crate does not meet

None of the call sites above asks for behaviour the crate lacks. The
two JSON-aware reads that Python has are not requested by any current
Rust caller — they remain gaps for a future HTTP layer
(`queue-core-gaps.md` §2).
