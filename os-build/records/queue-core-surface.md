# queue-core — public surface inventory (B118)

Every `pub` name in `crates/queue-core/src/lib.rs`, one line each.
Marks: **EXTERNAL** = called from another crate; **TESTS** = used only
by this crate's tests; **UNUSED** = no caller in the repo today.

## Functions

| Name | Line | What it is | Used |
|---|---|---|---|
| `sha256_hex` | `40` | SHA-256, lowercase hex | TESTS (internal callers at `188`, `219`) |
| `base64_decode` | `118` | strict base64 decode | TESTS (internal caller at `212`) |
| `deterministic_job_id` | `181` | `trio-` + 32 hex job id | **EXTERNAL** — `crates/assess-server/src/main.rs:191` |
| `validate_envelope` | `195` | envelope refusal check | TESTS |
| `job_key` | `229` | `<ns>:<jid>` | UNUSED (copied in `queue-store/src/lib.rs:100`, `os-jobs/src/lib.rs:392`) |
| `envelope_key` | `233` | `<ns>:<jid>:job` | UNUSED (copied in `queue-store/src/lib.rs:103`) |
| `claim_key` | `237` | `<ns>:<jid>:claim` | UNUSED (copied in `queue-store/src/lib.rs:106`, `os-jobs/src/lib.rs:400`) |
| `index_key` | `241` | `<ns>index` | UNUSED (copied in `queue-store/src/lib.rs:109`, `os-jobs/src/lib.rs:404`) |
| `result_key` | `247` | `trio:<jid>:result` | UNUSED (copied in `queue-store/src/lib.rs:112`) |

## Types and traits

| Name | Line | What it is | Used |
|---|---|---|---|
| `EnvelopeImage` | `161` | `data_url`, `byte_length`, `sha256` | TESTS (field of `Envelope`) |
| `Envelope` | `170` | v1 trio-assessment envelope | TESTS |
| `Backend` | `255` | nine-command store trait | TESTS (bound on `JobStore`; implemented by `MemoryBackend`) |
| `MemoryBackend` | `278` | in-memory `Backend` | TESTS |
| `JobStore<B: Backend>` | `383` | job semantics over a backend | TESTS |

## Methods and fields

| Name | Line | Used |
|---|---|---|
| `MemoryBackend::new` | `285` | TESTS |
| `Backend::get` | `256` | TESTS / internal |
| `Backend::set_body` | `257` | TESTS / internal |
| `Backend::delete` | `258` | TESTS / internal |
| `Backend::set_nx_ex` | `259` | TESTS / internal |
| `Backend::set_xx_ex` | `260` | TESTS / internal |
| `Backend::hset` | `262` | TESTS / internal |
| `Backend::hgetall` | `263` | TESTS / internal |
| `Backend::zadd` | `264` | TESTS / internal |
| `Backend::zrange` | `265` | TESTS / internal |
| `JobStore::new` | `389` | TESTS |
| `JobStore::submit` | `398` | TESTS |
| `JobStore::job_fields` | `420` | TESTS |
| `JobStore::job_envelope` | `424` | TESTS |
| `JobStore::open_job_ids` | `428` | TESTS |
| `JobStore::get_result` | `439` | TESTS |
| `JobStore::claim` | `444` | TESTS |
| `JobStore::renew_claim` | `464` | TESTS |
| `JobStore::release_claim` | `468` | TESTS |
| `JobStore::put_result` | `473` | TESTS |
| `JobStore::finish` | `477` | TESTS |
| `JobStore::backend` (field) | `384` | TESTS (`edge_cases.rs` reads the index) |
| `JobStore::ns` (field) | `385` | TESTS |

## Inventory result

One external entry point: `deterministic_job_id`. Every other public
name is reachable only from this crate's tests. The five key functions
have copies in two peer crates, which is why they show UNUSED here while
their format strings are live elsewhere (`queue-core-callers.md`).
