# settings — Round 11 record

Source: `services/settings/settings.goose` · Test: `services/tests/t130_settings_r11.goose` · Status: RUNS (`tests/t86_settings` 67 checks)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SK_MAX_ID` | 6 | `settings.goose` | already driven by `tests/t86_settings`; this test drives the import side | t86 writes/reads id 7 and gets `E_INVAL`; `t130` imports `7=1` and gets `E_CORRUPT` |
| `SET_TEXT_MAX` | 32 | `settings.goose` | already driven by `tests/t86_settings` | t86 accepts 31 bytes and refuses 32 with `E_NOROOM`; `t130` refuses an over-long imported value |
| `SET_COLOR_MAX` | 0xffffff | `settings.goose` | already driven by `tests/t86_settings` | t86 accepts `0xffffff` and refuses `0x1000000`; `t130` exercises `st_in_range` directly |
| `SET_WALLPAPER_MAX` | 7 | `settings.goose` | already driven by `tests/t86_settings` | t86 accepts 7 and refuses 8; `t130` checks both sides in `st_in_range` |
| `SET_MAX` | 24 | `settings.goose` | **unreachable on the host** (recorded in `LIMITS.md`) | the key set is closed at six ids and `st_import` refuses any id past `SK_MAX_ID`, so `entry_count` can never exceed 6; `t130` imports all six and the count is still 6 |

No limit row for this service is missing from `LIMITS.md`.

## 2. Refusals — PROVEN

| refusal | code | the test assertion that expects it |
|---|---|---|
| wrong kind (int vs text) | `E_INVAL` | `t86`: `st_put_int(SK_HOSTNAME, 1)`, `st_get_text(SK_BG)` |
| unknown key | `E_INVAL` | `t86`: id 9 on put and get; `t130`: `st_in_range(99, 1)` false |
| out-of-range int | `E_INVAL` | `t86`: wallpaper 8/-1, colour past max, mode 0/3, animation 2 |
| empty text | `E_INVAL` | `t86`: zero-length hostname |
| control or non-printable text | `E_INVAL` | `t86`: byte 7 in a hostname |
| space in a hostname | `E_INVAL` | `t86`: `a b` refused at `st_put_text` |
| text at `SET_TEXT_MAX` | `E_NOROOM` | `t86`: 32 bytes refused |
| corrupt import | `E_CORRUPT` | `t86`: out-of-range, unknown key, non-numeric, no `=`, blank line, empty file; `t130`: key 0, key 7, negative key, empty value, control byte in text |
| over-long imported text | `E_NOROOM` | `t86`: 35-byte hostname value |
| table full (`E_NO_SPACE`) | `E_NO_SPACE` | **unreachable**: six ids, 24 slots |
| missing key (`E_NOTFOUND`) | `E_NOTFOUND` | **unreachable after `st_init`**: all six defaults are written, and there is no remove path |
| **import accepts a hostname with a space** | — | **FINDING:** `st_import` validates printable bytes and the text length but not the hostname's no-space rule, so `6=a b` imports successfully while `st_put_text(SK_HOSTNAME, "a b")` refuses (`t130`). The file path is a weaker validator than the write path |

Rows naming `t130` are pending its first run; the `t86` rows are backed by the existing run in
`os-build/layer1/SERVICE_RUNS.md`.

## 3. Restart — NAMED GAP

The table is in memory. Persistence is `st_export`/`st_import`, and the caller owns the file:
this service never writes one itself. A restart starts from `st_defaults()` and whatever the
caller imports; dirty flags, and therefore unsaved changes, are lost. No service-level restart
has been run, so continuity is not claimed.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | storage | would persist the exported blob | yes — `SVC_SETTINGS` (id 25) allows `SVC_STORAGE` |
| out | log | logs refused writes | yes — allows `SVC_LOG` |
| out | time | stamps a save | yes — allows `SVC_TIME` |
| in | face services | read/write a setting | **no importer**: no service imports `settings.*`; only tests (`t86`, `t93`, `t94`, `t130`) do |

All three outbound edges are **dormant**: `settings.goose` imports only `common.err.err`.
**FINDING:** `SVC_WALLPAPER`'s matrix row grants `SVC_SETTINGS`, but `wallpaper.goose` does not
import settings — the declared edge has no caller. The store exists and is tested, and nothing
in the running system reads it yet.

## 5. Load — NAMED GAP

The load loop performs 120 `st_put_int` writes to the wallpaper key, cycling values 0-8 so
that every ninth write is out of range and refused at the write; the counters are the test's
own, not a prediction. The marker below is replaced from the run transcript; until then this
is a named gap.

RUNS pass=33 fail=0 · `LOAD settings ops=120 ok=107 refused=13`

## 6. README truth pass — PROVEN

The README was already true about status and behaviour (RUNS, t86, validation at the write,
atomic import). Three changes:

- **"Where the proof is"** named only `t86_settings`; now names `t130_settings_r11` and what it
  adds (the pure range gate, the import key bounds, the space-in-hostname finding).
- **Capacity paragraph** said "Capacity is `SET_MAX` (24) entries" without saying it cannot be
  reached. Now states that the closed key set caps the table at six and points at `LIMITS.md`.
- Added the **known import gap** (space in an imported hostname) to "What it is not", because a
  reader who trusts "validation at the write" would otherwise assume the file path validates
  the same rules.
