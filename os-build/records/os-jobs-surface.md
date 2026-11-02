# `os-jobs` — public surface inventory

B034. Every exported name in `crates/os-jobs/src/lib.rs`, one line
each, marked **used** (referenced by the crate, its tests, or another
crate in this repo today) or **unused** (declaration only). "Used" here
means a real reference, not a doc link. No other crate calls
`os_jobs::*` (see `os-jobs-callers.md`), so every "used" mark is
in-crate or test-only unless noted.

## Constants

| Name | Line | State | Note |
|---|---:|---|---|
| `LEASE_DEFAULT` | 76 | used | `PostArgs::default`, heartbeat fallback |
| `DEFAULT_NS` | 78 | **unused** | no reader; namespace is a constructor argument |
| `SIG_VERSION` | 80 | used | `post` signing |
| `NICKCLAIM_TTL` | 84 | used | `nick_claim` set/expire |
| `PRESENCE_TTL` | 87 | used (test only) | asserted equal to `NICKCLAIM_TTL` at 4024 |

## Traits and types

| Name | Line | State | Note |
|---|---:|---|---|
| trait `Clock` | 102 | used | `SystemClock`, `FakeClock`, `JobQueue` |
| struct `SystemClock` | 108 | used | public default clock; construct directly |
| struct `FakeClock` | 121 | used | tests and the fault suite |
| enum `SetMode` | 143 | used | `Nx`/`Xx` in claim, nick claim, `FakeStore` |
| trait `JobStore` | 151 | used | the backend seam; `FakeStore` and three test doubles implement it |
| struct `FakeStore` | 177 | used | in-crate tests and this lane's tests |
| struct `StoreError` | 92 | used | every `JobStore` method |
| struct `JobQueue<S>` | 942 | used | the command surface |
| struct `CmdOutcome` | 847 | used | every command return |
| struct `PostArgs` | 866 | used | `post` input |
| struct `Keyring` | 735 | used | `parse_keyring`, `read_keyring_file`, `verify_job` |
| enum `Verdict` | 814 | used | `verify_job`, `verify` |
| enum `VerifyError` | 834 | used | `verify_job`, `claim`, `verify` |
| enum `Value` | 2294 | used | `environment_jobs_record`, `environment_lines` |
| enum `EnvInput` | 2303 | used | `environment_jobs_record` |
| struct `EnvRepo` | 2359 | used | `environment_lines` |
| struct `EnvBus` | 2369 | used | `environment_lines` |
| struct `EnvBudget` | 2376 | used | `environment_lines` |
| struct `EnvRecord` | 2388 | used | `environment_lines` |

## Functions

| Name | Line | State | Note |
|---|---:|---|---|
| `url_quote` | 319 | used | `nickclaim_key`; parity tests |
| `url_unquote` | 335 | used | `nick_holder`, `nick_claim` |
| `python_repr` | 359 | used | error text in rooms, artifacts, keyrings |
| `clean_room` | 375 | used | `post`, `bus_key` |
| `bus_key` | 390 | used | `announce` |
| `seq_key` | 401 | used | `post` |
| `job_key` | 405 | used | commands and tests |
| `spec_key` | 409 | used | `job_get`, `post` |
| `claim_key` | 413 | used | claim/heartbeat/done/sweep |
| `index_key` | 417 | used | post/list/sweep |
| `nickclaim_key` | 423 | used | `nick_holder`, `nick_claim` |
| `sha256` | 429 | used | HMAC, tests |
| `hmac_sha256` | 511 | used | signatures, tests |
| `hex_digest` | 532 | used | signatures, tests |
| `ct_eq` | 538 | used | signature compare |
| `json_escape` | 553 | used | canonical JSON, `list --json` |
| `canonical_json` | 588 | used | v1/v2 payloads |
| `canonical_payload_v1` | 609 | used | `sign_job_v1` |
| `canonical_payload_v2` | 623 | used | `sign_job_v2` |
| `sign_job_v1` | 645 | used | `verify_job`, tests |
| `sign_job_v2` | 650 | used | `post`, `verify_job`, tests |
| `parse_artifact_ref` | 672 | used | `attach`, `post`, `validate_artifact_refs`; parity-tests has its own copy |
| `split_artifacts` | 711 | used | `post`, `attach`, `list --json` |
| `validate_artifact_refs` | 722 | used | `post`, `attach` |
| `parse_keyring` | 759 | used | `read_keyring_file`, tests |
| `read_keyring_file` | 801 | used | post/claim/verify |
| `normalize_req` | 921 | used | `post` |
| `valid_id` | 934 | used | `job_get` |
| `environment_jobs_record` | 2318 | used | environment tests; no production caller |
| `format_brief_time` | 2452 | used | `environment_age_label`, tests |
| `environment_age_label` | 2467 | used | `environment_lines` |
| `environment_lines` | 2479 | used | environment tests; no production caller |

