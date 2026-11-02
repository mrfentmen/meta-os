# queue-core — behaviour record (B109)

Read from `crates/queue-core/src/lib.rs` (679 lines, one module) at
`main` @ `6d8d54e`. Every claim names a line range. The crate is
zero-dependency: SHA-256 and strict base64 are implemented in-crate
(`lib.rs:28-159`).

## What it does

| Area | Code | Behaviour |
|---|---|---|
| SHA-256 | `lib.rs:28-116` | FIPS 180-4, lowercase hex, mirrors `hashlib.sha256`; `K256` table at `28-38`, `sha256_hex` at `40-116` |
| Base64 | `lib.rs:105-159` | Strict decode with Python `b64decode(validate=True)` semantics; alphabet at `105-115`, `base64_decode` at `118-159` |
| Envelope types | `lib.rs:161-179` | `EnvelopeImage { data_url, byte_length, sha256 }` and `Envelope { version, kind, id, product, timestamp, image }`; both `PartialEq + Eq` |
| Job id | `lib.rs:181-193` | `trio-` + first 32 hex of `sha256(product + "\0" + timestamp + "\0" + frame)`, byte-identical to `buildQueueJob` in `server/queue.mjs:99-136` |
| Envelope validation | `lib.rs:195-227` | Returns `Some(error)` or `None`; the caller supplies `product_ids` (`js/products.js` stays the source) |
| Key layout | `lib.rs:229-249` | `job_key`, `envelope_key`, `claim_key`, `index_key`, `result_key`; result prefix is always `trio` (`lib.rs:247-249`) |
| Backend trait | `lib.rs:255-266` | Nine Redis-shaped commands; the crate owns no transport |
| In-memory backend | `lib.rs:278-381` | Same command surface as the Python SQLite fallback; expired string keys read as absent (`live`, `lib.rs:289-299`) |
| JobStore | `lib.rs:383-494` | Submit (idempotent), fields, envelope, open-jobs scan, result read, claim/renew/release, put result, finish |
| Tests | `lib.rs:496-679` | 12 unit tests: SHA-256 vectors, base64 strictness, envelope refusals, key layout, store round-trips |

## What it refuses

All messages are literal strings in the code:

| Refusal | Line |
|---|---|
| `not a trio-assessment v1 envelope` (version or kind) | `lib.rs:196-198` |
| `envelope has no job id` (empty id) | `lib.rs:199-201` |
| `unknown product '<product>'` | `lib.rs:202-204` |
| `envelope has no timestamp` | `lib.rs:205-207` |
| `image.dataUrl is not a JPEG data URL` | `lib.rs:209-211` |
| `image.dataUrl does not base64-decode` | `lib.rs:212-215` |
| `image.byteLength does not match the decoded frame` | `lib.rs:216-218` |
| `image.sha256 does not match the decoded frame` | `lib.rs:219-221` |
| `invalid base64 length` / `invalid base64 padding` / `padding before end of base64 input` / `invalid base64 character` | `lib.rs:121`, `130`, `136`, `142` |

Store refusals are booleans, not messages: a second `submit` returns
`(jid, false)` (`lib.rs:400-403`), a lost claim race returns `false`
(`lib.rs:444-451`), and `renew_claim` returns false when the claim key
is gone (`lib.rs:464-466`).

## What it writes down

The crate itself writes no files and no logs. It defines the records a
backend stores (`lib.rs:398-492`):

- `<ns>:<jid>` — hash: `status`, `kind`, `version`, `product`,
  `timestamp`, `created_at`; then `claim`, `claimed_at`, `lease_until`,
  `lease`; then `status`, `note`, `done_at`.
- `<ns>:<jid>:job` — the envelope JSON string the caller supplies.
- `<ns>:<jid>:claim` — the claim holder, written with `SET NX EX`.
- `<ns>index` — sorted set of `jid` scored by `created_at`.
- `trio:<jid>:result` — the result JSON string the caller supplies.

## Findings (B112, reported not fixed)

1. **`job_envelope` and `get_result` do not parse JSON.**
   `lib.rs:424-426` and `439-441` return the stored string. Python's
   `JobStore.job_envelope` and `get_result`
   (`server/queue/trio_store.py:403-411`, `421-431`) parse and return
   `None` for invalid JSON or a non-object. A corrupt body therefore
   reads as `Some(corrupt_string)` here.
2. **All hash values are strings.** `job_fields` is
   `HashMap<String, String>` (`lib.rs:420-422`), so `created_at`,
   `claimed_at`, `lease_until` and `lease` are stringified
   (`lib.rs:411`, `454-457`). Python stores them as integers
   (`trio_store.py:385-398`, `433-441`). A caller comparing numbers
   would have to parse first.
3. **The stored envelope can disagree with the validated envelope.**
   `submit` takes `envelope_json` separately (`lib.rs:398`) and stores
   it verbatim (`lib.rs:409-410`); Python serializes the same dict it
   validated (`trio_store.py:380-397`). A caller can file a valid
   `Envelope` with unrelated JSON under its key.
4. **The result body can disagree with its key.** `put_result` takes
   `job_id` and `result_json` independently (`lib.rs:473-475`); Python
   keys by `result_env["job_id"]` from the body itself
   (`trio_store.py:454-456`).
5. **The unknown-product message is not verbatim for exotic product
   names.** Python uses `{...!r}` (`queue_service.py:71`), which escapes
   quotes and backslashes; `lib.rs:203` uses `'{}'`, so a product
   containing `'` or `\` produces a different string.
6. **`claim` does not require the job to exist.** `lib.rs:444-462`
   writes the claim key and job hash for any id. Python does the same
   (`trio_store.py:433-441`), so this is ported behaviour, not drift —
   recorded because it is surprising.
7. **`renew_claim` proves no ownership.** It is `SET XX`
   (`lib.rs:464-466`), so any caller can renew a live claim; Python is
   the same (`trio_store.py:443-444`).

## Spec-versus-code pass (B112)

The comments in `lib.rs` were read against the code and agree with it;
the thin place was the crate README, which was corrected in this pass:

- `README.md` "What it deliberately does NOT do yet" now names the
  missing-image and non-string id/timestamp refusals as parse-layer
  cases, and states that `job_envelope`/`get_result` return raw strings
  while `submit`/`put_result` can store a body that disagrees with its
  key (findings 1, 3 and 4).

`lib.rs` was left byte-identical so every line citation above stays
true; no behaviour was changed.
