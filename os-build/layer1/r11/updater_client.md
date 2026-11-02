# updater_client — Round 11 record

Source: `services/updater_client/updater_client.goose` · Test: `services/tests/t139_updater_client_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `UC_MIN_INTERVAL_MS` | `60000` | `updater_client.goose:51` | driven here and by `tests/t90_updater_client` | 59,999 ms after an accepted check returns `UC_REFUSED_RATE`; exactly 60,000 is accepted |
| `UC_NEVER` | `-1` | `updater_client.goose:52` | not a limit | sentinel for "no check yet"; no caller can cross it |

`UC_MIN_INTERVAL_MS` is not in `LIMITS.md` (the generated scan does not cover this service), so
the table's absence is a generator gap, not an untested limit.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| negative version | `E_INVAL` | `t139`: `uc_check(..., -1, ...)` |
| seed below the applied version | `E_ROLLBACK` | `t139`: seed 5, then seed 4 |
| apply with nothing available | `E_STATE` | `t139`: apply twice |
| retry when not failed | `E_STATE` | `t139`: second `uc_retry` |
| apply reports failure | `E_VERIFY` | `t139`: `uc_apply(false)` |
| STOP present | `UC_REFUSED_STOP` | `t139`: also proves the open offer is withdrawn |
| inside the rate window | `UC_REFUSED_RATE` | `t139`: 59,999 ms |
| digest or signature failed | `UC_REFUSED_VERIFY` | `t139`: false digest, then false signature |
| version below the applied one | `UC_REFUSED_ROLLBACK` | `t139` |
| version equal to the applied one | `UC_NO_UPDATE` | `t139` |

The counters are proven independent: after one STOP, one rate, two verify and one rollback
refusal, each counter holds exactly its own count.

## 3. Restart — NAMED GAP

Every field is process memory. The applied version is explicitly the caller's truth, seeded with
`uc_seed_applied` after a restart; the counters and any open offer are lost. That is the documented
design (the README says the image is the authority), so the loss is named rather than a defect —
but a restart mid-apply leaves a `DONE` state that never happened, which the caller must not read
as an install.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `updater` | the check/apply contract | declared on `SVC_UPDATER_CLIENT`, dormant: the source imports no service |
| out | `socket`, `net` | fetch | declared, dormant |
| out | `log`, `time` | records and stamps | declared, dormant |
| out | `notify` | "update available" | declared, dormant |
| in | — | — | **FINDING: no caller's row allows `SVC_UPDATER_CLIENT`** |

**FINDING:** the client mirrors a contract whose signature half does not exist
(`sig_verify_manifest` returns `E_UNSUPPORTED`). Its `signature_ok` parameter is therefore a
caller-supplied boolean, not a verification: a caller that passes `true` without checking has
told the client a signature was verified. The type cannot enforce who computed it; the README and
`updater.md` carry the finding.

## 5. Load — NAMED GAP

The load loop runs 100 checks, one per 60-second window, and requires 100 `UC_AVAILABLE` answers
and a check counter of 100. Ten times a normal check batch; no quota applies.

RUNS pass=51 fail=0 · `LOAD updater_client ops=100 ok=100 refused=0`

## 6. README truth pass — PROVEN

- The README was already true: `RUNS`, `t90` named, the four refusals in their check order, each
  counter named, and the seeded-applied design stated. Only the proof line changed, to name
  `t139` beside `t90`.
- No stale "not compiled" claim was present, so none was rewritten.
