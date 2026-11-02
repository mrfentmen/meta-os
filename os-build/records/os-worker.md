# `crates/os-worker` — behaviour record (B073)

Read from `crates/os-worker/src/lib.rs` at main (2026-11-02), 4,661
lines in one library module. Every claim cites a line range. The crate
is the B22 port of the worker runtime and drivers.

Status words: **LIVE** (the code runs and its result is used),
**SEAM** (a trait/argument the caller must supply; the crate does not
perform the live effect), **NOT PORTED** (see `os-worker-gaps.md`).

## What it is

One library crate, `os-worker`, version `0.1.0`, zero dependencies
(`Cargo.toml:1-5`). It does six jobs:

1. **Supporting crypto and JSON** — std-only SHA-256, HMAC-SHA256,
   timestamp and truncation helpers, and a minimal JSON parser/renderer
   (`lib.rs:62-561`).
2. **Acceptance checks** — parse `file-exists`, `tests-pass`,
   `command-ok`, `contains` lines and verify them against a workdir
   (`lib.rs:563-768`).
3. **Driver contract** — the job spec, its refusals, heartbeat records,
   before/after snapshots, artifacts records, and child-process control
   (`lib.rs:771-1202`).
4. **Two drivers** — `StubDriver` runs a caller-supplied argv; `MuseDriver`
   builds a prompt from the spec and runs `muse exec` (`lib.rs:1205-1803`).
5. **Relay uplink** — validate, sign, queue, drain, deduplicate and
   back off for orders read from the phone (`lib.rs:1910-2184`).
6. **MOS worker loop, stall detectors and drills** — the poll/claim/work
   cycle behind a backend trait, the two stall rules, lease sweep, and
   the kill-worker drill (`lib.rs:2187-3001`).

## Section map

| Lines | Section | Live? |
|---|---|---|
| 62-221 | SHA-256 / HMAC / time / truncation | LIVE |
| 223-561 | minimal JSON (`JsonValue`, `parse_json`, `json_escape`) | LIVE |
| 563-768 | acceptance parse, run, verify | LIVE |
| 771-1202 | driver contract (errors, spec, heartbeat, artifacts, process control) | LIVE |
| 1205-1427 | `StubDriver` | LIVE |
| 1429-1803 | `MuseDriver` | LIVE |
| 1806-1880 | `run_driver`, `spec_from_json` | LIVE |
| 1883-1908 | embedded `CONTRACT.md` / `CONFORMANCE.md` and their hashes | LIVE (text) |
| 1910-2184 | relay uplink | LIVE |
| 2187-2472 | worker loop + `WorkerBackend` trait | LIVE logic, SEAM backend |
| 2474-2735 | stall detectors | LIVE |
| 2737-2823 | drill helpers (`parse_section*`, slice, heartbeat bridge) | LIVE |
| 2825-3001 | lease sweep + kill-worker drill | LIVE |
| 3004-4661 | `#[cfg(test)] mod tests` (96 tests) | test only |

## What it does

- **Spec validation** (`validate_spec`, `lib.rs:880-920`): id, title and
  spec must be non-empty strings; `files` must be a non-empty list of
  non-empty paths; accept lines must parse; the signature must be
  present and non-blank. Returns a copy. `max_attempts` is carried as
  given (default 3 through `JobSpec::new` / `spec_from_json`), not
  range-checked — the Python original does the same (`stub_driver.py:58-89`).
- **Acceptance** (`parse_accept` 599-649, `run_accept_checks` 651-730,
  `verify_accept` 732-768): blank/`#` lines skipped; four kinds only;
  `contains` needs `path :: substring`. Empty accept text verifies true
  with a `(no acceptance criteria)` note; unparseable text returns one
  failed `(parse)` result.
- **Driver contract** (`LOG_NAME` 777, `DriverError` 783-822, `JobSpec`
  831-877): four error cases — generic `Driver`, `Unsigned`, `BadSpec`,
  `NotStarted`.
- **Heartbeats** (`progress_record`, 935-949): one line,
  `PROGRESS:<job_id> <note>`, with a Unix-seconds `ts`. A caller sink
  replaces the internal list; it does not supplement it (`vec_sink`
  951-960; `StubDriver::new` 1264-1290).
