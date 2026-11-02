# wallpaper — the registry, and the frame budget that keeps a live one honest

Status: **RUNS** — `tests/t87_wallpaper` passes in the native host corpus
(`run_native.sh t87_wallpaper`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 2.

## What it is

A fixed registry of wallpapers — static or live — plus the one rule that keeps a
live wallpaper from eating the machine: `wl_tick` grants a frame only when that
wallpaper's own interval has elapsed. `wl_interval_ms(fps)` derives the interval
from the registered rate, so the budget lives in the service and not in a
renderer.

## Why the budget is enforced on the tick

A renderer asked to throttle itself is a renderer that can decide not to. The
tick is the only place that hands out permission to draw, so a wallpaper that
ignores its own fps still cannot draw faster than the registry allows.
`wl_frames_drawn` and `wl_budget_refusals` are the two counters that make the
budget visible.

## Fullscreen pause

A fullscreen window is someone working. `wl_set_fullscreen(true, now_ms)` pauses
the tick, and `wl_pause_count` increments **once on entry**, not once per tick.
A counter that incremented every tick would read as "the wallpaper failed 600
times" after ten seconds of fullscreen, which is a true number about nothing.

## What it does not do

It does not decode an image, allocate a framebuffer, or talk to the display
service. It answers two questions — may this wallpaper draw now, and which one is
selected — which is exactly what the compositor needs before it does any of that.
Keeping image work out of here is why the registry can be a static table.

## Surface

| Function | Answers |
|---|---|
| `wl_register`, `wl_find`, `wl_find_name` | the registry: add, look up by id, look up by name |
| `wl_select`, `wl_current_id`, `wl_current_name` | which wallpaper is selected |
| `wl_tick` | may the current wallpaper draw at this `now_ms`? |
| `wl_set_fullscreen`, `wl_is_paused` | fullscreen pause state |
| `wl_frames_drawn`, `wl_budget_refusals`, `wl_pause_count` | the three counters |
| `wl_summary` | one line of the above, for a status readout |

## Where the proof is

`services/tests/t87_wallpaper.goose`.
