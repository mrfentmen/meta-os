# `crates/agent-runtime` — public surface inventory (B106)

Every exported name in `crates/agent-runtime/src/lib.rs`, one line
each, marked **USED** (a caller outside the crate uses it today) or
**UNUSED** (no caller outside the crate). "Tests" means the crate's own
`#[cfg(test)]` module, which does not count as a consumer.

| Export | Kind | What it is | Used? | Source |
|---|---|---|---|---|
| `now_iso` | `pub fn() -> String` | epoch-millis string, not ISO-8601 | UNUSED externally; called twice inside the crate | `lib.rs:23-33` |
| `relay_notify_payload` | `pub fn(&Value, Option<&str>) -> Option<Value>` | builds a `{severity, topic, text}` relay body; no POST | UNUSED | `lib.rs:35-56` |
| `Outcome` | `pub enum` | result of serving one job: `Done`, `Failed`, `Skipped`, `Lost` | UNUSED externally; returned by `serve_job` | `lib.rs:58-59` |
| `Outcome::Done` | variant | job answered, result written | tests only | `lib.rs:58` |
| `Outcome::Failed` | variant | refusal result written | tests only | `lib.rs:58` |
| `Outcome::Skipped` | variant | result already present, not re-billed | tests only | `lib.rs:58` |
| `Outcome::Lost` | variant | claim race lost, nothing written | tests only | `lib.rs:58` |
| `Generator` | `pub trait` | generation seam: `generate(product, image, timestamp, correction) -> Result<(Value, String, u64), String>` | UNUSED externally; implemented only by the crate's test doubles | `lib.rs:60-62` |
| `Agent` | `pub struct` | nick + lease + `JobStore` + `Generator` | UNUSED externally; constructed only in tests | `lib.rs:64-69` |
| `Agent.nick` | `pub` field | claim owner written to the store | tests only | `lib.rs:65` |
| `Agent.lease` | `pub` field | claim TTL in seconds | tests only | `lib.rs:66` |
| `Agent.jobs` | `pub` field | the injected job store | tests only | `lib.rs:67` |
| `Agent.gen` | `pub` field | the injected generator | tests only | `lib.rs:68` |
| `Agent::serve_job` | `pub fn(&mut self, &str) -> Outcome` | the whole serve path | UNUSED externally | `lib.rs:72-89` |
| `validate_assessment` | `pub fn(&Value, &str) -> (bool, Vec<String>)` | the v2 contract validator | **USED** by `assess-server` | `lib.rs:179-278` |

## Notes

- There is one module and no `pub mod`, no re-export, and no
  `pub(crate)` surface. The table is the complete API.
- The only external consumer is
  `crates/assess-server/src/main.rs:566-571`, and it uses exactly one
  function. Every other export exists for a caller that does not exist
  yet (see the callers record).
- `Agent::serve_claimed` and `Agent::finish_failed` are private and are
  not part of the surface (`lib.rs:91`, `lib.rs:157`).
- The public fields make the struct constructible without a
  constructor and make its invariant (`lease > 0`, non-empty nick)
  unenforced. That is a deliberate skeleton shape today; if the surface
  is ever frozen, a constructor and private fields are the change.
- `now_iso` is public but no external consumer imports it; its shape is
  the gap G2 risk, not a supported API.
