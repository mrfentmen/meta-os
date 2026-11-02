# crates/guardrail — behaviour record (B157)

Crate: `crates/guardrail` (B03, owner Rowan). Originals:
`server/queue/spark_guardrail.py` (the counter) and
`server/queue/spark_gen.py` (the prompt and transport that call it).
This record is read from the Rust code as it stands; every claim names
a line range in `crates/guardrail/src/lib.rs` unless another file is
named.

Scope, as the crate header states (lines 1-9): the counter covers the
DIRECT Spark transport only. The DEV helper transport carries its own
counter outside this repo. The two are never applied together.

## What it does

| Piece | Lines | Behaviour |
|---|---|---|
| Rate card | 13-17 | `TEST_BUDGET_USD` 75.0, `RATE_IN_PER_M` 1.25, `RATE_OUT_PER_M` 4.25, the Spark endpoint and model id. These are the published numbers, not read from config. |
| `GuardrailStop` | 20-25 | A string error; `Display` prints the string and `Error` is implemented, so callers can `?` it. |
| `UsageLog` | 27-37 | One ledger row: `ts`, `kind`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `est_cost_usd`, `cum_est_cost_usd`. All fields required on serialize. |
| `GuardrailState` | 39-46 | `calls`, `est_cost_usd`, `log`; each field is `#[serde(default)]`, so `{}` loads as a zero ledger. |
| `load_state` | 57-62 | Reads and parses the file; ANY error (missing, unreadable, malformed, wrong shape) returns `GuardrailState::default()`. |
| `save_state` | 64-68 | Serializes pretty JSON and writes the file; both the serialize and write results are discarded. |
| `check` | 70-78 | Refuses when `est_cost_usd >= 75.0`; otherwise `Ok(())`. Reads only the passed state, never the file. |
| `estimate` | 80-84 | `input/1e6*1.25 + output/1e6*4.25`. Tokens are `u64` arguments; there is no usage-map lookup. |
| `record` | 86-103 | Load, add the estimate, increment `calls`, push a `UsageLog`, round the cumulative to 6 dp, save, and return the UNROUNDED estimate. |
| `status_of` | 105-113 | JSON with `calls`, `est_cost_usd`, `test_budget_usd`, `remaining_usd` (not rounded). |
| `unwrap_model_text` | 116-137 | Trims; strips a leading ``` fence and a trailing ```; then slices first `{` to last `}` when the braces are ordered. No JSON parse. |
| `build_prompt` | 139-160 | Builds the assessment prompt from caller-supplied profile strings, plus a CORRECTION block when given. |
| `via_helper` | 162-164 | True only when `TRIO_SPARK_VIA_HELPER` is exactly `"1"`. |

## What it refuses

Exactly one thing: a call at or past the budget. The refusal string is
built at 72-76 and is byte-for-byte the Python one
(`spark_guardrail.py:53-58`):

```
GUARDRAIL STOP: estimated test spend $75.0000 has reached the $75.00 test budget. No call sent.
```

`check` does not load the file itself, does not send anything, and does
not retry. There is no other refusal in the crate: malformed input to
`unwrap_model_text`/`build_prompt` is returned, not rejected, and
ledger failures are swallowed (findings below).

## What it writes

One file, one JSON document, pretty-printed (`save_state`, 64-68):

```json
{
  "calls": 1,
  "est_cost_usd": 0.0055,
  "log": [
    {
      "ts": "2026-10-30T00:00:00Z",
      "kind": "assess:ignis",
      "model": "muse-spark-1.3",
      "input_tokens": 1000,
      "output_tokens": 1000,
      "latency_ms": 42,
      "est_cost_usd": 0.0055,
      "cum_est_cost_usd": 0.0055
    }
  ]
}
```

The timestamp is a literal (line 92), not the current time. The path is
always caller-supplied; the crate has no default ledger path.

## Findings (B160 spec-versus-code pass)

Code wins in each case; the doc was corrected where the comment
overclaimed, and nothing in the behaviour was changed.

1. **A corrupt ledger reads as zero spend.** `load_state` (57-62)
   collapses every error into `Default`. Python's `load_state`
   (`spark_guardrail.py:36-41`) raises on an unreadable/malformed
   existing file. A truncated ledger therefore disarms the cap in Rust
   silently. Reported to Rowan; not fixed here.
2. **A failed save is ignored.** `record` discards the write result
   (101 via `save_state`, 64-68), so a call can be sent and never counted.
   Python's `_save_state` (`spark_guardrail.py:44-46`) raises. The
   assess-server records also list this as a caller risk.
3. **The ledger timestamp is a constant.** Line 92 writes
   `2026-10-30T00:00:00Z` for every row; Python uses
   `datetime.now(timezone.utc).isoformat()` (`spark_guardrail.py:74`).
   The log cannot be ordered by time.
4. **The prompt is not the full `spark_gen.py` prompt.** `build_prompt`
   (139-160) carries the shape and the core limits but omits the
   `region` field in the observation shape, the Region paragraph
   (`spark_gen.py:126-129`), the Assessment rule (130-133), the
   visible-marks paragraph (134-143) and the vigiles crowd note
   (144-150). The doc comment was qualified to say so (139-144).
5. **No lock.** Python holds a module lock across load/modify/save
   (`spark_guardrail.py:68-73`); the Rust `record` is an unlocked
   read-modify-write (86-103), so concurrent calls can lose updates.
6. **`remaining_usd` is not rounded.** `status_of` (105-113) subtracts
   raw floats; Python rounds to 4 dp (`spark_guardrail.py:100`) and the
   Node mirror does the same (`server/budget.mjs:153-155`).
7. **`estimate` cannot read a usage map.** The Rust signature takes two
   token counts (80); Python accepts `prompt_tokens`/`input_tokens` and
   `completion_tokens`/`output_tokens` aliases (60-64). Callers must
   normalise before calling.
8. **`via_helper` has no Rust caller.** The transport choice lives in
   `spark_gen.py:57-58`; the Rust export (162-164) is unused in the
   repo today.
9. **`check` cannot load its own state.** Python's `check(state=None,
   path=None)` reads the file under the lock (49-58). The Rust `check`
   (70) takes a state only, so `assess-server` must call `load_state`
   first (see its record), which is where finding 1 bites.
