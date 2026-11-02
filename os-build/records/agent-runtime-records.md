# `crates/agent-runtime` — record shapes, worked examples (B102)

Every shape below is produced by the code named beside it. Values are
examples with the same types the code writes; nothing here is a schema
the crate does not enforce. The result key is fixed by
`queue-store/src/lib.rs:127-129`; the job/claim hashes by the same
crate's `JobStore::submit`/`claim`/`finish` (`:404-475`).

## 1. Result envelope — status `ok`

Written by `serve_claimed` (`lib.rs:148-155`), key
`trio:<jid>:result` (`queue-store/src/lib.rs:127-129`).

```json
{
  "job_id": "trio-7f3a",
  "status": "ok",
  "assessment": {
    "product": "ignis",
    "timestamp": "2026-11-02T05:59:00.000Z",
    "observations": [
      {
        "category": "visible smoke",
        "description": "grey plume above the roofline",
        "evidence": "frame centre",
        "confidence": 0.72
      }
    ],
    "assessment": {
      "category": "visible smoke",
      "summary": "Smoke is visible; origin is not determinable from one frame.",
      "uncertainty": ["wind direction unknown"],
      "requires_human_review": true
    },
    "processing": {
      "model": "muse-spark-1.3",
      "latency_ms": 812
    }
  },
  "error": null,
  "model": "muse-spark-1.3",
  "latency_ms": 812,
  "completed_at": "1793512740123"
}
```

Field notes:

- `job_id` — the id the caller passed to `serve_job`, echoed verbatim
  (`lib.rs:153`).
- `status` — literal `"ok"`; the only success value (`lib.rs:150`).
- `assessment` — the exact object that passed
  `validate_assessment`; the crate never rewrites it (`lib.rs:147-151`).
- `error` — `null` on success; the key is always present
  (`lib.rs:151`, `lib.rs:166`).
- `model` — the generator's model string, unmodified (`lib.rs:126`,
  `lib.rs:153`).
- `latency_ms` — the generator's measured milliseconds; on a correction
  retry the two values are added with saturation (`lib.rs:137-140`).
- `completed_at` — `now_iso()`, which today is epoch milliseconds as a
  **string**, not ISO-8601 (`lib.rs:23-33`; gap G2).

## 2. Result envelope — status `failed`

Written by `finish_failed` (`lib.rs:157-171`).

```json
{
  "job_id": "trio-7f3b",
  "status": "failed",
  "assessment": null,
  "error": "frame sha256 mismatch against the envelope",
  "model": null,
  "latency_ms": null,
  "completed_at": "1793512750456"
}
```

Field notes:

- `status` — literal `"failed"` (`lib.rs:164`).
- `assessment` — always `null`; no partial or fabricated object is
  written (`lib.rs:165`).
- `error` — the refusal string, capped at **500 characters**, char-safe
  (`lib.rs:161`, `lib.rs:166`). The original `&error[..500]` panicked on
  a multi-byte boundary; fixed in the B100 pass.
- `model` / `latency_ms` — the values known at the failure point; `null`
  when no call completed (`lib.rs:167`). A failure after a generation
  carries the model and summed latency (`lib.rs:138-142`).
- `completed_at` — same epoch-millis string as above.

## 3. Job hash — after claim

`JobStore::claim` (`queue-store/src/lib.rs:432-449`) writes these fields
into `<ns>:<jid>`; `serve_job` reads none of them except through the
store's own semantics.

```text
status      = claimed
claim       = trio-agent            (the Agent.nick passed to claim)
claimed_at  = 1793512740            (unix seconds, decimal)
lease_until = 1793513040            (claimed_at + lease)
lease       = 300                   (seconds, as given)
```

Field notes:

- `status` moves `open` -> `claimed` -> `done`/`failed`
  (`queue-store/src/lib.rs:414`, `:438`, `:471`).
- `claim` holds the nick, not the process id; two agents with the same
  nick are indistinguishable in the hash (`lib.rs:78-80`).
- `lease_until` is informational; the NX key `<ns>:<jid>:claim` is what
  actually enforces the race (`queue-store/src/lib.rs:434-435`).

## 4. Claim key

```text
key   = trio:trio-7f3a:claim
value = trio-agent
ttl   = 300 seconds (SET NX EX)
```

Written by `JobStore::claim`; released by `JobStore::finish`
(`queue-store/src/lib.rs:434-435`, `:474`). An expired or released key
lets the next agent claim the same job — which is why the idempotency
re-check exists before the envelope is read (`lib.rs:81-86`).

## 5. Finish note

Written by `JobStore::finish` into `<ns>:<jid>`
(`queue-store/src/lib.rs:467-475`):

```text
status  = done
note    = assessment by trio-agent
done_at = 1793512741
```

On failure the note is the error capped at **200 characters**
(`lib.rs:162`, `lib.rs:170`). The full error, capped at 500, is in the
result envelope. Two different caps are deliberate: the hash is a
short operational note, the result is the record.
