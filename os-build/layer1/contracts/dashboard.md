# Contract — `dashboard`

Status: **RUNS** — `services/tests/t89_dashboard.goose`, on the host shim. Not started by a
supervisor; nothing starts a service yet.

## What it is

The sample table behind the four dashboard numbers: `cpu`, `mem`, `disk`, `net`. One rule
makes it honest and everything else follows from it: **a value is never invented.**

| verdict | meaning | value returned |
|---|---|---|
| `DF_FRESH` (0) | sampled, inside its window | the sample |
| `DF_STALE` (1) | sampled, older than its window | the sample, plus its age |
| `DF_NEVER` (2) | never sampled | 0, and the caller must not draw it |

A metric nobody has measured reports `DF_NEVER`, not 0. 0% CPU is a fact; "nobody looked"
is not, and a dashboard that draws the two identically is a dashboard that lies slowly.

## Freshness is per metric

Each kind carries its own window, set at init and adjustable with `df_set_window`. A disk
figure ten seconds old is fine; a CPU figure ten seconds old is a claim about *now* that
nothing supports. The window belongs to the metric, not to the caller — a caller that
passed its own would have to remember four different numbers at every call site.

## API

| function | returns | notes |
|---|---|---|
| `df_init()` | — | all four kinds `DF_NEVER`, default windows |
| `df_put(kind, value, now_ms)` | code | rejects an unknown kind, and a value < -1 |
| `df_get(kind, now_ms)` | `(value, verdict)` | the only read that matters |
| `df_age_ms(kind, now_ms)` | ms, or -1 | -1 when never sampled |
| `df_verdict(kind, now_ms)` | verdict | for a caller that only needs the label |
| `df_label(kind, now_ms, out)` | — | `"cpu 42% fresh"` / `"mem -- never"` — the string the tile draws |
| `df_set_window(kind, ms)` | code | 0..`DF_MAX_AGE_MS` |
| `df_fresh_count(now_ms)` / `df_missing_count()` | counts | the fleet-level line |

## Clock

Every call that needs a time is given one. There is no ambient `now` in this layer, which
means a stale-label sequence can be replayed from a log — and the stale labels are exactly
the part worth replaying.

## Failure modes, all driven by the test

- **Never sampled** — `df_get` is `(0, DF_NEVER)`; `df_label` draws `--`.
- **Just inside the window** — `DF_FRESH` at `window - 1` ms.
- **Exactly the window** — `DF_STALE` at `window` ms: the boundary belongs to stale, so a
  window is "valid for less than N ms", which is the only reading that cannot round up.
- **Unknown kind** — `df_put` and `df_get` are `E_NOTFOUND`; kind 5 does not fit in the
  table and is refused rather than clamped onto `net`.
- **Clock going backwards** — a `now_ms` below `taken_ms` reports the sample as stale rather
  than as a negative age, because the alternative invites an age that reads as fresh.

## Restart semantics

All memory. After `df_init` every metric is `DF_NEVER` again, which is the honest state: the
new process has not measured anything. The intended recovery is that each producer pushes a
sample on start-up, and until it does the tile says so.

## Limits

Kinds 1..`DF_MAX_KIND` (4), `DF_MAX_AGE_MS` 60000 default per kind, value ≥ -1. Resident
storage is 5 × 32 bytes, measured by `size_audit.py`.
