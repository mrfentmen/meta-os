# `crates/os-worker` — Python behaviours not carried yet (B077)

The deliverable is the list, not the port. Each row: what the Python
original does, where it lives, and what the Rust crate does instead.
Line numbers are in the Python source; the Rust seam is named beside it.
Do not port these here — they belong to the owning batch.

| # | Python behaviour | Source | Rust today | Task for the owner |
|---|---|---|---|---|
| G1 | Acceptance checks run with a 300 s timeout and report `124, "timed out after 300s"` | `os/mos/acceptance.py:54-61`, `run_checks(..., timeout=300)` 68-88 | `run_accept_checks` (`lib.rs:651-730`) calls `Command::output()` with no timeout; a hung check blocks forever | Add a timeout parameter with the same 124 convention; keep the default 300 s |
| G2 | Live Redis/bus/jobs/capabilities: register, touch, heartbeat, claim, done, blocked, DM reads | `os/mos/worker.py:31` (`relay_common`), `75` (`capabilities.register`), `87` (`jobs heartbeat`), `131` (`bus_get`), `152-167` (`jobs.main` claim/done/blocked) | `WorkerBackend` trait (`lib.rs:2328-2355`); the loop calls the trait, no transport exists in the crate | Provide the backend in the jobs/capabilities batch; the loop is already real |
| G3 | `run_driver.py` reads the spec file, parses argv, prints artifacts JSON, exits 2 on driver error | `os/os/drivers/run_driver.py:36-60` | `run_driver(spec_json, workdir, binary, extra_args)` takes text and returns the record (`lib.rs:1821-1840`) | CLI shell in the assembly layer |
| G4 | Muse `wait()` joins the stdout reader with a 5 s timeout and proceeds regardless | `os/os/drivers/muse_driver.py:214-226` | Joins unconditionally after the child exits (`lib.rs:1780-1782`); a child holding stdout open can block | Add the bounded join; keep the current comment accurate until then |
| G5 | Python traceback text is caught and reduced to its last 400 characters | `os/mos/worker.py` run-once error path (the crate header describes the rule, `lib.rs:52-61`) | A crashing handler supplies its own message; the loop takes the last 400 characters (`lib.rs:2458-2467`) — no traceback is synthesized | Nothing to port in Rust; the caller's message is the traceback stand-in. Named so the difference is explicit |
| G6 | Full watchdog tick: every detector, severity table, explanation rendering, alert store | `os/intel/watchdog.py` (canonical B21 port) | Only the two stall detectors plus a plain explanation (`lib.rs:2474-2735`); canonical port is `crates/os-supervisor` | Use the B21 crate for every other detector; this section stays drill-facing |
| G7 | Muse merges stderr into stdout, so stderr lines also become progress notes | `os/os/drivers/muse_driver.py:172-174` | stderr goes straight to `driver.log`; only stdout lines produce heartbeats (`lib.rs:1668-1716`) | Merge the streams in the driver layer if note parity is required; the log already carries both |
| G8 | SIGTERM is delivered directly with `Popen.send_signal(signal.SIGTERM)` | `os/os/drivers/stub_driver.py:171-174`, `muse_driver.py:204-207` | Spawns the `kill -TERM <pid>` utility, falling back to `Child::kill` (`lib.rs:1163-1198`) | Accept as the std-only equivalent; a signal crate would restore direct delivery |

## Not a gap (checked)

- Spec validation field-for-field, including the `max_attempts` default
  and the absence of a range check: `stub_driver.py:58-89` vs
  `lib.rs:880-920`.
- Acceptance line kinds and parse errors: `acceptance.py:23-43` vs
  `lib.rs:599-649`.
- Backoff sequence and cap: Python `relay_uplink.py` vs
  `lib.rs:1922-1936` (5, 10, 20 … 300).
- Before/after snapshot and owned/unowned split: `stub_driver.py:91-105`
  and `wait()` vs `lib.rs:1024-1110`.
- Stall rule (strictly greater age, preference order, one alert per pair):
  `lib.rs:2584-2735` is the documented WDG-002/WDG-003 subset.

## Count

8 carried-behaviour gaps: one real behavioural omission (G1, no
acceptance timeout), two transport/CLI seams (G2, G3), three honest
deviations already named in the header (G5, G7, G8), one bounded-join
difference (G4), and one deliberate scope split (G6). None is faked:
every seam returns a value or an error, never a live effect.
