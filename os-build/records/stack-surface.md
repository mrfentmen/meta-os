# `crates/stack` — public surface inventory (B202)

One line per exported name (`crates/stack/src/lib.rs`). "Used" means a
caller outside the crate's own tests reaches it. No such caller exists
today (B199), so most of this crate is unused in the repo.

## Constants

| Name | Line | Used? |
|---|---|---|
| `WAIT_HTTP_MAX_ATTEMPTS` | 39 | yes — `http_health` at 163-171 |
| `WAIT_HTTP_INTERVAL_MS` | 41 | yes — `http_health` |
| `WAIT_HTTP_TIMEOUT_SECS` | 43 | yes — `http_health` |
| `AGENT_SETTLE_SECS` | 45 | **no production use** — only the tests read it; `plan` encodes the wait in `Readiness::ProcessAlive` without referencing the constant |

## Types

| Name | Line | Used? |
|---|---|---|
| `Transport` | 52-57 | yes — `StackConfig.transport`, `resolve_transport` |
| `Transport::dev_helper_warning` | 61-63 | **tests only** |
| `Readiness` | 68-79 | yes — constructed by `plan`; no runner reads it |
| `Service` | 84-99 | yes — returned by `plan`; no runner consumes it |
| `StackConfig` | 101-108 | yes — input to `plan`/`summary_lines` |

## `StackConfig` methods

| Name | Line | Used? |
|---|---|---|
| `from_entries` | 127-137 | tests and any pure caller; **no production caller** |
| `from_env` | 139-148 | **no caller in the repo** |
| `relay_base` | 150-152 | yes — `plan`, `summary_lines` |
| `queue_base` | 154-156 | yes — `plan`, `summary_lines` |
| `app_base` | 158-160 | yes — `plan`, `summary_lines` |

## Functions

| Name | Line | Used? |
|---|---|---|
| `plan` | 174-226 | **no caller** — the crate is not wired to `run-stack.sh` or a runner |
| `summary_lines` | 232-247 | **no caller** |

## Private helpers

| Name | Line | Note |
|---|---|---|
| `resolve_port` | 110-115 | used by both constructors |
| `resolve_transport` | 117-121 | used by both constructors; carries the two-state transport finding |
| `http_health` | 163-171 | used by `plan` |

## What is dead today

`plan`, `summary_lines`, `from_env`, `Service`, `Readiness` and all four
constants are reachable but unexercised outside tests, because nothing
executes the plan. The live composition is still `run-stack.sh`. This is
the honest state, not a defect to hide: a runner has to be written
before the crate can replace the script.
