# `crates/agent-runtime` — behaviour record (B097, 2026-11-02)

Read from `crates/agent-runtime/src/lib.rs` as it stands on `main`.
Every claim carries a `file:line` reference. Status words:

- **CARRIED** — present in the port and exercised by the crate's tests.
- **REFUSED** — a documented refusal branch that writes a failed result.
- **GAP** — the Python source does something this port does not carry;
  listed in `os-build/records/agent-runtime-gaps.md`.

Source: `server/queue/trio_agent.py`. The crate is a library, no
binary target (`crates/agent-runtime/Cargo.toml:1-4`, `src/lib.rs:1-21`).

## What it does

One job at a time, synchronously. `Agent::serve_job` (`lib.rs:72-89`)
runs four steps in this order:

1. **Idempotency before the claim** (`lib.rs:73-77`): an existing result
   at `trio:<jid>:result` finishes the job `done` with
   `idempotent skip: result already present, not re-billed` and returns
   `Outcome::Skipped`. No generator call is made.
2. **Atomic claim** (`lib.rs:78-80`): `JobStore::claim` is a SET NX with
   a caller-supplied lease. Losing the race returns `Outcome::Lost`
   and writes nothing.
3. **Idempotency again under the lease** (`lib.rs:81-86`): a result that
   appeared between the two checks wins; same `done` note and
   `Outcome::Skipped`.
4. **Serve** (`lib.rs:91-155`).

## What it refuses, branch by branch

Every refusal below writes a **failed result envelope** and marks the
job failed; none of them writes an assessment.

| # | Condition | Result `error` | Source |
|---|---|---|---|
| R1 | Envelope missing, not valid JSON, or not an object | `job envelope missing or unparseable in the store` | `lib.rs:92-98` |
| R2 | `image.dataUrl` does not start with `data:image/jpeg;base64,` | `envelope image is not a JPEG data URL` | `lib.rs:102-107` |
| R3 | Base64 payload does not decode | `envelope image does not base64-decode` | `lib.rs:108-114` |
| R4 | SHA-256 of the decoded bytes differs from `image.sha256` | `frame sha256 mismatch against the envelope` | `lib.rs:115-119` |
| R5 | Generator returns `Err` on the first call | `generation failed: <e>` | `lib.rs:120-128` |
| R6 | Generator returns `Err` on the correction retry | `generation failed: <e>` (with the first model/latency) | `lib.rs:132-142` |
| R7 | Output still fails `validate_assessment` after exactly one retry | `model output failed validateAssessment (after one correction retry): <errors>` | `lib.rs:144-147` |

R7 is the only path that makes two generator calls. A valid first
output makes exactly one (`lib.rs:129-131`). The retry carries the
validation errors joined with `"; "` as its `correction`
(`lib.rs:134-136`).

A claim race is **not** a refusal: `Outcome::Lost` leaves the job and
the store untouched (`lib.rs:78-80`), because the winner owns it.

## What it writes down

| Key | Shape | Written by | Source |
|---|---|---|---|
| `trio:<jid>:result` | the result envelope, JSON | `put_result`, on ok and on every failure | `lib.rs:152`, `lib.rs:168` |
| `<ns>:<jid>` | hash: `status`, `claim`, `claimed_at`, `lease_until`, `lease` | `JobStore::claim` | `queue-store/src/lib.rs:436-447` |
| `<ns>:<jid>` | hash: `status`, `note`, `done_at` | `JobStore::finish` | `queue-store/src/lib.rs:467-475` |
| `<ns>:<jid>:claim` | NX key holding the nick, expiring with the lease | `JobStore::claim` | `queue-store/src/lib.rs:434-435` |

The result object has exactly the seven fields the ruler specified:
`job_id`, `status`, `assessment`, `error`, `model`, `latency_ms`,
`completed_at` (`lib.rs:148-155`, `lib.rs:163-170`). On success
`assessment` is the validator-passing object and `error` is `null`; on
failure `assessment` is `null` and `error` is a capped string.
`latency_ms` is the generator's measured value; on a retry the two
latencies are added (`lib.rs:137-140`).

## Validation

`validate_assessment` (`lib.rs:179-278`) is the single contract
implementation; `assess-server` calls it rather than keeping a copy
(`crates/assess-server/src/main.rs:566-571`). It checks, in order:

- the value is a JSON object (`lib.rs:181-185`);
- `expected_product` is non-empty, `product` matches it exactly
  (`lib.rs:186-198`);
- `timestamp` is a non-empty string and a real ISO-8601 date with a
  timezone (`lib.rs:200-208`, `lib.rs:321-378`);
- `observations` is an array; each item is an object with non-empty
  `category`/`description`, a string `evidence`, and `confidence`
  present as null or a number in `0..=1` (`lib.rs:210-235`);
- `assessment` is an object with non-empty `category`, string
  `summary`, string-array `uncertainty`, boolean
  `requires_human_review` (`lib.rs:237-260`);
- `processing` is an object with non-empty `model` and `latency_ms`
  present as null or a non-negative number (`lib.rs:262-272`).

An empty `observations` array is accepted: the loop has no minimum
length (`lib.rs:211-214`). Extra fields are ignored. The full error
list is returned, not the first error.

## Findings (B100: docs versus code)

1. **`now_iso` is not ISO-8601.** The Python original emits
   `YYYY-MM-DDTHH:MM:SS.mmmZ` (`server/queue/trio_agent.py:81-84`).
   The Rust function returns epoch milliseconds as a decimal string
   (`lib.rs:23-33`), and the doc comment said "Millisecond ISO-8601
   UTC with Z" until this pass. The comment now states the real
   behaviour; the port gap is G2.
2. **The crate header claimed a heartbeat the code does not have.**
   The header said "atomic claim (SET NX + lease, heartbeat while
   generating)" but `serve_job` never renews the claim. The header now
   names the not-carried rules; the gap is G1.
3. **`relay_notify_payload` panicked on every ok result.** The ok
   branch sliced `format!(...)[..500.min(200)]`, i.e. byte index 200,
   which is out of bounds for a normal-length message. Fixed to cap by
   characters at 500, matching `trio_agent.py:99-101`; the failure
   branch got the same 500-character cap (`lib.rs:35-55`).
4. **`finish_failed` sliced by bytes.** `&error[..len.min(500)]` and
   `&error[..len.min(200)]` panic on a multi-byte boundary. Both are
   now char-safe (`lib.rs:161-162`).
5. **The out-of-range message prints `Option`.** `check_nullable_number`
   formats `{hi}` where `hi` is `Option<f64>`, so the text reads
   `out of range 0..Some(1)` (`lib.rs:312`). Cosmetic, not a contract
   change; left as a finding.
6. **A result with no `job_id` produces no relay payload.** Python
   would still format the job id as `None`; the Rust function returns
   `None` (`lib.rs:36-37`). No caller exists, so the divergence is
   recorded rather than fixed.
7. **The relay hook is not wired.** `relay_notify_payload` builds the
   body, but `serve_claimed` never calls it and nothing POSTs
   (`lib.rs:91-155`). Python does both (`trio_agent.py:86-119`,
   `trio_agent.py:204-214`, `trio_agent.py:315-318`). Gap G3.
