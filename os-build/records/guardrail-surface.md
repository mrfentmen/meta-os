# crates/guardrail — public surface inventory (B166)

Every exported name in `crates/guardrail/src/lib.rs`, one line each,
marked with real use in the repo today. "Tests" means the new
integration tests in `crates/guardrail/tests/`; "crate" means used
elsewhere inside the same file.

## Constants

| Name | Line | Kind | Used by |
|---|---:|---|---|
| `TEST_BUDGET_USD` | 13 | f64 | `check` (70), `status_of` (108), tests |
| `RATE_IN_PER_M` | 14 | f64 | `estimate` (81), tests |
| `RATE_OUT_PER_M` | 15 | f64 | `estimate` (82), tests |
| `SPARK_ENDPOINT` | 16 | &str | `assess-server` re-export and request URL (`main.rs:32,451`) |
| `SPARK_MODEL` | 17 | &str | `build_prompt` (145), `assess-server` (`main.rs:442`) |

## Types

| Name | Line | Kind | Fields | Used by |
|---|---:|---|---|---|
| `GuardrailStop` | 20 | tuple struct | `0: String` | `check`'s error; `assess-server` stop path (`main.rs:436-438`) |
| `UsageLog` | 27 | struct, Serialize+Deserialize | `ts`, `kind`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `est_cost_usd`, `cum_est_cost_usd` | `record` (92-100), ledger JSON |
| `GuardrailState` | 39 | struct, Serialize+Deserialize | `calls`, `est_cost_usd`, `log` | `load_state`, `save_state`, `check`, `record`, `status_of`, `assess-server` |
| `GuardrailState::default` | 48 | impl Default | zeroed state | `load_state` (61) |

## Functions

| Name | Line | Signature (short) | Used by |
|---|---:|---|---|
| `load_state` | 57 | `(&str) -> GuardrailState` | `assess-server` (`main.rs:436`) |
| `save_state` | 64 | `(&str, &GuardrailState)` | only `record` (101); no external caller |
| `check` | 70 | `(&GuardrailState) -> Result<(), GuardrailStop>` | `assess-server` (`main.rs:436`) |
| `estimate` | 80 | `(u64, u64) -> f64` | `record` (87), tests |
| `record` | 86 | `(&str, &str, &str, u64, u64, u64) -> f64` | `assess-server` (`main.rs:471`) |
| `status_of` | 105 | `(&GuardrailState) -> serde_json::Value` | **no production caller** — the Python `status()` has four readers, the Rust export has none |
| `unwrap_model_text` | 116 | `(&str) -> String` | `assess-server` (`main.rs:491`) |
| `build_prompt` | 139 | `(&str, &str, &str, &[&str], &str, &str, Option<&str>) -> String` | `assess-server` (`main.rs:423`) |
| `via_helper` | 162 | `() -> bool` | **no Rust caller**; the transport choice lives in `spark_gen.py` |

## Unused surface, stated plainly

- `status_of` — exported, tested, but nothing in the Rust tree calls it
  in production. It is the counterpart of Python `status()`, which four
  queue modules read.
- `via_helper` — exported, tested, no Rust caller. Keeping it is a
  port-completeness choice; it does not choose a transport here.
- `save_state` — exported but only reached through `record`; no caller
  persists a state it built by hand.