- **Artifacts** (`compute_artifacts`, 1061-1110): diff before/after
  snapshots, exclude `driver.log`, sort changed paths, split owned vs
  unowned, run acceptance, status `stopped` (if `stop()` ran) else
  `done` on exit 0 else `failed`.
- **Process control** (`status_code` 1113-1130, `wait_child` 1133-1160,
  `terminate_child` 1163-1198, `poll_child` 1201-1203): Python
  `Popen.returncode` encoding (plain code, negative signal), optional
  wait timeout, SIGTERM then 5-second grace then kill.
- **StubDriver** (1245-1427): runs the caller's argv with cwd=workdir,
  stdout and stderr appended to `driver.log`; refuses a second start
  even after the child exited (Python never clears `_proc`).
- **MuseDriver** (1541-1803): resolves the binary like `shutil.which`
  (1497-1514), writes the prompt outside the workdir (1636-1735),
  launches `muse exec --prompt-file <path>` (1469-1495), streams stdout
  lines into heartbeats and the log (1712-1730), joins the reader on
  wait, removes the temp dir.
- **Uplink** (1910-2184): `backoff_seconds` is 5, 10, 20 … capped at
  300 (1922-1936); invalid orders are rejected with a reason (2005-2017);
  connected ticks drain pending first then new orders (2108-2140);
  disconnected ticks queue and bump the failure count; crew mode without
  a key refuses intake but keeps the order pending (2043-2090).
- **Worker loop** (`Worker::run_once`, 2417-2472): register, heartbeat,
  poll (nothing when `dm_secret` is empty), skip unmet requirements,
  claim, run handler, finish or block. Claim errors keep the last 200
  characters of detail; block reasons are capped at 500; a crash becomes
  `handler crashed: <last 400 chars>`.
- **Stalls** (2474-2735): WDG-002 presence-stall and WDG-003
  progress-stall, one alert per (nick, job), critical severity, age
  strictly greater than the window, activity preference order
  `last_progress`, `progress_at`, `note_ts`,  `last_progress_at`, `claimed_at`.
- **Drill** (2897-3001): four phases — healthy zero alerts, kill yields
  exactly one presence-stall with the right age, unexpired lease stays
  claimed, expiry requeues and the alert stops firing.

## What it refuses

| Refusal | Where | Exact behaviour |
|---|---|---|
| Workdir missing | `StubDriver::new` 1264-1272, `MuseDriver::new` 1564-1572 | `DriverError::Driver("workdir does not exist: …")`, no state built |
| Empty id / title / spec | `validate_spec` 880-903 | `BadSpec`, message names the field |
| Empty files list or blank path | `validate_spec` 904-912 | `BadSpec("job spec field 'files' must be a non empty list of non empty paths")` |
| Bad accept line | `validate_spec` 913-919 | `BadSpec("unparseable accept lines: …")` |
| Missing/blank signature | `validate_spec` 921-928 | `Unsigned("job spec has no signature; refusing to start an unsigned job")` |
| Unknown accept kind | `parse_accept` 616-620 | `Err("line N: unknown check ...")` |
| Accept line without `:` | `parse_accept` 607-610 | `Err("line N: no ':' separator: ...")` |
| Empty accept argument | `parse_accept` 621-624 | `Err("line N: empty argument")` |
| `contains` without `::` | `parse_accept` 625-631 | `Err("line N: contains needs 'path :: substring'")` |
| Second start | `StubDriver::start` 1315-1321, `MuseDriver::start` 1637-1643 | `Driver("driver already started for job <id>")`; no new child |
| Empty stub command | `StubDriver::start` 1325-1329 | `BadSpec("command must be a non empty argv list")`; no child |
| Muse binary absent | `MuseDriver::start` 1648-1656 | `Driver("muse binary not found: ...")`; `self.spec` reset to `None`; no child, no prompt |
| Driver log cannot open | `start` 1330-1338 / 1664-1670 | `Driver("could not open driver log: ...")` |
| Child cannot spawn | `StubDriver::start` 1352-1354, `MuseDriver::start` 1690-1699 | `Driver("could not launch ...")` |
| Operation before start | `heartbeat`/`poll`/`stop`/`wait`/`artifacts` | `NotStarted("... before start")` |
| Wait timeout | `wait_child` 1152-1156 | `Driver("driver wait timed out")`, reworded to `driver wait timed out for job <id>` in the driver |
| Uplink order with no id | `validate_order` 2006-2008 | `(false, "order id missing")`, event `rejected` |
| Uplink empty text / no origin | `validate_order` 2009-2016 | `(false, "order text empty" / "order origin missing")` |
| Crew mode, no key | `take_in` 2053-2090 | event `unsigned-refused`, order stays pending, never dropped |
| Bad spec JSON | `parse_json` 550-561 / `spec_from_json` 1842-1880 | `Err` with `run_driver:` prefix |
| Bad `run_driver` input | `run_driver` 1821-1840 | `Err("run_driver: cannot read spec file: ...")` or the driver message |

