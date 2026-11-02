# queue-core — Python behaviours not carried (B113)

The task text says "the Python original (os/ tree)". This crate's
originals are not under `os/`: they are `server/queue/queue_service.py`
and `server/queue/trio_store.py` (the crate doc names both,
`crates/queue-core/src/lib.rs:1-24`). This list is against those files.

## 1. Validation cases the Rust types cannot receive

| Python behaviour | Source | Why it is absent in Rust |
|---|---|---|
| `envelope is not a JSON object` | `queue_service.py:66-67` | `validate_envelope` takes a parsed `Envelope`; JSON parsing is the HTTP layer's job (`lib.rs:16-21`) |
| `envelope has no image object` | `queue_service.py:76-78` | `Envelope.image` is a required `EnvelopeImage` (`lib.rs:170-178`) |
| non-string `id` refusal | `queue_service.py:70-71` | `Envelope.id` is `String` (`lib.rs:173`) |
| non-string `timestamp` refusal | `queue_service.py:74-75` | `Envelope.timestamp` is `String` (`lib.rs:174`) |
| `unknown product None` (missing product) | `queue_service.py:72-73` | `Envelope.product` is `String`; a missing product is a parse/construction refusal |

These are not ported as tests because a Rust caller cannot construct the
input without unsafe code. They belong to the HTTP layer that builds
`Envelope` from JSON — a later piece named in the crate README.

## 2. JSON-aware JobStore reads

| Python behaviour | Source | Rust today |
|---|---|---|
| `job_envelope` parses JSON and returns `None` for invalid/non-object | `trio_store.py:403-411` | returns the raw stored `String` (`lib.rs:424-426`) |
| `get_result` parses JSON and returns `None` for invalid/non-object | `trio_store.py:421-431` | returns the raw stored `String` (`lib.rs:439-441`) |
| `put_result(result_env)` serializes a dict and keys by `result_env["job_id"]` | `trio_store.py:454-456` | takes `job_id` + `result_json` separately (`lib.rs:473-475`) |
| `submit(envelope)` serializes the dict it validates | `trio_store.py:380-397` | takes `envelope_json` separately (`lib.rs:398`) |

Task candidates (do not port here):

- **QC-G1** — add a JSON-boundary adapter that parses/validates stored
  strings before returning them, matching `trio_store.py:403-431`.
- **QC-G2** — make `put_result` derive the key from the body's
  `job_id`, or validate that the two agree.
- **QC-G3** — make `submit` serialize the validated `Envelope`, or
  validate that `envelope_json` matches it.

## 3. Integer-typed hash values

Python writes `created_at`, `claimed_at`, `lease_until` and `lease` as
integers (`trio_store.py:385-398`, `433-441`). Rust stringifies every
hash value (`lib.rs:411`, `454-457`). `job_fields` returns
`HashMap<String, String>` (`lib.rs:420-422`). Task candidate:

- **QC-G4** — decide the typed shape (string map + accessors, or a
  `JobFields` struct with typed timestamps) before another crate reads
  these fields.

## 4. Transports and the service (deliberately out of this crate)

`UpstashStore`, `LocalSqliteStore`, `open_store`, the fallback
labelling, host resolution and the HTTP routes
(`trio_store.py:152-371`, `queue_service.py:93-220`) are not here.
`crates/queue-store` owns the transports and `crates/assess-server`
owns the HTTP surface (crate README scope note). They are listed so the
boundary is named, not silently dropped.

## 5. Parity cases from `tests/queue-python/test_queue.py` (29 tests)

The B01 spec says the 29 Python tests are the bar for B01-B04 jointly.
The crate ports the envelope and JobStore cases only. The unported
cases, with their owners:

- Node-built envelope verifies (`test_queue.py:85`) — no Rust test runs
  Node; the id rule is pinned against `server/queue.mjs:99-136` instead.
- Budget: estimate math, counts, stop-at-budget, under-budget
  (`test_queue.py:121-146`) — `crates/os-budget`.
- Result shape exact keys (`test_queue.py:148`) — HTTP layer.
- Serve result + idempotent skip (`test_queue.py:189`), health names
  fallback (`354`), POST idempotent + pending/unknown (`360`), tampered
  envelope 400 (`374`) — `crates/queue-store` + `crates/assess-server`.
- Self-correction: invalid model output, retry once, invalid twice,
  valid first (`test_queue.py:227-316`) — `crates/assess-server`.
- Direct request shape and guardrail (`test_queue.py:389`) —
  `crates/guardrail`.
- No key/helper clean refusal (`test_queue.py:452`) — `crates/queue-store`.
- Relay notify ok/failed/unset/dead (`test_queue.py:512-560`) —
  `crates/relay`.
- Host resolution: env host, full URL, credential URL, unconfigured,
  full round trip (`test_queue.py:629-690`) — `crates/queue-store`.

No exclusion-blocked case is claimed green here.
