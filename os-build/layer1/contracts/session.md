# session — contract (Round 7 B, 2026-11-02)

What this service promises, checked against the code as it stands. Status: **RUNS**
as a host process; nothing boots it.

`session.goose` is the table; `login.goose` is the question and the answer. Neither
holds a password — authentication is the caller's, by design, because a credential
check that lives in the layer that also decides who may read the disk is not a check.

## Inputs

| Input | Type | Accepted | Refused |
|---|---|---|---|
| `ses_open(owner, user_id, agent, caps, now_ms)` | 5 × i64 | `owner ∈ {OWNER_USER, OWNER_AGENT}`, a non-zero id for that owner, a free slot | bad owner / missing id → `E_INVAL`; table full → `E_NO_SPACE` |
| `ses_attach(id, console, now_ms)` | i64, i64, i64 | `SS_LOGIN`, `console ≥ 0`, console not held by a live session | wrong state → `E_STATE`; negative console → `E_INVAL`; console taken → `E_BUSY` |
| `ses_focus(id)` | i64 | `SS_ACTIVE` | unknown → `E_NOTFOUND`; any other state → `E_STATE` |
| `ses_lock` / `ses_unlock` | i64 | `ACTIVE`→`LOCKED`, `LOCKED`→`ACTIVE` | any other state → `E_STATE` |
| `ses_close(id)` | i64 | any live session, from any state | unknown → `E_NOTFOUND` |
| `ses_reap(id)` | i64 | a `CLOSED` session | live session → `E_STATE`; already gone → `E_NOTFOUND` |
| `ses_note_input(id, now_ms)` | i64, i64 | any live session | unknown → no-op |
| `login_key(f, c)` | flow, u8 | printable ASCII, backspace, CR/LF | control bytes → `E_INVAL`; field full → `E_NOROOM`; wrong state → `E_STATE` |
| `login_submit(f, expected, owner, who, now_ms)` | flow, slice, 3 × i64 | `LG_TOKEN` and a matching token | empty expected token → `E_AUTH`; mismatch → `E_AUTH`; wrong state → `E_STATE` |

## Outputs

- **Session id:** strictly increasing, never reused, including across `ses_init`.
- **State:** `SS_FREE` 0, `SS_LOGIN` 1, `SS_ACTIVE` 2, `SS_LOCKED` 3, `SS_CLOSED` 4.
- **Input gate:** `ses_accepts_input(id)` is true only for the foreground session in
  `SS_ACTIVE`. This is the single gate the input path consults.
- **Foreground:** `ses_foreground_id()`, and `ses_visible_console()` (-1 when nothing
  is focused).

## Limits (see `LIMITS.md`)

| Constant | Value | Enforced | Proven by |
|---|---|---|---|
| `SES_CAP` | 8 | the 9th `ses_open` is `E_NO_SPACE` | `t84_session_deep` (fill to 8, then refuse) |
| `LG_NAME_MAX` | 24 | 23 accepted, 24 refused | `t84_session_deep` (23 / 24) |
| `LG_TOKEN_MAX` | 40 | 39 accepted, 40 refused | `t84_session_deep` (39 / 40) |
| `LG_ATTEMPTS` | 3 | the third failure moves the flow to `LG_FAILED` and keeps it there | `t84_session_deep` |
| console index | ≥ 0 | negative refused; 63 accepted | `t84_session_deep` |

## Failure modes

| Failure | Behaviour | Counted |
|---|---|---|
| second session on a live console | `E_BUSY`; the session stays in `SS_LOGIN` and keeps no console | — |
| input while locked | `ses_accepts_input` false; `ses_note_input` still records the time | — |
| close without reap | the slot stays occupied: eight closed sessions still fill the table | — |
| agent exits | `ses_close_agent_sessions` closes every session with that handle and returns the count; they land in `SS_CLOSED`, not `SS_FREE` | return value |
| wrong token | attempt counted, back to the **name** prompt (not a token retry), field cleared | `attempts` |
| empty expected token | every login refused (`E_AUTH`) — a config that failed to load must not become a login that accepts anything | `attempts` |
| token compare | constant time in the token length: the whole buffer is visited regardless of where it differs | — |

## Restart semantics

`ses_init` sets every slot `SS_FREE`, clears the foreground, and **does not reset
`ses_next_id`**: ids issued before a restart cannot be reissued after it, so a stale
id cannot reach a new session. The table itself is in `var` module storage, so a
supervisor restart is a fresh address space with no sessions; nothing is persisted.

`ses_open` calls `ses_init` if it has not run, so a service that forgets to initialise
gets a table rather than writes into uninitialised storage.

## Findings (asserted, not fixed)

1. **Double close is accepted.** `ses_close` does not guard `SS_CLOSED`; a second
   close returns `CODE_OK`. It is harmless today because the state is already `CLOSED`
   and the foreground was cleared, but a caller can no longer tell "I closed it" from
   "somebody already did".
2. **`SS_FREE` means two things.** `ses_state(id)` returns `SS_FREE` for a reaped id
   and for an id that was never issued, and for a slot that is unused. A caller cannot
   distinguish "gone" from "never existed" through the accessors.
3. **Close does not free, and nothing in the corpus reaps.** `ses_close` is the
   record; `ses_reap` is the release, and the only caller of `ses_reap` in this tree is
   `t84_session_deep`. The supervisor's exit path has to call it, or the table leaks
   one slot per closed session until `E_NO_SPACE`.
4. **A locked foreground session still reports its console.** `ses_focus` refuses to
   focus a `LOCKED` session, but `ses_visible_console` does not check state, so a
   session locked while focused keeps drawing. The input gate is correct; the visible
   console is not gated.

## Drivers

| Driver | Checks | Covers |
|---|---|---|
| `t40_session` | happy path | open, attach, focus, lock, close, agent close |
| `t77_gaps` | partial | session column of the failure matrix |
| `t84_session_deep` | 106 | double attach, `E_BUSY`, input while locked, double close, `SES_CAP` fill, console boundary, id monotonicity, agent close, `ses_init`/ids across init, full login flow including the 3-attempt lockout and both field boundaries |
