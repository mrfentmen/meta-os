# updater_client — the desktop half of an update: ask, refuse, apply, report

Status: **RUNS** — `tests/t90_updater_client` passes in the native host corpus
(`run_native.sh t90_updater_client`, measured 2026-11-02: `RUNS=1 FAILS=0`), and
the program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 5.

## What it is

The client side of the image updater's contract (`services/updater`). It does not
fetch, verify a signature itself, or write an image — it records what was asked,
what was refused, and what was applied, so the state machine has one owner.

## The four refusals, in the order they are checked

1. **STOP wins over everything.** A STOP file present in the image is checked
   first, before the rate limit and before the signature. Stopping is the answer
   to "should this machine update right now", and nothing else is.
2. **A failed verification never becomes "available".** The version is recorded
   as available only after the digest *and* the signature both pass. A manifest
   that fails leaves the previous state untouched.
3. **No rollback.** A manifest offering a version at or below the applied one is
   a refusal, not a "nothing to do". A server that goes backwards is either
   spoofed or was rolled back, and this client is not the place to find out which.
4. **A rate limit that reports itself.** Two checks in a second is a client bug;
   it returns its own code, so the caller can tell "no update" from "not asked".

Each refusal has its own counter — `uc_stop_count`, `uc_verify_count`,
`uc_rate_count`, `uc_rollback_count` — because a single "refused" total would hide
which of the four is firing.

## Where the applied version lives

Not here. `uc_init` starts from "nothing applied" and the caller seeds the truth
with `uc_seed_applied(version)`. On a machine that boots the same image twice,
the authority for "what is installed" is the image, not a service's memory.

## Surface

| Function | Answers |
|---|---|
| `uc_check` | one check, with the four refusals and their codes |
| `uc_apply` / `uc_retry` | the outcome of an apply, and the retry path |
| `uc_status` | state and last code, in one call |
| `uc_available_version`, `uc_applied_version` | the two versions that matter |
| `uc_check_count`, `uc_applied_total`, `uc_failed_total` | how often, how many |
| `uc_state_name`, `uc_code_name` | the strings a report can print |

## Where the proof is

`services/tests/t90_updater_client.goose` (the happy path and the check order) and
`services/tests/t139_updater_client_r11.goose` (the seeded truth, independent counters, and the
apply/retry path).
