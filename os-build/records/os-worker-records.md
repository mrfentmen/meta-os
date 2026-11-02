# `crates/os-worker` — worked records (B078)

One worked example per record kind the crate produces, annotated field
by field. Values come from the crate's own fixtures, tests and drills,
not from a live bus; every field named exists in the cited struct, and
the producer named is the code path that sets it.

## 1. `HeartbeatRecord` — one progress line

Producer: `progress_record` (`lib.rs:935-949`); shape `lib.rs:923-933`.
Example for job `7`, note `compiling`.

| Field | Value | Meaning / why set |
|---|---|---|
| `line` | `"PROGRESS:7 compiling"` | the exact bus progress format; no bus post is made here |
| `job_id` | `"7"` | the claimed job |
| `note` | `"compiling"` | caller note, or a child stdout line cut to 200 chars (`NOTE_LIMIT`, `lib.rs:1437`) |
| `ts` | `1762100000.25` | `now_secs_f64()`, Unix seconds (`lib.rs:201-207`) |

## 2. `ArtifactsRecord` — a finished StubDriver run

Producer: `compute_artifacts` (`lib.rs:1061-1110`); shape
`lib.rs:962-1021`. Example: job `7` owns `out.txt`, the child wrote it
and exited 0, acceptance `file-exists: out.txt`.

```json
{"acceptance":{"ok":true,"results":[{"check":"file-exists: out.txt","detail":"found","ok":true}]},"changed_files":["out.txt"],"exit_code":0,"job_id":"7","log":"/tmp/work/driver.log","status":"done","unowned_files":[]}
```

| Field | Value | Meaning |
|---|---|---|
| `job_id` | `"7"` | from the validated spec |
| `status` | `"done"` | `stopped` if `stop()` ran; else `done` on 0; else `failed` (`lib.rs:1091-1099`) |
| `exit_code` | `0` | `status_code` encoding: plain code, negative signal (`lib.rs:1113-1130`) |
| `changed_files` | `["out.txt"]` | before/after SHA-256 diff, `driver.log` excluded, sorted (`lib.rs:1074-1089`) |
| `unowned_files` | `[]` | changed paths not in `spec.files` |
| `log` | workdir + `driver.log` | `LOG_NAME` (`lib.rs:777`) |
| `acceptance_ok` | `true` | every check held |
| `acceptance_results` | one row | check text, ok, detail |

## 3. `StartRecord` / `StopRecord`

Producers: `StubDriver::start` (`lib.rs:1355-1363`), `stop`
(`lib.rs:1381-1393`); shapes `lib.rs:1211-1231`.

| Record | Field | Value | Meaning |
|---|---|---|---|
| Start | `job_id` | `"7"` | validated spec id |
| Start | `pid` | `48213` | real child pid |
| Start | `status` | `"running"` | constant |
| Stop | `job_id` | `"7"` | same job |
| Stop | `status` | `"stopped"` | constant |
| Stop | `exit_code` | `-15` | SIGTERM before the child reported a code |

## 4. `IntakeRecord` — an order taken in by the uplink

Producer: `intake_record` (`lib.rs:2041-2052`); shape `lib.rs:1970-1987`.
Example: order `o-1`, text `"ship the fix"`, origin `"phone"`, received
at `1762100000`, signing key present.

| Field | Value | Meaning |
|---|---|---|
| `order_id` | `"o-1"` | the order id, never invented |
| `text` | `"ship the fix"` | carried verbatim as the spec |
| `origin` | `"phone"` | the source the order came from |
| `received_at` | `Some(1762100000)` | only when the order carried one |
| `kind` | `"ORDER"` | constant |
| `signed` | `true` | a key was supplied |
| `signature` | `"9f2c…"` | HMAC-SHA256 over `"o-1\nship the fix"` (`lib.rs:2019-2024`) |

## 5. `UplinkEvent` — duplicate, queued, refused

Shape `lib.rs:1989-2003`. Producer: `take_in` / `uplink_tick`
(`lib.rs:2043-2184`).

| Case | `event_type` | `order_id` | `reason` | `record` |
|---|---|---|---|---|
| Already seen | `"duplicate"` | `Some("o-1")` | `None` | `None` |
| Disconnected | `"queued"` | `Some("o-2")` | `None` | `None` |
| Bad order | `"rejected"` | the id it has | `Some("order text empty")` | `None` |
| Crew mode, no key | `"unsigned-refused"` | `Some("o-3")` | `Some("crew mode requires a signing key")` | `None`; order stays pending |
| Connected, good | `"intake"` | `Some("o-1")` | `None` | `Some(IntakeRecord)` |

## 6. `RunReport` — one worker cycle

Producer: `Worker::run_once` (`lib.rs:2417-2472`); shape
`lib.rs:2298-2311`.

| Field | Example | Meaning |
|---|---|---|
| `claimed` | `["7"]` | claims that returned ok |
| `done` | `["7"]` | finishes that returned true |
| `blocked` | `["8"]` | handler `Blocked` or `Crashed` |
| `skipped` | `["9"]` | requirements not covered by caps |
| `errors` | `["claim 10: no such job"]` | claim/finish error lines, detail tail 200 |

## 7. `StallAlert` — a kill-worker drill alert

Producer: `stall_alert` (`lib.rs:2624-2642`), from
`detect_presence_stall`; shape `lib.rs:2597-2622`. Fixture: the drill's
phase 2 (`lib.rs:2926-2960`).

| Field | Value | Meaning |
|---|---|---|
| `kind` | `"presence-stall"` | WDG-002 |
| `severity` | `"critical"` | only critical alerts announce |
| `nick` | `"pax"` | the absent claimer |
| `job` | `"7"` | the claimed job |
| `job_title` | `"demo job"` | from the snapshot |
| `last_progress_age_seconds` | `961` | `stall_at - last_activity` |
| `last_progress_age_minutes` | `16` | integer division |
| `dedupe_key` | `"presence-stall:pax:7"` | one alert per (nick, job) |
| `created_at` | `100661` | tick time |
| `explanation` | `"pax stalled on job 7 (age 16m)"` | plain rendering |

Announcement: `ALERT:presence-stall:pax:7 presence-stall: pax stalled on
job 7 (age 16m)` (`announcements_for`, `lib.rs:2726-2735`); newlines are
flattened to spaces and the line is never posted.

## 8. `driver.log` — the file the drivers append

Producer: `StubDriver::start` opens append (`lib.rs:1330-1345`); both
child streams write to it. Muse mirrors stdout lines from the reader
thread (`lib.rs:1712-1730`). Example:

```
hello from the agent
warning on stderr
{
```

It is excluded from `changed_files` by name (`lib.rs:1078-1082`), so its
own growth never looks like agent work. The log is the only file the
crate writes inside the workdir; the Muse prompt file lives underthe system temp dir and is removed after wait (`lib.rs:1789-1792`).
