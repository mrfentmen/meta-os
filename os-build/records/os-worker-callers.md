# `crates/os-worker` — callers and expectations (B079)

Every place in the repo that names this crate, what it expects, and
whether the crate meets it.

## Inside the crate (the real call graph today)

The crate is one module; these are the load-bearing internal calls.

| Caller | Callee | Expectation | Met? |
|---|---|---|---|
| `StubDriver::start` (`lib.rs:1314-1365`) | `validate_spec`, `snapshot` | refuse before spawning on any bad spec; snapshot after the log opens | yes (`lib.rs:1322`, `1341-1343`) |
| `StubDriver::wait` (`lib.rs:1395-1419`) | `wait_child`, `compute_artifacts` | timeout is an error; artifacts from the on-disk workdir | yes |
| `MuseDriver::start` (`lib.rs:1636-1736`) | `validate_spec`, `find_binary`, `build_prompt`, `build_argv` | no child when the binary is missing; prompt outside the workdir | yes (`1648-1656`, `1678-1691`) |
| `MuseDriver::wait` (`lib.rs:1765-1796`) | `wait_child`, reader join, `compute_artifacts`, temp cleanup | exit code, stream drained, prompt removed | yes; join is unbounded (finding 4) |
| `run_driver` (`lib.rs:1821-1840`) | `parse_json`, `spec_from_json`, `MuseDriver` | every failure becomes an `Err` string with the `run_driver:` prefix | yes |
| `Worker::run_once` (`lib.rs:2417-2472`) | `WorkerBackend` methods, `tail_chars`, `head_chars` | transport is the caller's; truncation is the loop's | yes |
| `uplink_tick` (`lib.rs:2108-2184`) | `validate_order`, `record_failure`, `record_success`, `take_in` | inputs untouched; new state returned | yes |
| `run_kill_worker_drill` (`lib.rs:2897-3001`) | `tick_stalls`, `announcements_for`, `sweep_expired_leases` | four phases, exact alert, no early requeue | yes |
| `hmac_sha256_hex` (`lib.rs:177-199`) | `sha256` | RFC 2104 digest | yes |
| `compute_artifacts` (`lib.rs:1061-1110`) | `snapshot`, `verify_accept`, `sha256_hex` | diff excludes the log; acceptance from disk | yes |

## Outside the crate

| Caller | What it expects | Met? |
|---|---|---|
| Workspace member list `Cargo.toml:20` | the crate builds as `os-worker` | yes (single-crate check) |
| `crates/os-boot/src/cli.rs:143` | comment only: "The real implementation lives in the B22 crate (`os-worker`)" | it points at this crate; **no call** is made |
| `crates/parity-tests/src/tests/test_os_uplink.rs:5` | comment: "os-worker still the B00 skeleton" | **stale** — the crate is the B22 port (finding 5). No code call |
| `os-build/records/os-supervisor-callers.md:30` | cites `crates/os-worker/src/lib.rs:43` as a documentation seam for B21 | it is a comment; no call |
| `os-build/aegis/DRILL.json:82` | lists `crates/os-worker/Cargo.toml` as scanned code | yes; scan metadata only |
| `BATCHES.md:56`, `batches/B22.md:1-66`, `docs/RUST_REBUILD_PLAN.md:240`, `SUPER_PROMPT.md:263-277` | the B22 port task set and completion-report shape | the module exists; this file is not the batch report |

## Flag

No crate outside `os-worker` imports or calls its API. The only
consumers are the crate's own modules, its tests, and comments that
point at it. That is expected while B22 is a library in progress, but
it means: **a green `cargo test -p os-worker` is the only external
evidence today**. Any claim that another program "uses the worker
runtime" is a comment-derived claim, not a call-site fact. The
`parity-tests` comment is actively wrong and should be corrected by its
owner (B079 files it; this lane does not edit another crate).
