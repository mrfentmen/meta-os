# crates/guardrail — worked record shapes (B162)

Every shape below is produced by `crates/guardrail/src/lib.rs` as it
stands. Field names and rules come from the struct definitions and
`record`; the example values are a real 1000-in/1000-out call, which
costs `0.0055` at the published rate card.

## 1. The ledger file (`save_state`, 64-68)

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

| Field | Type | Rule | Source |
|---|---|---|---|
| `calls` | u64 | incremented once per `record`, never decremented | 39-46, 89 |
| `est_cost_usd` | f64 | cumulative, rounded to 6 dp after each add | 90, 39-46 |
| `log` | array | append-only in call order; no trimming | 39-46, 91 |
| `log[].ts` | string | fixed literal, not the call time (gap G3) | 92 |
| `log[].kind` | string | caller label, e.g. `assess:<product>` | 93 |
| `log[].model` | string | model id the caller got back | 94 |
| `log[].input_tokens` | u64 | caller-supplied count | 95 |
| `log[].output_tokens` | u64 | caller-supplied count | 96 |
| `log[].latency_ms` | u64 | caller-supplied | 97 |
| `log[].est_cost_usd` | f64 | this row only, rounded 6 dp | 98 |
| `log[].cum_est_cost_usd` | f64 | the new cumulative, same rounded value | 99 |

## 2. The status document (`status_of`, 105-113)

```json
{
  "calls": 1,
  "est_cost_usd": 0.0055,
  "test_budget_usd": 75.0,
  "remaining_usd": 74.9945
}
```

| Field | Rule | Source |
|---|---|---|
| `calls` | copied from the state | 106 |
| `est_cost_usd` | copied unrounded | 107 |
| `test_budget_usd` | the constant, not state | 108 |
| `remaining_usd` | `75.0 - est_cost_usd`, unrounded (gap G9) | 109-110 |

This is the Rust counterpart of Python `status()`
(`spark_guardrail.py:94-101`), which rounds `remaining_usd` to 4 dp.

## 3. The refusal (`check`, 70-78)

```text
GUARDRAIL STOP: estimated test spend $75.0000 has reached the $75.00 test budget. No call sent.
```

Built with `{:.4}` for the spend and `{:.2}` for the budget (72-76), so
the text matches Python's f-string (`spark_guardrail.py:53-58`). The
error carries no structured fields; the numbers are only in the string.

## 4. Estimate results (`estimate`, 80-84)

| Input tokens | Output tokens | Estimate |
|---:|---:|---:|
| 0 | 0 | 0.0 |
| 1 | 0 | 0.00000125 |
| 1,000 | 1,000 | 0.0055 |
| 1,000,000 | 0 | 1.25 |
| 0 | 1,000,000 | 4.25 |
| 1,000,000 | 1,000,000 | 5.5 |

`record` rounds the STORED value to 6 dp but returns the unrounded
`est` (88-102), so a caller's returned value and the ledger's row can
differ below the sixth decimal.

## 5. Model-text unwrap (`unwrap_model_text`, 116-137)

| Input | Output | Why |
|---|---|---|
| `"  {\"a\":1}  "` | `{"a":1}` | trim, then brace slice |
| `"```json\n{\"a\":1}\n```"` | `{"a":1}` | leading and trailing fence stripped |
| `"Here {\"a\":1} thanks"` | `{"a":1}` | prose outside the braces dropped |
| `""` | `""` | nothing to slice |
| `"no braces"` | `"no braces"` | returned trimmed |
| `"x {not json} y"` | `{not json}` | slices, does not parse (the caller parses) |
