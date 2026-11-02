# audit — Round 11 record

Source: `services/audit/audit.goose`, `retention.goose` ·
Test: `services/tests/t105_audit_r11.goose` · Status: RUNS (t60; t105 run by the coordinator)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `AUD_REC_BUDGET` | 4096 | `audit.goose` | driven by `t105` §3 and `tests/t60_audit` | `t105` lands a record exactly on 4096, then the next record is refused |

`AUD_SLOT` (128) is a slot number in the record head, not a compared limit; `AUD_DIGEST` (8) is
the digest width. LIMITS.md lists only `AUD_REC_BUDGET`, and that row is now driven twice.

## 2. Refusals — PROVEN

| refusal | code | the assertion that expects it |
|---|---|---|
| body larger than the budget | `AUD_NO_REC` (-1) | `t105` "a 4097-byte body is refused with AUD_NO_REC" |
| buffer full | `AUD_NO_REC` (-1) | `t105` "the next record is refused" |
| body copy past the caller's cap | `-1` | `t105` "a body larger than the caller cap is refused" |
| body copy at an offset no head occupies | `-1` | `t105` "a bad offset body copy is refused" |
| a chain with one changed body byte | `audit_verify_buf` names the seq | `t105` "a changed body byte fails at seq 1" |
| a buffer cut mid-record | `audit_verify_buf` verifies what it has | `t105` "a truncated buffer verifies the records it has" |

Two different refusals return the same `AUD_NO_REC`, and that is deliberate but worth stating:
an **oversize body** does not move `audit_dropped_count` (it is the caller's bug, nothing was
lost), while a **full buffer** does (a record was genuinely dropped). `t105` asserts both sides.

## 3. Restart — NAMED GAP

The buffer is process memory and nothing flushes it on exit. `audit_bytes()` exists so the
host can write the block to storage, but no caller in this tree does that on shutdown, so a
restart loses every record written since the last explicit flush. The chain's guarantee is
about a buffer that survives — it does not survive by itself.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | none (library) | — | — |
| out | none | — | — |
| internal | `audit` | `retention.goose` imports `audit.audit` | n/a (same service) |

`audit.goose` imports only `common.err`. The matrix row for id 20 grants storage, time and log —
all **dormant**: the service writes its own buffer and does not import any of the three. No
call exists that the matrix does not know; no finding for room 1.

## 5. Load — PROVEN (expected line; run fills it)

80 small records (ten times a normal batch of eight) after one boot record. The test asserts
each got the next sequence and prints:

`LOAD audit ops=80 ok=80 refused=0`

RUNS pass=25 fail=0 · `LOAD audit ops=80 ok=80 refused=0`

## 6. README truth pass — PROVEN

The README said **WRITTEN (not COMPILED)** and "nothing in it has been compiled or run"; the
native corpus has run `t60_audit` and now `t105`. Rewritten:

- status line now says RUNS with the tests and the date;
- "Offers to Layers 5–6" says until booted, not until compiled;
- "Not verified" names boot, restart flushing and the non-cryptographic digest instead of
  claiming no toolchain;
- a `## Limits` section names `AUD_REC_BUDGET` and the exact-fit rule;
- the failure paragraph now keeps the two `AUD_NO_REC` cases apart (oversize vs full).

The "no `svc_entry`" deviation is true and was left alone.
