# `crates/os-worker` — failure drill (B081)

What breaks first when the crate's inputs stop arriving, written from
the code. Another agent can run every phase against the public API; the
expected values are the code's own, not round numbers chosen here.

## Inputs, in the order they usually stop

1. The child stops writing stdout (heartbeats stop, the process lives).
2. The child dies (exit code or signal).
3. The claimant disappears (presence), then its lease expires.
4. The uplink connection drops (orders queue, backoff grows).
5. The bus/queue backend refuses a claim or a finish.

## Phase 0 — baseline

```rust
let dir = std::env::temp_dir().join("os-worker-drill");
std::fs::create_dir_all(&dir)?;
let spec = JobSpec::new("7", "drill", "do the work", vec!["out.txt".into()],
                        "file-exists: out.txt", Some("sig"));
let mut d = StubDriver::new(&dir, None)?;
d.start(&spec, &["sh".into(), "-c".into(), "printf hi > out.txt; echo one".into()])?;
let a = d.wait(None)?;
```

Expected: `a.status == "done"`, `a.exit_code == Some(0)`,
`a.changed_files == ["out.txt"]`, `a.acceptance_ok == true`, and
`d.heartbeats()` empty (StubDriver emits only on `heartbeat()`, not from
child output — `lib.rs:1314-1365`).

## Phase 1 — stdout stops, the process lives

Start `sh -c "printf 'one\n'; sleep 60"` through `MuseDriver` with a
fake binary is not possible (Muse needs `muse`), so drive `StubDriver`:
start `sh -c "sleep 60"`, call `d.heartbeat("still here")` once, then
`d.poll()`.

Expected: `poll()` is `Ok(None)`; `heartbeats()` has exactly one record
with `line == "PROGRESS:7 still here"`; no new record appears on its
own. **First thing that breaks is progress, not liveness** — a quiet
driver looks alive at `poll()` and stall-free only until the progress
window passes (`lib.rs:2680-2714`).

Stop it with `d.stop()`; expect `status == "stopped"` and a negative
`exit_code` (`-15` when SIGTERM landed).

## Phase 2 — the child dies

Start `sh -c "exit 3"`, `wait(None)`.

Expected: `status == "failed"`, `exit_code == Some(3)`, artifacts still
built (the diff and acceptance run even on failure —
`lib.rs:1091-1099`). No panic, no invented success.

## Phase 3 — presence disappears, then the lease expires

Build the drill snapshot from `lib.rs:2905-2925`: caps `["pax"]`,
presence `["pax"]`, job `7` claimed by `pax`, `last_progress = T0+120`,
`T0 = 100000`.

1. Tick at `T0+300` with defaults (`10` min): **zero alerts**
   (`age = 180 <= 600`).
2. Remove `pax` from presence, tick at `T0+300+600+61`: **exactly one**
   `presence-stall`, `nick == "pax"`, `job == "7"`,
   `last_progress_age_seconds == 961`, `dedupe_key ==
   "presence-stall:pax:7"`.
3. `sweep_expired_leases` at `stall_at` with
   `lease_until = T0+1800`: **no requeue** (lease still holds).
4. Sweep at `T0+1800` (the boundary; the code requeues when
   `now >= lease_until`, `lib.rs:2866-2872`): **requeue one**, job
   `open`, `claim`/`claim_host`/`claimed_at`/`lease_until` all `None`.
5. Re-tick with the job open: **zero alerts**.

Expected order matters: the drill fails if phase 3 requeues early or
phase 4 leaves the claim behind.

## Phase 4 — the uplink drops

`uplink_tick(&UplinkState::default(), &[order], 1000, false, None, false)`.

Expected: one `queued` event; `failures == 1`;
`next_retry_at == Some(1005)` (`backoff_seconds(1) == 5`). A second
disconnected tick with `failures == 1`: `next_retry_at == 1010`
(`backoff_seconds(2) == 10`). At `failures == 9` the wait is capped at
`300` (`lib.rs:1922-1936`).

Then `connected = true` with the same order: the pending order drains
**first**, yielding `intake` with a signature when a key is supplied;
the same id delivered again is `duplicate` and the state does not grow
(`lib.rs:2108-2184`).

## Phase 5 — the backend refuses

A `WorkerBackend` whose `claim` returns `(false, "no such job")`:
`Worker::run_once` puts one line in `errors` (`"claim 7: no such job"`),
`claimed` stays empty, the handler is never called
(`lib.rs:2437-2445`). A `finish` returning `false` yields
`"done 7: finish failed"` in `errors` after the job is in `claimed`
(`lib.rs:2451-2455`).

## What the drill proves and what it does not

- Proves the decision rules and the record shapes at fixed inputs.
- Does **not** prove a live bus, a live Muse CLI, or a real watchdog
  (gaps G2, G3, G6). A green drill is not a green worker fleet.
- The whole drill runs without network, Redis, or a model: it needs
  only `cargo test -p os-worker` on a machine with `sh`.
