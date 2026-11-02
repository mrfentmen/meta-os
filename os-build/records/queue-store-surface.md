# Public surface — `crates/queue-store`

Every exported name in `crates/queue-store/src/lib.rs` on `main`,
2026-11-02, with one line and whether the repo uses it today. "Used"
means a caller outside the crate's own `#[cfg(test)]` module; the
crate's unit tests and this pass's integration tests do not count.

## Types

| Name | What it is | Used? |
|---|---|---|
| `ProductProfile` (`lib.rs:29-35`) | static product config record | **yes** — `assess-server/src/main.rs:421-422` reads every field |
| `PRODUCTS` (`lib.rs:37-84`) | the three embedded profiles | internal only — no external caller |
| `TrioStoreConfigError` (`lib.rs:123-134`) | typed host-config refusal; `.0` is the message | **yes** — appears in both resolve signatures; no external construction |
| `InMemoryStore` (`lib.rs:192`) | test/local backend, `Default` | **yes** — `agent-runtime/src/lib.rs:381` |
| `SqliteStore` (`lib.rs:270`) | file-backed fallback backend | **no** — never constructed outside this crate |
| `JobStore<B>` (`lib.rs:376-380`) | job semantics over a `StoreBackend` | **yes** — `agent-runtime/src/lib.rs:14`, `414` |
| `StoreBackend` (`lib.rs:173-189`) | ten-method backend trait | **yes** — imported as a bound by `agent-runtime` |

## Functions and methods

| Name | What it does | Used? |
|---|---|---|
| `product_ids()` (`lib.rs:86-88`) | ids as a `HashMap<String, ()>` | **no** |
| `product_profile()` (`lib.rs:90-92`) | lookup, `Option` | **yes** — `assess-server` |
| `namespace()` (`lib.rs:102-104`) | reads `TRIO_JOB_NS`, default `trio` | **no** — callers pass an explicit `ns` |
| `job_key` (`lib.rs:108-110`) | `<ns>:<jid>` | internal |
| `envelope_key` (`lib.rs:111-113`) | `<ns>:<jid>:job` | internal |
| `claim_key` (`lib.rs:114-116`) | `<ns>:<jid>:claim` | internal |
| `index_key` (`lib.rs:117-119`) | `<ns>index` | internal |
| `result_key` (`lib.rs:120-122`) | `trio:<jid>:result`, namespace-independent | internal |
| `resolve_upstash_host` (`lib.rs:147-162`) | env → credential URL → typed error | **no** — unit tests only |
| `resolve_upstash_host_from_env` (`lib.rs:164-166`) | env-only convenience | **no** — no test, no caller |
| `InMemoryStore::default` | empty store | **yes** — agent-runtime tests |
| `SqliteStore::open` (`lib.rs:274-287`) | open/create the SQLite file | **no** |
| `JobStore::new` (`lib.rs:382-384`) | bind a backend + namespace | **yes** |
| `JobStore::submit` (`lib.rs:385-401`) | file an envelope, idempotent | **yes** — agent-runtime tests |
| `JobStore::job_fields` (`lib.rs:403-405`) | raw job hash | **no** — crate tests only |
| `JobStore::job_envelope` (`lib.rs:406-409`) | parsed envelope or `None` | **yes** — agent-runtime |
| `JobStore::open_job_ids` (`lib.rs:410-414`) | open jobs from the index | **no** — crate tests only |
| `JobStore::get_result` (`lib.rs:415-418`) | result or `None` | **yes** — agent-runtime |
| `JobStore::claim` (`lib.rs:419-430`) | NX claim + lease fields | **yes** — agent-runtime |
| `JobStore::renew_claim` (`lib.rs:431-433`) | XX lease refresh | **no** — no caller in the repo |
| `JobStore::release_claim` (`lib.rs:434-437`) | delete the claim key | internal — called by `finish` |
| `JobStore::put_result` (`lib.rs:438-441`) | write the frozen result envelope | **yes** — agent-runtime |
| `JobStore::finish` (`lib.rs:442-448`) | set status/note/done_at, release claim | **yes** — agent-runtime |
| `JobStore.backend` field (`lib.rs:377`) | public backend handle | **no** external access |
| `JobStore.ns` field (`lib.rs:378`) | public namespace | **no** external access |
| `TrioStoreConfigError.0` | public message field | **yes** — tests assert on it |

## Trait methods implemented on both backends

`ping`, `get`, `set_body`, `delete`, `set_nx_ex`, `set_xx_ex`, `hset`,
`hgetall`, `zadd`, `zrange` (`lib.rs:173-189`). Used through the trait
by `JobStore` and by `agent-runtime`'s import. `ping` has **no caller**
inside the crate; Python used it to gate the Upstash fallback
(`trio_store.py:355`), which is not ported.

## Summary

- Exported names: 7 types/traits + 7 free functions + 11 `JobStore`
  methods + 2 fields + 10 trait methods.
- Used outside the crate: 1 type family (`ProductProfile`/`PRODUCTS`
  lookup), `JobStore` and 7 of its methods, `InMemoryStore`,
  `StoreBackend`.
- Unused or internal-only: `product_ids`, `namespace`, both resolve
  functions, `SqliteStore`, `renew_claim`, `open_job_ids`,
  `job_fields`, the key helpers, both public fields, and `ping`.
