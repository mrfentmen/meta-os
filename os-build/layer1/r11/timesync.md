# timesync — Round 11 record

Source: `services/timesync/timesync.goose` · Test: `services/tests/t137_timesync_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `NTP_MAX_OFFSET_MS` | `86400000` | `timesync.goose:47` | driven here and by `tests/t80_limit_drivers2` | a reply whose offset is beyond a day returns `E_INVAL`, and the settled offset is unchanged (`t137`); t80 drives the negative side |
| `NTP_PACKET` | `48` | `timesync.goose:36` | driven here | a 10-byte packet returns `E_CORRUPT`; a built request is exactly 48 bytes |
| `NTP_SMEAR_DIVISOR` | `10` | `timesync.goose:52` | driven here | 15 ms of error gives a first step of exactly 1 ms |
| `NTP_SMEAR_MIN_MS` | `1` | `timesync.goose:53` | driven here | the last 1 ms of error still moves (a zero step would never close) |

`NTP_PACKET`, `NTP_SMEAR_DIVISOR` and `NTP_SMEAR_MIN_MS` are not in `LIMITS.md`; they are read by
the code and crossed by `t137`, so `gen_limits.py`'s scan is the gap, not the coverage.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| packet shorter than 48 bytes | `E_CORRUPT` | `t137`: a 10-byte packet |
| mode is not server (4) | `E_CORRUPT` | `t137`: a client-mode packet |
| stratum 0 (kiss-o'-death) | `E_REFUSED` | `t137`: stratum 0 |
| leap indicator 3 (server unsynchronised) | `E_UNSUPPORTED` | `t137`: LI 3 |
| transmit time zero | `E_CORRUPT` | `t137`: transmit stamp 0 |
| negative delay | `E_CORRUPT` | `t137`: send stamped 490 ms after receive on a 100 ms trip |
| offset beyond a day | `E_INVAL` | `t137`: 100,000,000 ms; t80 negative side |

Every refusal is followed by the invariant that matters: `ts_now_ms(0)` and `ts_pending_ms()` are
unchanged. A refused measurement cannot half-apply.

## 3. Restart — NAMED GAP

The offset, target and last measurement are process memory. `timesync` holds no file and the
supervisor restarts it with `offset_ms = 0`, so wall-clock time falls back by whatever offset had
been applied until the next accepted reply is smeared in. A fresh boot re-syncing is by design
(the source says so); a mid-run restart losing a correction is the same behaviour, stated as a
loss rather than hidden. No continuity test exists because there is no storage binding to hold
the offset.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `socket` | the exchange (send, wait, receive) | declared on `SVC_TIMESYNC`'s row, **dormant**: the source imports no service |
| out | `time` | monotonic clock | declared, dormant |
| out | `log` | accepted/rejected measurements | declared, dormant |
| in | — | — | **FINDING: no caller's row allows `SVC_TIMESYNC`** |

The row says what timesync may reach; no row says who may reach timesync, so a service that calls
it would be denied. That is a matrix gap for room 1, recorded here and not fixed (the file is not
this worker's).

## 5. Load — NAMED GAP

The load loop builds and reads back 100 request stamps with the offset settled, which is ten
times a normal exchange batch for this service. It approaches no quota: timesync has no table and
no rate limit.

RUNS pass=26 fail=0 · `LOAD timesync ops=100 ok=100 refused=0`

## 6. README truth pass — PROVEN

- `services/timesync/README.md` said **WRITTEN (not COMPILED)**; it is `RUNS` — `tests/t77_gaps`
  drives it (73 checks) and `t137` adds the smear. Rewritten.
- "Nothing may rely on them until the layer is COMPILED" → the host drivers rely on them; nothing
  boots them on the kernel yet. Rewritten to say exactly that.
- "Not verified" listed compilation and execution as unverified; compilation has happened and the
  host corpus runs. It now names only what is still true: host execution, not a kernel boot, and
  no real NTP exchange (the socket/timeout owner is the caller).
- Failure list already matched the code (`E_CORRUPT`, `E_REFUSED`, `E_UNSUPPORTED`, `E_INVAL`).
