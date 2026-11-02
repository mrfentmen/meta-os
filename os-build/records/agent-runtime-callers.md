# `crates/agent-runtime` — callers (B103)

Repo-wide scan for `agent_runtime`, `agent-runtime`, `serve_job(`,
`relay_notify_payload`, `validate_assessment`, plus every
`Cargo.toml` that names the crate.

## Dependants

| Caller | How it depends | What it expects | Source |
|---|---|---|---|
| `crates/assess-server` | path dependency `agent-runtime = { path = "../agent-runtime" }` | one function: `validate_assessment(&Value, &str) -> (bool, Vec<String>)` | `crates/assess-server/Cargo.toml:20` |
| workspace | member of the root virtual workspace | the crate builds as a library target; no binary is expected | `Cargo.toml:8` |

## Call sites

### `validate_assessment` — USED

`crates/assess-server/src/main.rs:566-571`:

```rust
fn contract_check(output: &Value, product: &str) -> Result<Value, Value> {
    match agent_runtime::validate_assessment(output, product) {
        (true, _) => Ok(output.clone()),
        (false, errors) => Err(json!({"error": format!(
            "Model response failed contract validation: {}", errors.join("; "))})),
    }
}
```

Expectation: the validator returns **all** errors, joined for the 502
body; `true` means the object is safe to return verbatim. The crate
meets this: it returns the full `Vec<String>` and never mutates the
value (`lib.rs:179-278`).

One behavioural coupling worth stating: the same validator governs the
agent's one correction retry (`lib.rs:129-146`), so a tightening here
also tightens what the agent will accept from the model. There is one
implementation, not two.

### `Agent`, `Generator`, `Outcome`, `serve_job`, `relay_notify_payload` — NO CALLERS

No binary, crate, test outside the crate, or script in the repo
constructs an `Agent` or calls `serve_job`. The only uses are the
crate's own unit tests (`lib.rs:391-470`).

Flag: **the resident Rust agent process does not exist yet.** The Python
resident (`server/queue/trio_agent.py:335-356`) is what actually runs
today. Until a binary or service calls `serve_job`, this crate is a
library with a proven core and no deployment path — that is a caller
gap, not a crate bug.

### `now_iso` — INTERNAL ONLY

Called at two sites, both inside the crate (`lib.rs:154`, `lib.rs:169`).
No caller depends on its shape today, so the epoch-millis divergence
(gap G2) has no consumer impact yet; it will the moment a result is
read by something expecting the Python ISO string.

## Callers that expect something the crate does not do

| Expectation | Reality | Where it would bite |
|---|---|---|
| A resident agent that keeps its claim alive during a slow generation | no heartbeat (gap G1) | a generation longer than `lease` is claimable by a second agent; the first result still wins only if it lands first |
| A finished-job relay notification | payload builder exists but no call/POST (gap G3) | `TRIO_RELAY_URL` has no effect in the Rust path |
| `completed_at` in the Python ISO-8601 shape | epoch-millis string (gap G2) | any consumer that parses it as a date |
| A poll loop that drains `open_job_ids()` | no `serve_once` (gap G4) | the caller must write the loop and its `{done, failed, skipped, lost}` report |

No caller in the repo currently holds any of these expectations — the
table is the risk list for the first one that does.
