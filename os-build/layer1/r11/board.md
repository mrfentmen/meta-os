# board — Round 11 record

Source: `services/board/board.goose` ·
Test: `services/tests/t106_board_r11.goose` · Status: RUNS (t91; t106 run by the coordinator)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `BD_MAX_ROOMS` | 4 | `board.goose` | driven by `t106` §1 and `t91_board` | the fifth room returns `E_NO_SPACE`; the count stays 4 |
| `BD_MAX_POSTS` | 24 | `board.goose` | driven by `t106` §4 and `t91_board` | the 25th post returns `E_NO_SPACE`; the count stays 24 |
| `BD_ROOM_NAME_MAX` | 16 | `board.goose` | driven by `t106` §1 | a 16-byte name returns `E_NOROOM` (the bound is exclusive) |
| `BD_POST_MAX` | 96 | `board.goose` | driven by `t106` §2 | a 96-byte text returns `E_NOROOM` (exclusive bound) |

No limit was removed. LIMITS.md already lists all four against `t91_board`; `t106` drives each
edge directly as well.

## 2. Refusals — PROVEN

| refusal | code | the assertion that expects it |
|---|---|---|
| empty room name, comma in a name | `E_INVAL` | `t106` "an empty name is E_INVAL", "a comma is E_INVAL" |
| duplicate room name | `E_STATE` | `t106` "a duplicate name is E_STATE" |
| room name at 16 bytes | `E_NOROOM` | `t106` "a 16-byte name is E_NOROOM" |
| fifth room | `E_NO_SPACE` | `t106` "the fifth room is E_NO_SPACE" |
| post to an unknown room | `E_NOTFOUND` | `t106` "an unknown room is E_NOTFOUND" |
| empty text, newline in text | `E_INVAL` | `t106` two assertions |
| text at 96 bytes | `E_NOROOM` | `t106` "a 96-byte text is E_NOROOM" |
| 25th post | `E_NO_SPACE` | `t106` "the 25th post is E_NO_SPACE" and the refused counter |
| malformed import line, post in an undefined room | `E_CORRUPT` | `t106` §5, plus "applies nothing" |

## 3. Restart — NAMED GAP

Rooms and posts are process memory. `bd_export` / `bd_import` can carry the whole board across a
restart and the round trip is proven by `t106` §5, but nothing calls export on shutdown or
import on start-up today. A supervisor restart therefore starts an empty board. The export
format is not the gap; the missing automatic call is.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | none (library) | — | — |
| out | none | — | — |

`board.goose` imports only `common.err`. The matrix row for id 30 grants net, storage, log, time
and notify — every edge is **dormant**; the row is the policy the face layer will be held to,
not a description of calls today. No call exists that the matrix does not know; no finding for
room 1.

## 5. Load — PROVEN (expected line; run fills it)

240 posts (ten times `BD_MAX_POSTS`) into one room. The log accepts 24 and refuses 216 with
`E_NO_SPACE`; the test asserts both counts and the refused counter, then prints:

`LOAD board ops=240 ok=24 refused=216`

RUNS pass=39 fail=0 · `LOAD board ops=240 ok=24 refused=216`

## 6. README truth pass — PROVEN

The README was already true: status RUNS with `t91_board`, the three design choices match the
code (`bd_post` refuses at `BD_MAX_POSTS`, ids only go up, `bd_fetch` uses `since_id`), the
surface table names functions that exist, and the persistence paragraph matches `bd_export` /
`bd_import` atomicity. No edit was made. The only correction is this record: `E_NO_SPACE` is
counted in `bd_refused_total`, which the README implies but does not say.
