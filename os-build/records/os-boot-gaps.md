# Gaps — what `crates/os-boot` does not carry yet (B005)

Deliverable only: these are tasks with the Python source lines named. Nothing here was ported
in this pass. The Rust side is cited where it shows the seam.

## G1 — A real capabilities backend (`register`, `caps`)

Python: `os/mos/cli.py:34-52` calls `capabilities.register` / `capabilities.agents`
(`os/mos/capabilities.py:44-113`), a heartbeated Redis registry.
Rust: `CapabilitiesBackend` trait (`crates/os-boot/src/cli.rs:85-99`); no implementation exists
in any crate. `cmd_register`/`cmd_caps` work only against a test fake.
Port: the registry read/write, freshness rule, and claim index.

## G2 — A real overseer backend (`dispatch`, `tick`, `verify`)

Python: `os/mos/cli.py:54-92` calls `overseer.dispatch`, `overseer.tick`,
`overseer.verify_done` (`os/mos/overseer.py:64-190`).
Rust: `OverseerBackend` trait (`cli.rs:116-142`); no implementation.
Port: job record creation, DM fan-out, lease sweep, acceptance verification, requeue.

## G3 — A real worker backend, and the worker flags it needs

Python: `os/mos/cli.py:94-123` constructs `worker.Worker(dm_secret, caps, roles, workdir,
lease)` (`os/mos/worker.py:57`) and then registers, heartbeats, polls, matches, claims.
Rust: `WorkerBackend` trait (`cli.rs:144-161`); `run_cli` parses `--dm`, `--caps`, `--roles`,
`--workdir`, `--lease` and then discards them (`cli.rs:638-641`, `let _ = (...)`). A caller must
pre-construct the worker, so the flags have no effect. No implementation exists.
Port: worker construction from flags, heartbeat loop, `_matches`, `_claim`, spec fetch.

## G4 — A real reconcile backend

Python: `os/mos/cli.py:125-127` calls `reconcile.main([])`
(`os/mos/reconcile.py:93`), which sweeps leases, requeues done-unverified and blocked jobs.
Rust: `ReconcileBackend` trait (`cli.rs:163-170`); no implementation.

## G5 — Relay identity (`relay_common.NICK`)

Python: `os/mos/cli.py:35,39` reads the relay identity global `rc.NICK` for register/print.
Rust: `MOS_NICK` environment variable (`cli.rs:559`), default empty. There is no relay import
and no refusal on an empty nick: `REGISTERED :` is printable.
Port: resolve the nick the way the Python tree does, or define the env contract and refuse empty.

## G6 — `jobs.job_get`'s header

Python: `os/mos/cli.py:111` unpacks `_, spec = jobs.job_get(jid)`; the header exists and is
dropped at print time.
Rust: `WorkerBackend::job_spec` returns `String` only (`cli.rs:158-160`). The header is not
merely unprinted — it is unavailable to any caller.

## G7 — The argparse surface

Python: `os/mos/cli.py:154-221` uses `argparse` (required subcommand, `-h/--help`, long-option
abbreviations, exact error text, `type=int` conversion).
Rust: a hand parser (`cli.rs:482-536`) implementing only the documented long flags. No `--help`,
no abbreviations, and the usage line replaces argparse's text (`cli.rs:38-41` documents the
approximation).

## G8 — The git timeout

Python: `os/mos/gitops.py:17-30` runs git with `timeout=120` and turns a timeout into
`git <args> timed out`.
Rust: `std::process::Command::output()` with no timeout (`git.rs:20-42`). A hung git hangs the
call indefinitely. Documented at `git.rs:9-12`; not fixed.

## G9 — Full `~` expansion

Python: `os/mos/cli.py:29` uses `os.path.expanduser`, so `~user/path` expands too.
Rust: only a leading `~/` is expanded (`cli.rs:237-245`); `~user/path` is opened literally and
fails with `cannot read ~user/path`.

## G10 — An executable entry point

Python: `os/mos.py:1-10` is the shim that calls `mos.cli.main`; the CLI runs as a program.
Rust: `Cargo.toml` has no `[[bin]]`, and `run_cli` has no caller outside the crate's tests.
A caller must build `Backends` from five trait objects first, which this repository cannot do
(see G1-G4). The port is a library with no entry point.

## G11 — Deployment-asset behaviour is carried, not reimplemented

Python: `os/os/**` scripts and units are executable deployment behaviour.
Rust: `carried.rs` carries the 47 files byte-identical and asserts identity; it never runs them.
This is deliberate ("never rewritten, never ported" — `carried.rs:5-7`). Listed so the gap is
not mistaken for an omission: running the assets belongs to the image lane, not this crate.
