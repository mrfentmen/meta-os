# Callers of `crates/queue-store`

Repo-wide search on `main`, 2026-11-02 (`queue_store::` imports and
the exported names). Two code callers; one README claim that is not a
code caller.

## 1. `crates/agent-runtime` — the real consumer

- Import: `use queue_store::{JobStore, StoreBackend};`
  (`crates/agent-runtime/src/lib.rs:14`).
- It holds a `JobStore<B>` and calls, in order of use:

| Call | Site | What the caller expects |
|---|---|---|
| `get_result(jid)` | `agent-runtime/src/lib.rs:74`, `82` | `Some` means already answered; skip generation and do not re-bill |
| `finish(jid, "done", reason)` | `:75`, `:83`, `:153` | marks the job, releases the claim; accepts a reason string |
| `claim(jid, nick, lease)` | `:78` | `false` means another worker owns it; `true` means this worker may generate |
| `job_envelope(jid)` | `:92` | `None` is a hard failure; the frame is read from the envelope |
| `put_result(&result)` | `:152`, `:168` | keys the result by `result["job_id"]`; the caller builds that field |
| `submit(&env)` (tests) | `:418` | ignores `created`; files the job for the test |

**Expectation that the crate does not enforce:** the idempotent-skip
path (`:75`, `:83`) calls `finish` **before** any claim. `finish` has
no status or ownership precondition (`queue-store/src/lib.rs:442-448`),
so this works today. If a later slice adds a claim-owner check to
`finish`, this caller breaks. Flagged, not fixed.

**Expectation the crate meets only in tests:** production selection of
a backend. The caller is generic over `StoreBackend`, but the only
backend constructed in the repo is `InMemoryStore` in tests
(`agent-runtime/src/lib.rs:381`). `SqliteStore` is never constructed
outside its own crate, and no Upstash backend exists (see
`queue-store-gaps.md`).

## 2. `crates/assess-server` — the repo layer

- Use: `queue_store::product_profile(product)`
  (`crates/assess-server/src/main.rs:421`).
- Expects `Option<&'static ProductProfile>` and turns `None` into its
  own `ModelError { code: "model_call_failed" }`. It reads
  `display_name`, `department`, `categories`, `limitations` and passes
  them to `guardrail::build_prompt` (`main.rs:422`).
- No other product-layer function is called: `PRODUCTS`,
  `product_ids`, and `namespace` have no caller in the repo.

## 3. `crates/queue-core` README — a claim, not a caller

`crates/queue-core/README.md:20-23` says B02
(`crates/queue-store`) builds on queue-core's `Backend` trait and owns
the transports. The code does not: `crates/queue-store/Cargo.toml` has
no `queue-core` dependency, and `queue-store` defines its own
`StoreBackend` trait, key functions, and `JobStore`
(`queue-store/src/lib.rs:108-122`, `173-189`, `376-450`).
`OPENCODE_FINISH_REPORT.md:50-56` already names this duplication
(queue-core 12 tests vs queue-store 5). It is a real architectural
split, not a missing import: nothing fails today because no code
mixes the two traits.

## 4. No other callers

- `os-build/aegis/*` names the crate only as a path to sweep.
- `BOND_TASKS.md`, `BATCHES.md`, `SUPER_PROMPT.md` are task records.
- No Python or JavaScript caller links the Rust crate; the Python
  originals remain the live fallback (`server/queue/trio_store.py`).