## What it writes down

- `driver.log` in the workdir, append-only: child stdout/stderr and, for
  Muse, stdout lines mirrored by the reader thread (`LOG_NAME` 777;
  Stub start 1330-1351; Muse reader 1712-1730).
- Heartbeat records in memory (`HeartbeatRecord` 923-933): line, job id,
  note, ts. No bus post exists in the crate.
- `ArtifactsRecord` (962-1021) and its JSON (`to_json` 986-1021).
- `StartRecord` / `StopRecord` (1211-1231).
- `IntakeRecord` / `UplinkEvent` (1970-2003); `RunReport` (2298-2311);
  `StallAlert` (2597-2642); `BridgeJob` (2800-2816); `SweepJob` 2836-2855;
  `KillDrillReport` 2882-2895.
- A prompt file under the system temp dir while a Muse run is active
  (1636-1735), removed on `wait` (1789-1792).

Worked, field-by-field examples: `os-worker-records.md`.

## Live-behaviour boundary (never faked here)

- Redis, the bus, job claims, capability registration and lease renewal
  are the `WorkerBackend` trait (`lib.rs:2328-2355`). The crate performs
  no network call; the loop's decisions are real, the transport is the
  caller's.
- The canonical acceptance port is B31; this section covers only what
  the drivers need (`lib.rs:563-571`).
- The canonical watchdog is B21; the stall detectors here are the
  drill-facing subset (`lib.rs:2474-2489`).
- `MuseDriver` never posts a heartbeat to the bus; the sink is local
  (`lib.rs:1507-1539`).

## Findings

1. **Header stale.** `lib.rs:1` says "skeleton (B00)" and `lib.rs:25`
   says "Skeleton only: no logic yet", but the file is the B22 port with
   4,661 lines and 96 tests. Fixed in this pass (B076); the port notes
   below that line were already accurate.
2. **Acceptance has no command timeout.** Python `mos/acceptance.py:54-61`
   runs each check with `timeout=300` and reports `124, "timed out after
   300s"`; the Rust `run_accept_checks` (651-730) uses
   `Command::output()` with no timeout, so a hung `command-ok` or
   `tests-pass` blocks the caller forever. Recorded as gap G1, not fixed
   here (behaviour change).
3. **Stream separation.** Python merges stderr into stdout for both
   drivers (`stub_driver.py:139-141`, `muse_driver.py:172-174`). Stub
   here appends both to the same file (equivalent). Muse sends stderr
   straight to the log and streams only stdout as heartbeats
   (`lib.rs:1668-1716`), so stderr lines are in the log but never become
   PROGRESS notes. The header states this deviation; it is real.
4. **`MuseDriver::wait` joins the reader without the Python 5-second
   timeout** (`muse_driver.py:224`; `lib.rs:1780-1782`). The header
   already names this; a child that holds stdout open without exiting
   would block `wait` past the child's exit.
5. **No in-repo caller imports the crate.** It is a workspace member and
   other files only mention it in comments (see `os-worker-callers.md`).
   `crates/parity-tests/src/tests/test_os_uplink.rs:5` still calls it
   "the B00 skeleton", which is now false.
