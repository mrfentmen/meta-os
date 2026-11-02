# crates/guardrail — callers (B163)

Search basis: every `guardrail`/`guardrail::` reference in `meta-os/`
(excluding the crate itself). The Rust crate has one production caller
and one parity peer; the Python originals have four readers.

## Rust callers

### `crates/assess-server/src/main.rs` — the only caller

| Line | Uses | What it expects |
|---|---|---|
| 32 | `pub use guardrail::{SPARK_ENDPOINT, SPARK_MODEL};` | re-exported for its own callers |
| 423 | `build_prompt(..., None)` | a complete model prompt for the product profile |
| 436 | `guardrail::check(&guardrail::load_state(state))` | a refusal BEFORE any network send, with the exact stop text |
| 442 | `guardrail::SPARK_MODEL` | the model id in the request body |
| 451 | `guardrail::SPARK_ENDPOINT` | the endpoint when `SPARK_ENDPOINT` is unset |
| 471 | `guardrail::record(...)` after a billable response | the ledger is updated and survives the process |
| 491 | `guardrail::unwrap_model_text(&text)` | a JSON object string ready for the contract parser |

**Flags — where the caller expects more than the crate gives:**

1. `build_prompt` (423) is expected to produce the same prompt as
   `spark_gen.py:93-151`; it omits the region field and four
   paragraphs (guardrail.md finding 4 / gaps G4-G7). The model's
   contract can therefore drift on region and visible marks.
2. `record` (471) is expected to persist spend; its write result is
   ignored (finding 2 / gap G2), so a successful assessment can go
   uncounted and the $75 cap can under-count.
3. `check(load_state(...))` (436) is expected to survive a damaged
   ledger; `load_state` resets a corrupt file to zero (finding 1 /
   gap G1), so spend protection silently disappears exactly when the
   ledger is broken.

The assess-server records carry the same three observations:
`os-build/records/assess-server-gaps.md:48-51,124-125,156-159` and
`os-build/records/assess-server-callers.md:38-41`.

## Parity peer (not a Rust caller)

- `server/budget.mjs:31-156` — the Node mirror of the Python
  guardrail, same $75 ledger and same refusal wording. It is stricter
  than the Rust port on three points: it raises `BudgetError` for an
  unreadable/invalid/malformed state (`65-103`), writes the real ISO
  timestamp (`125`), and rounds `remaining_usd` to 4 dp (`154`).
  `server/model.mjs:163-166,227` is the Node caller that checks before
  send and records after.

## Python callers (the behaviour the port must match)

| Caller | Lines | Expects |
|---|---|---|
| `server/queue/spark_gen.py` | 170 (`check()`), 202-204 (`record`) | a pre-send refusal; one ledger row per direct call with usage tokens and latency |
| `server/queue/patrol.py` | 157-160 (`check()`, `status()`) | the stop text is caught and filed as `guardrail_stop`; `remaining_usd` drives the pause |
| `server/queue/supervisor.py` | 189, 401-415 (`status()`) | a read-only spend finding at 80%+ of budget; unreadable status invents nothing |
| `server/queue/orchestrator.py` | 86, 216-217, 281-286 (`status()`) | per-call average and `remaining_usd` for its limit breach check |

## Not callers

- `crates/parity-tests` — no `guardrail` import; its B03 cases are not
  written there.
- `crates/stack`, `crates/relay`, `crates/os-*` — no references.
