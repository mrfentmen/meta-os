# COUNTS — the limit ledger, closed (BF4-17 / E1, 2026-11-02)

Final count, measured on this tree:

**95 limit-like constants. 78 proven by a running test. 9 not limits (1 bit flag, 8 dead
declarations). 8 real limits no host driver can reach. 0 UNPROVEN.**

The task that opened this round said "close the rest of the 49". The 49 was the UNPROVEN
set before `t78`, `t79` and `t80` landed; regenerating the table after them took it to 20,
and this pass accounts for the last 20 — five driven, fifteen classified with reasons. No
constant is left in the UNPROVEN bucket, and none was moved out of it by renaming it.

## Evidence

```
$ python3 os-build/layer1/gen_limits.py
limits: 95  proven: 78  flags: 1  dead: 8  unreachable: 8  unproven: 0

$ os-build/layer1/run_native.sh
ran: 59 programs  RUNS=59  FAILS=0  built-not-run=5

$ grep t103 os-build/layer1/host/run_rows.txt
tests/t103_limits_rest|RUNS|11|0|
```

`t103_limits_rest` drives the five host-reachable constants: `SK_GEN_MAX` (263
open/bind/close cycles through the generation wrap), `SCROLL_MAX` (264 newlines on a 2-row
console, history clamps at 256), `UPD_CONTENT_MAX` (4096 bytes read, 4097 refused),
`UPD_REC_KEEP` (five confirmations keep four), and `HISTORY_SLOTS` (the ring's capacity is
the constant). Two of those needed a real guard added first: `content_get` had no length
check against `UPD_CONTENT_MAX`, and the history depth had no reader, so the clamp could
not be observed. The guard and the accessors are in the same commit.

## Not limits (9)

| constant | value | why |
|---|---|---|
| `MOD_CAPS` | 8 | a modifier bit, not a capacity: the CAP heuristic matched it by name |
| `ROT_NAME_MAX` | 40 | declared only; the enforcement uses literals (a follow-up: wire the constant) |
| `AK_CAPS` | 4 | declared only; the audit table is typed with the literal 4 |
| `EX_NAME_MAX` | 32 | declared only; the example's name is a fixed 7-byte literal |
| `DL_LIT_MAX` | 64 | declared only; literal bytes are bounded by the literal pool slice |
| `FS_MAX_DEPTH` | 16 | declared only; `paths.goose` bounds depth by path length, not this |
| `CK_MAX_BLOCKS` | 64 | declared only; fsck's mark arrays use the literal 128 |
| `CK_MAX_INODES` | 128 | declared only; same arrays |
| `BO_MAX` | 30 | declared only; `bo_count()` returns 29 |

A dead constant is not a passing limit. The table says so, and the follow-up for each is
either "wire it where the literal is" or "delete it" — not "write a test that mentions it".

## Unreachable on the host (8)

| limit | value | structural reason |
|---|---|---|
| `SET_MAX` | 24 | only seven setting ids exist and `st_import` refuses any other, so the 24-entry table cannot fill |
| `SH_OUT_MAX` | 4096 | the cap is the caller's buffer; no in-tree command emits 4 KiB into `sh_exec` |
| `EX_REC_MAX` | 128 | a tick record's fields bound it at about 45 bytes |
| `CFG_TEXT_MAX` | 256 | the cap is the read size handed to `fs_read`; the filesystem's caps are driven by t65 |
| `DL_OPS_MAX` | 4 | `DeltaFile.ops` is `[..4]`; the array type is the enforcement |
| `STALL_LIMIT` | 100000 | needs a frozen kernel clock; the host shim's clock advances |
| `DNS_QUERY_MAX` | 512 | `DNS_NAME_MAX` bounds the encoding to 261 bytes; the check is defensive |
| `DEP_MAX` | 32 | the boot table holds 29 services, so `deps_stop_plan` cannot produce 32 |

Each one becomes provable when its bound changes: the kernel test for `STALL_LIMIT`, a
larger boot table for `DEP_MAX`, an argument-taking service surface for `SET_MAX`, a
command that emits 4 KiB for `SH_OUT_MAX`. Until then, `LIMITS.md` names them and does not
call them proven.

## What "proven" means here

A constant is proven when a driver that RUNS reaches the enforcing code with a value on the
wrong side — by naming the constant, or through the override table that records exactly
which check does it. A green suite that mentions a constant by accident does not count.
`ROT_NAME_MAX` and `AK_CAPS` used to be credited that way through the override table; the
occurrence audit found them declared and unread, so they moved to "not limits" and the
proven count dropped by two. That is the ledger being honest, not a regression.
