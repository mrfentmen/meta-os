# `crates/os-supervisor` — Python behaviours not carried yet (B017)

The deliverable is the list, not the port. Each row: what the Python
original does, where it lives, and what the Rust crate does instead
today. Line numbers are in the Python source; the Rust seam is named
beside it. Do not port these here — they belong to the owning batch.

| # | Python behaviour | Source | Rust today | Task for the owner |
|---|---|---|---|---|
| G1 | Live Redis reads/writes for jobs, capabilities, bus | `os/mos/reconcile.py` (`rc.api_get("ping")`, sweep, prune, `_hgetall`) | `ReconcileBackend` seam (`reconcile.rs:31-48`); logic only | Provide a backend impl in the jobs/capabilities batch; wire `reconcile()` at startup. |
| G2 | Live overseer: post job, find workers, send DM, git worktrees | `os/mos/overseer.py` (`_post_job`, `capabilities.find_for`, `send --dm`, `gitops.worktree_add`) | `OverseerBackend` seam (`overseer.rs:62-117`); decision logic only | Provide the backend; keep announcements best-effort. |
| G3 | Alert store: write, dedupe, ack, resolve, query, self-beat | `os/intel/store.py` (`write_alert`, `wd_self_beat`) | `tick`'s `emit`/`beat` callbacks (`watchdog.rs:1813-1910`); `--beat` is a no-op sink (`watchdog.rs:56-63`) | Port the store writer; replace the no-op beat. |
| G4 | Spark polish of explanations | `os/intel/explanations.py` (`polish_explanation`) | `PolishClient` trait + `polish_explanation` (`watchdog.rs:796-831`); no client supplied by default | Supply a client at assembly; keep suggested_fix unpolished. |
| G5 | `journalctl` execution and systemd restarts | `os/intel/watchdog.py` (journal read, `systemctl restart`) | `--journal` reads JSON text from a file; no unit restarts (`watchdog.rs:48-63`, `2042-2123`) | Wire the journal reader and restart rung in the systemd lane (OS-034). |
| G6 | Live 200-job load check with fake Redis and real store writes | `os/intel/watchdog_load_check.py` (seed queue/room, three ticks) | Constants + `evaluate` over caller-supplied outcomes (`watchdog_load_check.rs:1-36`, `429-506`) | Run the live orchestration in the integration batch; `evaluate` stays the assertions. |
| G7 | Relay-watchman CLI: read jobs/agents files, print JSON, sleep, state file | `os/os/watchman/relay_watchman.py` (`main`, `--once`, `--loop`) | `run_once` / `loop_cycle` over `InputLoad`/`StateLoad`; no filesystem (`relay_watchman.rs:30-52`, `407-554`) | Parent CLI shell performs reads/prints; keep decisions here. |
| G8 | Watchman service unit installation and real cycle subprocess | `os/intel/watchman_service.py` (`serve_forever`, systemd unit) | `UNIT_DIRECTIVES` text (`watchman_service.rs:102-116`); `serve_cycles` loop; subprocess seam `default_cycle_fn` (`219-264`) | Install units in the image/boot lane; supply the real cycle fn. |
| G9 | Push actually sent for a dead watchman | `os/intel/push.py` (`blocked_push` send) | Payload built and validated, never sent (`watchman_watch.rs:44-46`, `379-418`) | Send in the push/bus lane; the crate only produces the payload. |
| G10 | Boot sweep actually performed by jobs | `os/intel/watchman_boot.py` (calls `jobs sweep`) | Rings computed; `sweep_mismatch` compares a caller-supplied sweep list (`watchman_boot.rs:217-252`) | Supply the real sweep result from jobs. |
| G11 | Wall-clock and server-time reads used by a live tick | `os/intel/watchdog.py` (`time.time`, `parse_server_time`) | `wall_clock_now` / `parse_server_time` exist (`watchdog.rs:1734-1782`); tests pass explicit `now` | No gap in logic; a live caller must pass the real clock. |
| G12 | `os/mos/reconcile.py` main CLI (`argv`, stdout, exit 2) | `os/mos/reconcile.py` `main()` | `render_summary` + `exit_code` (`reconcile.rs:133-166`); no argv parser | CLI shell in the assembly layer. |

## Not a gap (checked)

- Detector set and severity table: ported (`watchdog.rs:840-1601`).
- Threshold defaults and env fallback: ported twice, identically
  (`thresholds.rs:24-61`, `watchdog.rs:75-212`).
- Watchman state judgement and episode dedupe: ported
  (`watchman_watch.rs:264-479`).
- Boot ring reasons: ported (`watchman_boot.rs:57-59`).

## Count

12 carried-behaviour gaps, all seams or CLI shells; 4 areas checked
with no gap. None is faked in the crate: every seam returns a value or
an error, never a fabricated live result.
