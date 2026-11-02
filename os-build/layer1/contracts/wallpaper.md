# Contract — `wallpaper`

Status: **RUNS** — `services/tests/t87_wallpaper.goose`, on the host shim. Not started by a
supervisor; nothing starts a service yet.

## What it is

The wallpaper registry and the frame budget. It answers two questions for the compositor —
*what is selected* and *may it draw now* — and refuses to do anything else. No decode, no
framebuffer, no display call: those are the compositor's, and a wallpaper that allocated
would be a wallpaper that can starve the machine it is decorating.

## Registry

Eight slots (`WL_MAX`). A wallpaper is `{id, name ≤ 19 bytes, kind, fps}`:

- `WL_KIND_STATIC` (1) — no frame budget; `wl_tick` returns 0 for it by design.
- `WL_KIND_LIVE` (2) — draws at its own rate; `fps` is 1..`WL_FPS_MAX` (60).
- Names are unique. A duplicate is `E_EXISTS`, not a silent second entry.

## API

| function | returns | notes |
|---|---|---|
| `wl_init()` | — | registry empty, nothing selected, counters zero |
| `wl_register(name, kind, fps)` | `(id, code)` | validates name, kind and fps |
| `wl_select(id, now_ms)` | code | resets the frame clock; unknown id → `E_NOTFOUND` |
| `wl_tick(now_ms)` | `1` draw / `0` not yet | due = `now - last_frame >= 1000/fps` |
| `wl_set_fullscreen(on, now_ms)` | — | pause on entry, unpause resets the frame clock |
| `wl_interval_ms(fps)` | ms | `1000/fps`, floored at 1 |
| `wl_current_id()` / `wl_current_name()` | selection | `WL_NEVER` (-1) before any select |
| `wl_summary(out)` | — | one status line, for the boot log |

## The budget rule

`wl_tick` grants a frame only when the wallpaper's own interval has elapsed, and counts a
refusal when it has not. Two consequences worth stating: a caller that ticks every frame
gets one draw per interval, not one per tick; and `fps` 60 on a machine that ticks at 60 Hz
gets one frame per tick, which is the ceiling by construction.

## Failure modes, all driven by the test

- **Unknown id** — `wl_select` is `E_NOTFOUND` and the current selection is unchanged.
- **Bad fps** — 0, negative or above 60 is `E_RANGE` at registration.
- **Duplicate name** — `E_EXISTS`.
- **Ninth wallpaper** — `E_NO_SPACE`; the registry is fixed and the test proves the eighth
  one still registers.
- **Pause counted once.** Ten fullscreen ticks after one `wl_set_fullscreen(true)` is one
  pause, not ten. A per-tick increment would read as 600 failures a minute.

## Restart semantics

Everything is memory. After `wl_init` the registry is empty and the selected id is
`WL_NEVER`. The *selection* is meant to come from `settings` key 1, which is why the two
services exist separately: the registry is runtime, the choice is config.

## Limits

`WL_MAX` 8, `WL_NAME_MAX` 20 (19 usable), `WL_FPS_MAX` 60, `WL_NEVER` -1. Resident storage is
8 × (8 + 20 + 8 + 8 + 8) ≈ 416 bytes, measured by `size_audit.py`.
