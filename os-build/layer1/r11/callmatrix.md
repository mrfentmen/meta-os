# callmatrix — Round 11 record

Source: `services/callmatrix/callmatrix.goose` · Test: `services/tests/t109_callmatrix_r11.goose`
(plus existing `t69_callmatrix`) · Status: RUNS (t69, 28 checks)

## 1. Limits — PROVEN

`LIMITS.md` lists no constant for this service; the table's bound is `SVC_COUNT`, which is a
count rather than a byte cap, and `t109` drives both sides of it.

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SVC_COUNT` | 31 | `callmatrix.goose` | driven | `t69` asserts every id 1..31 has a non-empty row; `t109` asserts `cm_bit(31) == 1<<31` and `cm_bit(32) == 0`, `cm_row(32) == 0`, and that 32 may not call itself |
| matrix width | 31 rows × `i64` | `var matrix: Row[SVC_COUNT]` | not a limit | the row is a bitmask; there is no request size to exceed, only ids, and both ends are driven |

No row can be partially written: `cm_set` assigns `caller` and `allow` in one function, and
`cm_row` denies a row whose `caller` field does not match the index, so an uninitialised table
fails closed.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| a pair not in the table | `E_DENIED` | `t69`: `cm_check(SVC_FS, SVC_NET) == E_DENIED`; `t109`: `cm_check(SVC_LOGFMT, SVC_NET) == E_DENIED` |
| caller id 0 or > `SVC_COUNT` | `E_INVAL` | `t69`: `cm_check(999, SVC_LOG) == E_INVAL`; `t109`: `cm_check(0, SVC_LOG)` and `cm_check(SVC_LOG, 32)` |
| callee id 0 or > `SVC_COUNT` | `E_INVAL` | `t69`: `cm_check(SVC_FS, 0)`; `t109`: `cm_check(SVC_LOGFMT, 0)` |
| unknown service pair when asked through `cm_allows` | `false` | `t109`: logfmt→net, logfmt→supervisor, bootlog→storage, display→audit |

The split is deliberate and tested: a denial is policy and belongs to the table's owner; an
invalid id is a caller bug and belongs to the caller's author.

## 3. Restart — NOT APPLICABLE

The matrix is static data rebuilt by `cm_init()`, which zeroes every row and re-applies the
`cm_set` calls. A supervisor restart loses nothing and cannot leave a half-built table: the
registry is expected to call `cm_init` before the first check, and an uncalled table denies
everything (fail-closed). There is no file and no cross-restart continuity to prove.

## 4. Contract — PROVEN

| direction | other | call | in the matrix? |
|---|---|---|---|
| in | supervisor registry | `cm_allows(caller, callee)` / `cm_check(caller, callee)` | n/a — this is the table being consulted, not an edge |
| in | any service, at startup | `cm_mask(caller)` for a startup record | n/a |
| out | none | — | — |

**FINDING:** the table has no row for itself. `callmatrix` is not among `SVC_*`; it is the
permission function, not a participant, so it cannot be called through the registry it answers
for. That is a design choice, but it means a compromised table cannot be audited by asking the
table — the supervisor's startup record is the only witness. Filed here for room 1 rather than
changed, because adding an id is an append-only decision (ids are also supervisor service
numbers).

## 5. Load — NAMED GAP

`LOAD callmatrix ops=3100 ok=300 refused=2800`
RUNS pass=29 fail=0 · `LOAD callmatrix ops=3100 ok=300 refused=2800`

100 passes over all 31 ids, asking the fs row every time. 3100 is ten times the table's width ten
times over; the counts are structural — fs allows storage, log, and itself (self-calls need no
bit) — so the assertion is that the loop's arithmetic and the table agree, not a performance
measurement. The self-call is exempt from the mask/check comparison for the same reason.

## 6. README truth pass — PROVEN

`services/callmatrix/README.md` said `WRITTEN (not COMPILED)` and "nothing in it has been
compiled or run", while `t69_callmatrix` has run it 28 times green. The status now says RUNS with
the test and check count; "Not verified" now names only what remains — the freestanding link and
a kernel-hosted start. The failure-behaviour section was accurate (`E_DENIED` vs `E_INVAL`) and
stays.
