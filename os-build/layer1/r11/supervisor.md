# supervisor — Round 11 record

Source: `services/supervisor/{supervisor,deps,bootorder}.goose` · Test:
`services/tests/t135_supervisor_r11.goose` · Status: RUNS

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `NAME_MAX` | `32` | `supervisor.goose` | driven by a test | `LIMITS.md` row `tests/t52_supervisor`; `t135` additionally refuses a name of exactly 32 bytes and accepts 31 |
| `MAX_SERVICES` | `32` | `supervisor.goose` | driven by a test | `LIMITS.md` row `tests/t75_supervisor_load`; `t135` fills all 32 and expects `E_NOROOM` on the 33rd |
| `HANDLE_GEN_MAX` | `65535` | `supervisor.goose` | already driven by `tests/t83_sup_deep` | `t135` asserts the handle arithmetic and a stale handle resolving to `-1`; it does not wrap 65 535 generations, because that would need 65 535 releases |

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| registration with an empty name, or one at `NAME_MAX` | `E_INVAL` | `t135` `sup_register(empty[..0])`, `sup_register(long[..32])`; `long[..31]` is accepted |
| a 33rd registration | `E_NOROOM` | `t135` fills to 32, then registers `s32` |
| duplicate name, table not full | `E_STATE` | `t135` registers the 31-byte name twice before filling |
| duplicate name, table full | `E_NOROOM` — **FINDING**, capacity is checked first | `t135` registers `s01` again after the 32nd slot |
| illegal transition (`STOPPED`→`RUNNING`, `RUNNING`→`RUNNING`) | `E_STATE` | `t135` asserts both are refused **and that the state did not move** |
| bad slot index | `E_INVAL` | `t135` `sup_set_state(999, …)` |
| release of a slot that is not `STOPPED` | `E_STATE` | `t135` releases a `RUNNING` slot |
| heartbeat from a slot that is not up | `E_STATE` | `t135` beats on a `STOPPED` slot |
| a disabled service, a self-dependency, a dependency that is not running | `E_STATE` | `t135` `sup_can_start` on slots carrying each shape |
| a dependency index past the table | `E_INVAL` | `t135` a slot registered with `needs = 99` |
| a bad policy, `base_ms <= 0`, `max_ms < base_ms`, negative budget | `E_INVAL` | `t135` four `sup_set_policy` refusals |
| `sup_restart_ready` outside `RESTARTING` | `E_STATE` | `t135` calls it from `STARTING` |
| unknown name lookup | `E_NOTFOUND` with handle `0` | `t135` `sup_lookup("nope")` |

**FINDING (refusal order).** `sup_register` checks `table_len >= MAX_SERVICES` before
`sup_find`, so a duplicate name submitted at a full table returns `E_NOROOM` and the duplicate
is not reported. Both refuse, so nothing is accepted that should not be; but a caller that wants
to tell "your name is already taken" from "the table is full" cannot, and the message it shows
the operator will be wrong. Recorded, not fixed: reordering two checks changes which refusal a
full table reports first, and that is the service owner's call. The test asserts both orders.

## 3. Restart — PROVEN (decision), NAMED GAP (real process)

`sup_decide` and `sup_on_exit` are proven in-process by `t135` for all four decisions
(`RT_LEAVE`, `RT_GIVE_UP`, `RT_NOW`, `RT_AFTER`) and for both ways a budget ends: the third
crash under `max_restarts = 2` gives up and stays `FAILED`; a 30 s healthy run resets the
count and the delay to `base_ms`.

The gap is named: **no process is restarted**, because there is no spawn call. What a restart
would preserve is nothing in this file — the table lives in the supervisor's memory, so a
supervisor restart loses every entry, every generation and every restart count. The table is
rebuilt by registration, not reloaded. That is the loss, stated rather than implied.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | `shell` (`SVC_SHELL`) | `ps`, start/stop commands | yes — `SVC_SHELL` allows `SUPERVISOR` |
| in | `watchdog` (`SVC_WATCHDOG`) | liveness decisions | yes |
| in | `dashboard` (`SVC_DASHBOARD`) | service feed | yes |
| in | `example` (`SVC_EXAMPLE`) | the template's registry use | yes |
| in | `agenthost` (`SVC_AGENTHOST`) | agent lifecycle | yes |
| out | `logd`, `watchdog`, `session`, `audit`, `time`, `agenthost` | — | declared on `SVC_SUPERVISOR`, **dormant**: this file imports `common.err` and `common.ring` only |

`common.ring` is a library, not a service, so it correctly has no matrix row. No call this
service makes is missing from the matrix.

## 5. Load — PROVEN

640 name lookups: 500 of a registered service and 140 of an unknown name, so both the found
and the refused path are exercised at ten times a normal registration pass.

RUNS pass=79 fail=0 · `LOAD supervisor ops=640 ok=500 refused=140`

## 6. README truth pass — PROVEN

- `Status: **WRITTEN**` and the long "no Goose toolchain … nothing is COMPILED" paragraph →
  `Status: **RUNS**`, naming `t52_supervisor`, `t75_supervisor_load`, `t83_sup_deep` and the
  new driver. The measured run rows already said RUNS; the README contradicted them.
- The struct snippet was stale: it omitted `policy`, `max_restarts`, `base_ms`, `max_ms` and
  `gen`, and showed `var table: ServiceEntry[..32];` without the initialiser the source has.
  It now matches the source.
- `The complete legal set … twelve pairs` was wrong: the code has **fourteen**. The two missing
  edges, `STOPPED → FAILED` (out-of-band crash) and `RESTARTING → FAILED` (budget spent while
  waiting), are now in the table with the reason the source gives for each.
- `Not compiled, not run. No toolchain on this Mac.` → removed; it is false as of the run rows.
- `Verification` still says "Not compiled, not run"; rewritten to state what the four drivers
  prove and that no process spawn exists.