## Methods

| Method | Line | State | Note |
|---|---:|---|---|
| `FakeClock::new` / `advance` | 125/130 | used | tests |
| `FakeStore::new` | 184 | used | tests |
| `Keyring::get` | 741 | used | `post`, `verify_job` |
| `Keyring::kids_sorted` | 748 | used | unknown-kid error |
| `Verdict::as_str` | 822 | used | `claim` announce, `verify` |
| `JobQueue::new` | 952 | used | tests |
| `JobQueue::set_nick` | 964 | used | tests |
| `JobQueue::now` | 969 | used | every command's timestamps |
| `JobQueue::pushes_to` | 974 | used | tests, this lane's error paths |
| `JobQueue::store_set_raw` | 1008 | used | tests (tamper simulations) |
| `JobQueue::store_hset_raw` | 1018 | used | tests (tamper simulations) |
| `JobQueue::store_get_raw` | 1027 | used | tests |
| `JobQueue::job_get` | 1035 | used | every command, tests |
| `JobQueue::nick_holder` | 1059 | used | `creator_warning`, tests |
| `JobQueue::nick_claim` | 1070 | used | tests |
| `JobQueue::nick_conflict_holder` | 1103 | used (tests) | not called by a command |
| `JobQueue::creator_warning` | 1113 | used | `show`, `claim` |
| `JobQueue::verify_job` | 1189 | used | `claim`, `verify` |
| `JobQueue::post` | 1343 | used | tests |
| `JobQueue::list` | 1498 | used | tests |
| `JobQueue::show` | 1618 | used | tests |
| `JobQueue::attach` | 1653 | used | tests |
| `JobQueue::claim` | 1699 | used | tests |
| `JobQueue::heartbeat` | 1864 | used | tests |
| `JobQueue::progress` | 1900 | used | tests |
| `JobQueue::done` | 1939 | used | tests |
| `JobQueue::blocked` | 1993 | used | tests |
| `JobQueue::cancel` | 2046 | used | tests |
| `JobQueue::requeue` | 2088 | used | tests |
| `JobQueue::sweep` | 2181 | used | tests |
| `JobQueue::verify` | 2253 | used | tests |

## Public fields that are part of the surface

- `StoreError(pub String)` (92) — the message is read by every
  `RELAY_ERROR` line.
- `PostArgs` fields (866-904) — all are set by callers; `Default`
  fills the documented defaults.
- `CmdOutcome.code/out/err` (847-864) — read by every test and the
  future CLI.
- `Keyring.keys/default_kid` (735-738) — read by `post`/`verify_job`.
- `EnvRepo/EnvBus/EnvBudget/EnvRecord` fields (2359-2394) — read by
  `environment_lines`.
- `JobQueue.store/clock/ns/nick/host/announcements` (942-949) — public
  so tests can inject a fault, advance time, and read announcements.
  A production wrapper should not need them, but they are load-bearing
  for the current test style.

## Bottom line

Two names are dead surface: `DEFAULT_NS` and (without its test)
`PRESENCE_TTL`. Everything else has a reader inside the crate. **No
name has a reader outside the crate**, which is the integration gap
recorded in `os-jobs-callers.md`, not a naming problem.
