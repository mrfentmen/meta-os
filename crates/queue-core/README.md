# queue-core (Rust port, B01)

First Rust piece of Rowan's server/queue lane in the 12-hour Meta OS
Rust rebuild (bus order 2026-10-30 04:47, Pax relaying Mrfentmen).
Batch B01 per `BATCHES.md` (Pax's B00 skeleton): queue core, owner Rowan.

## What it ports (no redesign)

| Rust | Python/Node original (untouched fallback) |
| --- | --- |
| `validate_envelope` | `server/queue/queue_service.py` — same error strings verbatim |
| `deterministic_job_id` | `server/queue.mjs` `buildQueueJob` — `trio-` + sha256 prefix |
| `job_key` / `envelope_key` / `claim_key` / `index_key` / `result_key` | `server/queue/trio_store.py` key layout (result prefix always `trio`, bus-424 ruling) |
| `JobStore` + `Backend` trait + `MemoryBackend` | `trio_store.JobStore` semantics: idempotent submit, open-job scan, claim/renew/release mutex, put/get result, finish |

## Scope note (B01 vs B02)

B01's batch map names `queue_service.py` as the source; the store
semantics here are the store-agnostic core (`JobStore` over the
`Backend` trait) that B02 (`crates/queue-store`) builds on. B02 owns
the transports — Upstash Redis REST and the SQLite fallback — plus the
repo layer (`trio_repo.py`); this crate implements neither transport
and holds no credentials.

## What it deliberately does NOT do yet

- No JSON parsing: `validate_envelope` takes a parsed `Envelope`. A
  non-object body is a parse-layer refusal at the HTTP service, not a
  core case.
- No transports (see B02 above); `MemoryBackend` carries the same
  command surface and expiry semantics as `LocalSqliteStore` for tests
  and local use.
- No HTTP service: the queue-service routes are a later piece (B05
  assess-server / stack wiring).

## Product list

`validate_envelope` takes the product list as a parameter — the source
of truth stays `js/products.js` (vigiles / ignis / medicus); this crate
never hardcodes a copy of it.

## Build and test

```sh
cargo test -p queue-core   # zero dependencies, std only (SHA-256 + base64 in-crate)
```

Tests mirror `tests/queue-python/test_queue.py`'s envelope cases and
job-store round-trips, plus SHA-256 known vectors (including the
1,000,000-byte padding boundary) and strict-base64 rejections.

## Status / compile gates

Per `BATCHES.md`: a batch is DONE when it compiles at both gates
(Milo's VM = gate 1, the boss's Mac = gate 2) and its ported tests
pass. This crate compiled and passed 12/12 tests on Rowan's VM; gate
1 (Milo) and gate 2 (Mac) are still pending. Python originals stay
untouched as fallback until then. Spark stays held; this crate makes
no model calls and holds no credentials.
