# `crates/os-worker` — config surface (B080)

Every environment variable, argument, constant and file the crate reads.
No flags exist: this is a library, not a binary.

## Environment variables

| Name | Read at | Default | Wrong-value behaviour |
|---|---|---|---|
| `PATH` | `find_binary` (`lib.rs:1497-1514`) | inherited process `PATH` | a binary not found on `PATH` (and not an executable path) is `DriverError::Driver("muse binary not found: …")`; no child spawns (`lib.rs:1648-1656`) |
| `WATCHDOG_STALL_MINUTES` | `StallThresholds::from_env` (`lib.rs:2518-2540`) | `10` | unset, blank, unparseable, or negative falls back to `10` silently; never an error (`lib.rs:2520-2532`) |
| `WATCHDOG_PROGRESS_STALL_MINUTES` | same (`lib.rs:2534-2538`) | `10` | same silent fallback |
| `TMPDIR` (via `std::env::temp_dir`) | `make_tmpdir` (`lib.rs:1516-1524`) for the Muse prompt | the OS temp dir | if the directory cannot be created, `Driver("could not create temp dir: …")`; no child spawns |

The two watchdog variables are the only names the crate reads directly.
`Worker::dm_secret` is a constructor argument, not an env read; the
Python side reads `MUSE_RELAY_NICK`/`MUSE_RELAY_DM_SECRET` in
`os/mos/worker.py`, and that mapping is the caller's job (gap G2).

## Arguments and constants

| Name | Kind | Value / meaning | Where |
|---|---|---|---|
| `DEFAULT_BINARY` | const | `"muse"` | `lib.rs:1434` |
| `NOTE_LIMIT` | const | `200` chars per streamed note | `lib.rs:1437` |
| `BACKOFF_BASE_SECONDS` | const | `5` | `lib.rs:1915` |
| `BACKOFF_CAP_SECONDS` | const | `300` | `lib.rs:1918` |
| `LEASE_DEFAULT_SECONDS` | const | `1800` | `lib.rs:2542` |
| `LOG_NAME` | const | `"driver.log"` | `lib.rs:777` |
| `StallThresholds::defaults()` | fn | `10` / `10` minutes | `lib.rs:2510-2516` |
| `slice_expected()` | fn | `CPUQuota=100%`, `MemoryMax=1G` | `lib.rs:2793-2798` |

## Files and paths

| Path | Access | Purpose | Refusal |
|---|---|---|---|
| `<workdir>/driver.log` | create/append | child stdout and stderr; Muse mirrors stdout lines | open failure is `Driver("could not open driver log: …")`; spawn failure is `Driver("could not launch …")` |
| `<workdir>` | read/write | cwd for the child, snapshot root, acceptance root | must be an existing directory: `Driver("workdir does not exist: …")` (`lib.rs:1264-1272`, `1564-1572`) |
| `<temp>/muse-driver-<pid>-<n>/prompt.md` | write/remove | Muse prompt, outside the workdir so it never pollutes changed files | write failure is `Driver("could not write prompt file: …")`; removed on `wait` (`lib.rs:1789-1792`) |
| `os/os/drivers/CONTRACT.md` | compile-time `include_str!` | embedded contract text | a missing file is a compile error, not a runtime fallback (`lib.rs:1891-1895`) |
| `os/os/drivers/CONFORMANCE.md` | compile-time `include_str!` | embedded conformance text | same (`lib.rs:1897-1900`) |

## Not read here (named, so nobody guesses)

- The job spec JSON file: `run_driver` takes the text; the caller reads
  the file (`os/os/drivers/run_driver.py:36-60` is the Python reader,
  gap G3).
- Redis / bus / capabilities settings: the `WorkerBackend` implements
  them (gap G2).
- Any model endpoint or API key: the crate holds no model and reads no
  secret.
