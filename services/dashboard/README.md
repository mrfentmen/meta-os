# dashboard — four numbers, and the refusal to invent a fifth

Status: **RUNS** — `tests/t89_dashboard` passes in the native host corpus
(`run_native.sh t89_dashboard`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 4.

## What it is

A sample table for the four numbers the dashboard shows: CPU, memory, storage and
network. The one rule that makes a dashboard honest is that **a value is never
invented**. `df_get` returns a verdict alongside the number:

| Verdict | Meaning |
|---|---|
| fresh | sampled within this metric's window |
| `DF_STALE` | sampled, but older than the window; the age is reported |
| `DF_NEVER` | nobody has ever sampled this metric |

`DF_NEVER` is not reported as `0`, because 0% CPU is a fact and "nobody measured"
is not. A dashboard that shows zero for an absent sample is a dashboard that
lies politely.

## Why staleness is per metric

A disk figure that is ten seconds old is fine. A CPU figure that is ten seconds
old is a lie about right now. `df_default_window(kind)` puts the window on the
*kind*, not on the caller, so every consumer of the CPU number agrees about when
it went stale. `df_set_window` can tighten it for a specific deployment, and
`df_window` reads it back.

## Why the caller passes the clock

There is no ambient `now` in this layer: every call that needs a time is given
one. A feed that read a clock itself could not be replayed, and the stale labels
are exactly the part worth replaying.

## Surface

| Function | Answers |
|---|---|
| `df_put` | record a sample for a kind at a `now_ms` |
| `df_get` / `df_verdict` | the value and whether it is fresh, stale or never |
| `df_age_ms` | how old the sample is |
| `df_label` | the dashboard's one-line form, verdict included |
| `df_default_window`, `df_set_window`, `df_window` | the staleness policy |
| `df_fresh_count`, `df_missing_count` | how much of the page is real right now |

## Where the proof is

`services/tests/t89_dashboard.goose` — the never-sampled and stale paths, which
are the two that a naive feed gets wrong.
