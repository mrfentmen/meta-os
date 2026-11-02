# Python budget governor — behaviour record (B235)

Module: `os/intel/budgets.py`. Read 2026-11-02. Every claim cites the
file and line range it comes from.

## What it does

One definition of "at warning", "at cap", and "may claim" over the
OS-079 budget-entry shape `{"lane", "spent", "cap"}`
(`budgets.py:1-37`). The watchdog, the drill, and the queue gate all
answer from these functions, so there is no second definition of "at
cap" anywhere (`budgets.py:13-20`).

## Inputs

- `spent`, `cap` — integers on a budget entry (`budgets.py:85-131`).
- `warn_percent` — optional override; default
  `BUDGET_WARN_PERCENT` (`budgets.py:100-114`).
- `snapshot` — an object carrying a `"budgets"` list
  (`budgets.py:162-183`).
- Environment: `WATCHDOG_BUDGET_WARN_PERCENT`, read once at import
  through `_env_int(name, default, minimum, maximum)`
  (`budgets.py:51-78`).

## Outputs

- `spend_ratio(spent, cap)` → float, or `None` when unusable
  (`budgets.py:85-97`).
- `at_warning(...)` → bool in the band `[warn_percent, 100%)`
  (`budgets.py:100-114`).
- `at_cap(...)` → bool, true at or above cap (`budgets.py:117-126`).
- `claim_allowed(...)` → `not at_cap(...)` (`budgets.py:129-136`).
- `budget_state(entry)` → `"capped"` | `"warning"` | `"ok"` |
  `"unbudgeted"` (`budgets.py:140-159`).
- `budgets_from_snapshot(snapshot)` → list of usable entry dicts
  (`budgets.py:162-183`).
- `hold_entry(lane, spent, cap)` → an entry with `"held"` set by
  `at_cap` (`budgets.py:186-196`).

## Refusals (these functions never raise)

- Non-integer, boolean, float, missing, zero-cap, or negative-cap
  figures have no ratio and are treated as unbudgeted
  (`budgets.py:81-97`).
- A negative `spent` has no ratio (`budgets.py:94-95`).
- A bad `WATCHDOG_BUDGET_WARN_PERCENT` — blank, unparseable, or outside
  1-100 — silently falls back to 80 (`budgets.py:51-78`).
- `budget_state` on a non-dict, or an entry with no usable cap, returns
  `"unbudgeted"` (`budgets.py:140-159`).
- `budgets_from_snapshot` skips a non-list/tuple `"budgets"`, non-dict
  items, and entries whose `"lane"` is missing, non-string, or empty
  (`budgets.py:173-183`).

## Precedence

`budget_state` checks `at_cap` first, then `at_warning`, then a usable
ratio, then unbudgeted (`budgets.py:149-158`). A lane at cap is
therefore never reported as merely warning.

## Findings

- `at_warning` accepts a caller-supplied `warn_percent` with no range
  validation (`budgets.py:100-114`); `warn_percent=0` warns at zero
  spend. The env path is range-checked, the argument path is not.
- The module is not wired into the live `jobs.py` claim path yet, and
  says so in its own header (`budgets.py:29-36`). The gate is proven
  against the drill's fake queue, not the real one.
