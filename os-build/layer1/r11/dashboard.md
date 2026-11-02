# dashboard — Round 11 record

Source: `services/dashboard/dashboard.goose` ·
Test: `services/tests/t111_dashboard_r11.goose` · Status: RUNS (reached by
`tests/t89_dashboard`, 50 checks)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `DF_MAX_KIND` | `4` | `dashboard.goose` | driven by `t111` | kind 0 and kind 5 are refused with `E_INVAL`; kinds 1-4 are accepted |
| `DF_MAX_AGE_MS` | `60000` | `dashboard.goose` | driven by `t111` | a 60001 ms window is refused, 60000 is accepted and reads back |

Both are mapped to `t89_dashboard` in `LIMITS.md`; `t111` crosses the range edge rather than
only naming the constants. The per-kind default windows (CPU/NET 2000, MEM 5000, DISK 30000)
are also asserted at both sides of the boundary.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| unknown kind (0, or past `DF_MAX_KIND`) | `E_INVAL` | "kind 0 is refused", "a kind past DF_MAX_KIND is refused" |
| a negative percentage, CPU over 100% | `E_INVAL` | "a negative percentage is refused", "CPU over 100% is refused" |
| a zero or over-max staleness window | `E_INVAL` | "a zero window is refused", "a window past DF_MAX_AGE_MS is refused" |
| a sample stamped earlier than the previous one | `E_STATE` | "a backwards clock is refused" |

Network bytes are deliberately not a percentage: `df_put(DF_NET, 150, 0)` is accepted, and
the test asserts that difference so a later "range check everywhere" change cannot silently
cap a byte rate at 100.

## 3. Restart — NAMED GAP

Every sample is static memory in this process. A restart returns all four metrics to
`DF_NEVER` until their producers sample again; the labels say `never`, not `0`, which is the
correct post-restart answer but is still a loss of the last known figures. No supervisor
restart was run, so continuity is not claimed: **the loss is the last sample of every
metric, and the dashboard's rule is that a gap is labelled, not filled.**

## 4. Contract — PROVEN

Imports: `common.err.err`. No service is imported and no service function is called.

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | log | none in code | declared: `cm_set(SVC_DASHBOARD, ... SVC_LOG ...)` — DORMANT |
| out | supervisor | none in code | declared — DORMANT |
| out | watchdog | none in code | declared — DORMANT |
| out | session | none in code | declared — DORMANT |
| out | settings | none in code | declared — DORMANT |
| in | — | none | no row in `callmatrix.goose` includes `SVC_DASHBOARD` |

`FINDING: no service in the matrix is allowed to call the dashboard, and no caller imports
it.` The feed is currently produced and read by the same surface, so there is no second
party to prove an edge. Room 1 should decide whether the face reads it across a permission
boundary (then a caller row is needed) or inside one process (then the row is noise).

## 5. Load — NAMED GAP

The load loop records 1000 samples (ten times a 100-sample batch) across the four kinds at
increasing timestamps, with one deliberately out-of-range sample per hundred so the refusal
path is exercised under volume as well as at rest.

RUNS pass=35 fail=0 · `LOAD dashboard ops=1000 ok=990 refused=10`

## 6. README truth pass — PROVEN

`services/dashboard/README.md` was already true and is left unchanged: it states RUNS with
`t89_dashboard` and the measured `RUNS=1 FAILS=0`, names all six surface functions, and
describes the never/stale/fresh rule exactly as the code implements it. No sentence needed
rewriting, so none was rewritten — an annotated README would have been a worse outcome than
an untouched correct one.
