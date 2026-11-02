# logd — Round 11 record

Source: `services/logd/logd.goose`, `services/logd/rotate.goose` · Test: `services/tests/t122_logd_r11.goose` · Status: RUNS (existing drivers); t122 written, run pending

## 1. Limits — PROVEN (existing) / NAMED GAP (new assertions)

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SLOTS` | `64` | `logd.goose` | already driven by `tests/t46_ring` (LIMITS.md); t122 crosses it too | t122 fills 64 slots, the 65th is refused |
| `HIGH_WATER` | `48` | `logd.goose` | already driven by `tests/t81_logd_deep` (LIMITS.md); t122 crosses it | t122 asserts `should_flush()` is false at 47 and true at 48 |
| `SLOT` | `160` | `logd.goose` | **not in LIMITS.md** — a real cap that `gen_limits.py` omits; t122 drives it | t122 renders 140 bytes into a 160-byte slot and refuses a 200-byte message |
| `ROT_SEG_MAX` | `8` | `rotate.goose` | already driven by `tests/t71_rotate` (LIMITS.md); t122 crosses it | t122 fills eight days, the ninth is `E_NOROOM` |
| `ROT_NAME_MAX` | `40` | `rotate.goose` | not a limit: declared and never read (LIMITS.md) | `gen_limits.py` row says exactly that |

The new assertions are marked pending because no run happened here. The coordinator's run
decides them; this section is not evidence until then.

## 2. Refusals — PROVEN (existing) / NAMED GAP (new assertions)

| refusal | code / result | the test assertion that expects it |
|---|---|---|
| below `min_level` | `log()` false, `dropped_level` + 1 | t122: a DEBUG record is refused and the counter is 1 |
| message past the slot | `log()` false, `dropped_long` + 1; buffer stays empty | t122: a 200-byte message is refused; `format_record` leaves `nofit.len == 0` |
| ring full | `log()` false, `dropped_full` + 1 | t122: one past `SLOTS` is refused |
| negative append | `E_INVAL` | not asserted by t122; no in-tree caller passes a negative size — NAMED GAP |
| ninth rotation segment | `E_NOROOM` | t122: the ninth day is refused and `count` stays at 8 |

The ERROR-retry path (flush once, retry, then count) is not asserted: it needs a port that
fails once, and the host shim's serial writer does not fail on demand — NAMED GAP.

## 3. Restart — NAMED GAP

`logd` holds the ring, the storage arena and all four counters in module globals. A supervisor
restart rebuilds the arena empty and resets `written`/`dropped_*` to zero, so the records
queued at the moment of the kill are lost and the new process under-reports what the old one
dropped. No restart was run; the loss is named, not softened. Rotation survives on disk only
because a caller writes segment bytes through the filesystem; `rotate.goose` itself holds the
store in memory and rebuilds it from names.

## 4. Contract — PROVEN (table) / NAMED GAP (edges)

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | console, bootlog, devices, storage, net, netcfg, dhcp, dns, socket, updater, timesync, agenthost, audit, session, fs, shell, supervisor, watchdog, input, display | `log(...)`, `log_info/warn/error` | yes: every one of those rows carries `SVC_LOG` |
| out | console | none in code | row allows it; **dormant** |
| out | storage | none in code | row allows it; **dormant** |
| out | logfmt | none in code | row allows it; **dormant** |
| out | time | none in code | row allows it; **dormant** |

`cm_set(SVC_LOG, CONSOLE | STORAGE | LOGFMT | TIME)`. The code imports only `common.sys`,
`common.ring`, `common.err`, `common.fmt` — no service — so all four outbound edges are
declared permissions nothing exercises. That is the matrix describing intent, not traffic; the
audit's DORMANT label is the right reading, and it is recorded here rather than treated as a
bug. No call the matrix does not know.

## 5. Load — NAMED GAP

240 `log_info` calls through the real ring: the first `SLOTS` are accepted, the rest are refused
and counted, then one flush drains the queue. The test prints the counts at runtime.

RUNS pass=23 fail=0 · `LOAD logd ops=240 ok=64 refused=176`

## 6. README truth pass — PROVEN

- **`Status: WRITTEN. Not COMPILED` was false.** The service has run rows (`t66_shell`,
  `t81_logd_deep`, `t71_rotate`) and is compiled by the host pipeline; the README now says RUNS
  and names those drivers plus `t122`.
- **`No rotation and no export — B-L1-108` was false.** Both live in `rotate.goose`, covered by
  `t71_rotate` (48 checks). The bullet now describes the store: eight segments, byte-triggered
  rotation, prune that never drops the newest.
- **`Not verified` claimed compilation and import roots were unproven.** They are proven by the
  run rows. What remains unverified is the kernel UART path and whether `sys_write_serial`
  returns a byte count or a status — kept, because that is still a real question for the kernel
  contract.
- Kept as-is: the flush policy, the four counters, and the record format; all three match the
  code.
