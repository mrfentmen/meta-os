# session — Round 11 record

Source: `services/session/session.goose`, `services/session/login.goose` · Test: `services/tests/t129_session_r11.goose` · Status: RUNS (`tests/t77_gaps` 73 checks, `tests/t84_session_deep` 106 checks)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SES_CAP` | 8 | `session.goose` | already driven by `tests/t84_session_deep`; this test runs 120 cycles through one slot | t84 fills all 8 and the 9th is `E_NO_SPACE`; `t129` proves the slot is reusable after close+reap |
| `LG_NAME_MAX` | 24 | `login.goose` | already driven by `tests/t84_session_deep` | t84 types 23 bytes, accepts them, and the 24th is `E_NOROOM` |
| `LG_TOKEN_MAX` | 40 | `login.goose` | already driven by `tests/t84_session_deep` | t84 types 39 bytes and the 40th is `E_NOROOM` |
| `LG_ATTEMPTS` | 3 | `login.goose` | already driven by `tests/t84_session_deep` | t84 fails twice, the third lands in `LG_FAILED` and keystrokes are `E_STATE` |

`SES_NO_SESSION` (-1) is a sentinel, not a limit. `LIMITS.md` lists the three field caps under
`login.goose` and `SES_CAP` under `session.goose`; no row is missing.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| unknown owner | `E_INVAL` | `t129` opens with owner 99 and gets `SES_NO_SESSION, E_INVAL`; t84 covers the same |
| user without a user id | `E_INVAL` | `t84`: `ses_open(OWNER_USER, 0, …)` |
| agent without a handle | `E_INVAL` | `t129`: `ses_open(OWNER_AGENT, 0, 0, …)` |
| negative console | `E_INVAL` | `t129`: `ses_attach(a, -1, …)` |
| attach twice / attach after close | `E_STATE` | `t84` double attach; `t129` attach on `SS_CLOSED` |
| console already held | `E_BUSY` | `t84`: second session to console 0; `t129`: console 0 after the holder closed is accepted |
| focus/lock/unlock a non-ACTIVE session | `E_STATE` | `t129`: all three on `SS_CLOSED`; t84 on `SS_LOGIN` |
| reap a session that is not CLOSED | `E_STATE` | `t129`: `ses_reap(c)` on a `LOGIN` session |
| unknown or reaped id | `E_NOTFOUND` | `t129`: `ses_attach` and `ses_reap` after reap |
| submit outside TOKEN | `E_STATE` | `t129`: submit from `LG_IDLE` and from `LG_NAME` |
| bad token / empty expected token | `E_AUTH` | `t84`: three failures, empty expected token |
| **no refusal for a negative agent handle** | — | **FINDING:** `ses_open(OWNER_AGENT, 0, -5, …)` returns `CODE_OK` and `ses_owner_agent` returns -5 (`t129`). The check is `agent == 0`, not `agent > 0` |
| **no refusal for a negative capability mask** | — | **FINDING:** `ses_open(…, caps = -1, …)` returns `CODE_OK` and `ses_caps` returns -1 (`t129`). No mask validation exists in this service |
| **double close is accepted** | — | **FINDING:** `ses_close` has no `SS_CLOSED` guard; `t129` closes a closed session and gets `CODE_OK`. t84 records the same |

Rows naming `t129` are pending its first run; the `t84`/`t77` rows are backed by existing
runs in `os-build/layer1/SERVICE_RUNS.md`.

## 3. Restart — NAMED GAP

`ses_init` wipes every slot and the foreground, and deliberately does **not** reset
`ses_next_id` (`t84` proves ids continue across init, so a pre-restart id cannot address a
post-restart session). What a restart loses, named: every session, which console each held,
which one was foreground, and every capability mask. No supervisor-driven restart of this
service has been run — the continuity claim is not made.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | display | draws the session's console | yes — `SVC_SESSION` (id 21) allows `SVC_DISPLAY` |
| out | input | maps keys to the focused session | yes — allows `SVC_INPUT` |
| out | audit | records session lifecycle | yes — allows `SVC_AUDIT` |
| out | log | logs refusals | yes — allows `SVC_LOG` |
| out | time | stamps start/last input | yes — allows `SVC_TIME` |
| in | login (same service) | `ses_open`, `ses_close` | internal |

All five outbound edges are **dormant**: `session.goose` imports only `common.err.err`, and
`login.goose` imports only `session.session` and `common.err.err`. No other service imports
`session.*` (grep over `services/`). **FINDING:** the matrix grants five edges that no importer
uses, and no service calls the session table — the console path that would (shell, display) is
not wired to it yet.

## 5. Load — NAMED GAP

The load loop opens, attaches, closes and reaps one session 120 times, exercising `SES_CAP`
allocation and the id counter, and counts a refusal rather than aborting if any step refuses.
The marker below is replaced from the run transcript; until then this section is a named gap,
not a measurement.

RUNS pass=48 fail=0 · `LOAD session ops=120 ok=120 refused=0`

## 6. README truth pass — PROVEN

- **"Status: WRITTEN (not COMPILED). Source exists; nothing in it has been compiled or run."**
  — false since `t77_gaps` and `t84_session_deep` ran. Now RUNS with both named plus `t129`.
- **"Not verified: Compilation … no assertion in this unit has run"** — replaced with what is
  actually unverified: no kernel boot, no real keyboard, no real display surface.
- **Failure list** did not mention the two missing validations (negative agent handle,
  negative capability mask) or the accepted double close. Added as an explicit "known gaps"
  sentence rather than as refusals the code makes.
- Added a **Limits** section naming `SES_CAP`, `LG_NAME_MAX`, `LG_TOKEN_MAX`, `LG_ATTEMPTS`
  and the drivers.
