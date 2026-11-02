# Contract — `updater_client`

Status: **RUNS** — `services/tests/t90_updater_client.goose`, on the host shim. Not started by
a supervisor; nothing starts a service yet.

## What it is

The desktop half of an update: ask, refuse, apply, report. It mirrors the image updater's
contract (`services/updater`, which verifies manifests and digests) and owns the client-side
policy — when to ask, what to refuse, and what the tile shows while it happens.

## The four refusals, in the order they are checked

1. **STOP wins over everything.** A STOP file in the image is checked first, before the rate
   limit and before the signature. Stopping is the answer to "should this machine update
   right now", and nothing else is. Counted in `uc_stop_count`. It also wins over an offer
   already on the table: the file is read *between* the offer and the apply, so a STOP that
   arrives then withdraws the offer (`uc_available_version` back to 0, state back to `IDLE`)
   and `uc_apply` then returns `E_STATE`. Without that, "checked first" would be true of the
   check and false of the only step that installs anything.
2. **Verification before availability.** Digest and signature must both pass before a
   version is recorded as available. A manifest that fails leaves the previous state
   untouched and the version is *not* offered — counted in `uc_verify_count`.
3. **No rollback.** A version at or below the applied one is a refusal, not "nothing to do":
   a server that goes backwards is a server that is being spoofed or was rolled back, and
   either way this client is not the place to find out which. Counted in
   `uc_rollback_count`.
4. **A rate limit that reports itself.** Two checks inside `UC_MIN_INTERVAL_MS` (60 s) is a
   client bug, and it returns its own code so the caller can tell "no update" from "not
   asked". Counted in `uc_rate_count`.

All four are above the error range (9001..9006) so a caller can test "refused" as a group.

## State machine

`IDLE → CHECKING → AVAILABLE → APPLYING → DONE`, with `FAILED` reachable from `APPLYING`.
`uc_busy()` is true in `CHECKING` and `APPLYING`; a second `uc_check` while busy is
`E_BUSY` and does not move the state. `uc_retry()` is the only transition out of `FAILED`,
and it returns to `IDLE` — it does not re-check by itself.

## API

| function | returns | notes |
|---|---|---|
| `uc_init(now_ms)` | — | IDLE, nothing applied, counters zero |
| `uc_seed_applied(version)` | code | the caller supplies the truth after a restart |
| `uc_check(stop, version, digest_ok, sig_ok, now_ms)` | code | the four refusals, in order |
| `uc_apply(ok)` | code | `APPLYING` → `DONE` or `FAILED` |
| `uc_retry()` | code | `FAILED` → `IDLE` only |
| `uc_status()` | `(state, last_code)` | what the tile draws |
| `uc_available_version()` / `uc_applied_version()` | version | `UC_NEVER` (-1) for none |
| counters | `uc_check_count`, `uc_stop_count`, `uc_verify_count`, `uc_rate_count`, `uc_rollback_count`, `uc_applied_total`, `uc_failed_total` | one per refusal, so a log can say *why* |

## Where the applied version lives

**Not here.** `uc_init` starts from "nothing applied" and the caller seeds the truth with
`uc_seed_applied` from the same record the boot path reads. A version remembered only in
this process would forget every update across a restart and re-offer the version that is
already installed.

## Failure modes, all driven by the test

- **STOP present** — `UC_REFUSED_STOP`, no version recorded; an existing offer is withdrawn (`t94`).
- **Bad digest / bad signature** — `UC_REFUSED_VERIFY`, previous state untouched.
- **Same or older version** — `UC_REFUSED_ROLLBACK`.
- **Immediate re-check** — `UC_REFUSED_RATE`; the count moves, the state does not.
- **Apply fails** — `FAILED`, `uc_failed_total` +1, and `uc_retry` is the only exit.
- **Check while busy** — `E_BUSY`, no state change.

## Restart semantics

State and counters are memory. The applied version is re-seeded by the caller, which is the
designed path and not a workaround: a client that persisted its own idea of the installed
version would be a second source of truth about what is on the disk.

## Limits

`UC_MIN_INTERVAL_MS` 60000, `UC_NEVER` -1, versions are positive ints. No storage of its own.
