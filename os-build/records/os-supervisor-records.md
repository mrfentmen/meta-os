# `crates/os-supervisor` — worked records (B018)

One worked example per record kind the crate produces, annotated field
by field. Values come from the crate's own fixtures and drills, not
from a live system; every field named exists in the cited struct, and
the producer named is the code path that sets it.

## 1. `Alert` — presence-stall

Producer: `detect_presence_stall` (`watchdog.rs:840-892`), shape
`watchdog.rs:610-720`. Fixture: `e2e_watchdog_surfaces::stall_snapshot`
(`e2e_watchdog_surfaces.rs:189-202`) — job 7, claimed by `pax`, absent
from presence, last activity 9340, seen at 10000.

| Field | Value | Meaning / why set |
|---|---|---|
| `kind` | `"presence-stall"` | detector identity; also the severity-table key (`watchdog.rs:1588`) |
| `severity` | `"critical"` | canonical table, not per-call |
| `nick` | `Some("pax")` | the claimer |
| `job` | `Some("7")` | the claimed job |
| `job_title` | `"demo job"` | `""` when the job has no title |
| `last_progress_age_seconds` | `Some(660)` | 10000 − 9340 |
| `last_progress_age_minutes` | `Some(11)` | integer minutes, floored |
| `explanation` | `"pax holds claimed job 7 but has been absent from presence for over 10 minutes with no progress on it for 11 minutes."` | WDG-011 template, filled (`watchdog.rs:722-…`) |
| `suggested_fix` | `"Check on pax; if the worker is gone, the lease sweep will requeue job 7 for another worker."` | same template, never polished |
| `dedupe_key` | `"presence-stall:pax:7"` | store id and episode identity (`e2e_watchdog_surfaces.rs:50`) |
| `created_at` | `10000` | tick time |
| all other fields | `None` / empty | this kind does not carry them; never filled with guesses |

Announcement: `ALERT:presence-stall:pax:7 presence-stall: <explanation>`
(`format_announcement`, `watchdog.rs:1621-1655`) — only because severity
is `critical`.

## 2. `JournalEntry` — escalation for a dead watchman

Producer: `escalation_for` (`watchman_watch.rs:379-418`), shape
`watchman_watch.rs:206-234`.

| Field | Value | Meaning |
|---|---|---|
| `kind` | `"escalation"` | one of the four journal kinds |
| `machine` | `"box-a"` | the dead machine |
| `state` | `None` | escalations do not carry a state |
| `reason` | `Some("watchman dead, restart failed")` | why a human is needed |
| `question` | `Some("The watchman on machine box-a is dead … Dale's call is needed.")` | the parked question, verbatim |
| `push` | `Some(BlockedPush { push_type: "blocked", job_id: "watchman:box-a", title: "Watchman on machine box-a", body: "…", question: "…" })` | built by the push seam; **never sent** |
| `restart_ok` | `None` | an escalation is not a restart attempt |
| `created_at` / `recovered_at` / `attempted_at` | `None` | other kinds' fields |
| `escalated_at` | `Some(now)` | tick time of the escalation |
| `dedupe_key` | `"watchdark-escalate:box-a"` | one escalation per episode |

## 3. `ReconcileReport` — a startup recovery run

Producer: `reconcile` (`reconcile.rs:109-132`), shape
`reconcile.rs:77-95`.

```json
{
  "redis": true,
  "requeued": ["7"],
  "pruned": ["stale-nick"],
  "unverified": ["8"],
  "blocked": [["9", "waiting on acceptance"]]
}
```

| Field | Meaning |
|---|---|
| `redis` | the backend answered; when false every list is empty and the run stops |
| `requeued` | jobs whose expired claim the sweep requeued |
| `pruned` | capability nicks dropped as stale |
| `unverified` | `status == "done"` and `verified != "1"` (`reconcile.rs:50-62`) |
| `blocked` | `status == "blocked"`, reason is `note` truncated to 200 **chars** (`reconcile.rs:64-75`) |

Rendered: `redis: OK`, `REQUEUED 7`, `PRUNED stale-nick`,
`UNVERIFIED 8`, `BLOCKED 9: waiting on acceptance`
(`render_summary`, `reconcile.rs:133-156`). A clean run adds
`RECONCILE_CLEAN`. Exit 0 if redis, else 2 (`reconcile.rs:158-166`).

## 4. `BootNote` — first cycle after downtime

Producer: `verify_boot_cycle` (`watchman_boot.rs:254-310`), shape
`watchman_boot.rs:120-140`.

| Field | Meaning |
|---|---|
| `rings` | the ring set in input order; each has `job_id`, `reason`, `posted_at`, `lease_expires_at` |
| `arrived_count` | jobs posted while the machine was down |
| `lease_expired_count` | claims whose lease died while it was down |
| `total_rings` | `rings.len()` |
| `sweep_requeued` | the sweep's ids, sorted and deduplicated |
| `reconciled` | true only when lease-expired rings exactly equal the sweep record |
| `mismatch` | `SweepMismatch { missing, extra }`, both sorted |
| `counter_ignored` | recompute with copies yields the identical ring set (always true: no counter field exists) |

Brief: `watchman boot: 2 ring(s) (1 arrived during downtime, 1
lease-expired)` then one `ring <id>: <reason>` line
(`boot_brief_lines`, `watchman_boot.rs:312-…`).

## 5. `StateRecord` — the board row

Producer: `current_states` (`watchman_watch.rs:293-322`), shape
`watchman_watch.rs:99-112`.

| Field | Value | Meaning |
|---|---|---|
| `machine` | `"box-a"` | machine name, output in name order |
| `state` | `"alive"` | one of `alive` / `dead` / `unknown` |
| `last_bell` | `Some(1000.0)` | carried from the record |
| `last_wake` | `Some(1000.0)` | carried from the record |
| `as_of` | `1000600.0` | the tick time the state is judged at |

## 6. `AlertRecord` — the surfaces record

Producer: `build_alert_record` (`e2e_watchdog_surfaces.rs:286-326`),
shape `e2e_watchdog_surfaces.rs:113-145`.

| Field | Value | Rule |
|---|---|---|
| `id` | dedupe key | this builder uses the dedupe key; the store's id-preference rule is a seam |
| `kind` / `severity` | from the alert | missing either is an error, never a default |
| `room` | cleaned, default `"main"` | `clean_room` |
| `subjects` | `["pax", "7"]` | nick then job, deduplicated |
| `created_at` / `last_seen` | same tick value | fresh record |
| `status` | `"open"` | every fresh occurrence |
| `acknowledged_at` / `resolved_at` | `None` | nothing acknowledged yet |
| `explanation` / `suggested_fix` / `dedupe_key` | carried verbatim | no rewriting |

## 7. `RunResult` — the load check

Producer: `evaluate` (`watchdog_load_check.rs:429-506`), shape
`watchdog_load_check.rs:149-181`; stage rows 149-158.

| Field | Meaning |
|---|---|
| `ok` | true only when all six stages pass |
| `stages` | `[StageResult { name, ok, detail }]` in the fixed order `STAGE_NAMES` (`:63-70`) |
| `transcript` | the rendered run text |
| `message_count` / `job_count` / `claimed_count` | 2000 / 200 / 50 on a passing run |
| `ticks` | per-tick count records |
| `total_seconds` | three-tick wall time; the budget is 15 s (`:58-60`) |
