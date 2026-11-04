# `session` — Layer 4, service 25

**Status: COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/session/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — reached by `tests/t77_gaps` (73 checks), `tests/t84_session_deep` (106 checks)
and `tests/t129_session_r11` in the native host corpus (`run_native.sh`). Layer 4, service 25.

## What it does

Sessions for both citizens -- a user at a keyboard and an agent -- owning which console the display service shows. A session starts in LOGIN and claims a console only when it attaches.

## Contract

- **Entry:** none yet. No file here exports `svc_entry`; the units are functions a `service_main` will call once the spawn signature is fixed (Q-B-L1-4, `os-build/layer1/SERVICE_CONTRACT.md` §2). That is a deviation, stated in `Deviations` below.
- **Kernel surface:** none. This unit reaches the kernel only through other services.
- **Needs from Layers 1–3:** see `os-build/layer1/BOUNDARIES.md`; the binding milestone is K6 for anything that calls a syscall, and nothing here needs K2/K3 directly unless the kernel surface line above says so.
- **Offers to Layers 5–6:** the functions listed below in the source. Nothing may rely on them until the layer is COMPILED.

## Dependencies

- **Libraries:** `common.err.err`
- **Services:** none resolved by name from this unit; the caller resolves names through the supervisor's registry (B-L1-22).
- **Data it owns:** The session table (8 slots) and which session is foreground. Volatile.

## Failure behaviour

- `E_INVAL` for a malformed owner, `E_NO_SPACE` when the table is full, `E_STATE` for an illegal move (focusing a locked session, attaching twice), `E_BUSY` when two sessions claim one console, `E_NOTFOUND` for an unknown id.
- Known gaps, recorded rather than fixed: `ses_open` checks `agent == 0` but not `agent > 0`, and does not validate `caps` at all, so a negative agent handle and a negative capability mask are stored as given; `ses_close` has no `SS_CLOSED` guard, so a second close returns `CODE_OK`.
- Missing dependency at start-up: refuses to start (non-zero exit), rather than running with a hole it cannot report.
- Every failure path returns a code from `common/err` or a trailing `false`; none of them is silent.

## Limits

`SES_CAP` (8 sessions), `LG_NAME_MAX` (24), `LG_TOKEN_MAX` (40), `LG_ATTEMPTS` (3). Every row
is exercised: `t84_session_deep` fills the table and crosses both field caps, and
`t129_session_r11` runs 120 open/attach/close/reap cycles through one slot. See
`os-build/layer1/LIMITS.md` and `os-build/layer1/r11/session.md`.

## Verification

Checked against the Goose docs served by the language MCP (goose-mcp@1.1.0 `lookup_symbol` / `overview`):

| Symbol / form | Source |
|---|---|
| struct with typed fields | `tutorial` §3, `samples/01_tour.goose` |
| fixed arrays `T[..N]`, `u8[..N]` | `samples/03_strings.goose` |
| growable builder `u8[>..]`, `.push`, `.len` | `samples/03_strings.goose` |
| `while` / `if` / `return` | `list_keywords` |
| trailing-bool and multi-value returns | `samples/04_errors.goose` |
| reference parameter `T&` | `reference` #46 |
| bitwise `&` `|` `~` `<<` `>>` | `list_keywords` |

## Not verified

- Kernel behaviour. Nothing here has run on the kernel; the drivers run as host processes under `run_native.sh`.
- A real keyboard and a real display. `ses_attach` is driven with invented console indices and `ses_accepts_input` with invented focus; no framebuffer or input device was involved.
- Supervisor-driven restart. The table is volatile and no restart drill has been run, so continuity across a restart is not claimed.

## Deviations

- No `svc_entry`. The spawn signature is not published (Q-B-L1-4), so a `service_main` would be guessing at its own arguments. The functions are the body a `service_main` will wrap.
