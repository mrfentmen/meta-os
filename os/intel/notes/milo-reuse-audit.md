# FND-031 — Milo reuse audit: jobs.py sweep + mos/overseer.py tick

Date: 2026-10-26. Scope: what the watchdog (intel/watchdog.py) reuses
verbatim, what it must write new, and what is blocked on schema that does
not exist yet. All line numbers against commit 5485b08 (meta-os main).

## The lease model, as built

- Claim mutex: `jobs.py:90` (`_claim_key`), set with `SET NX EX <lease>`
  at claim time (`jobs.py:498`). Minimum lease 60s (`jobs.py:345,493`),
  default `LEASE_DEFAULT = 1800` (30 min, `jobs.py:71`).
- Mutex gone = lease expired. That is the single source of truth for
  "worker dead or gone": `jobs.py:305` (`_mutex_holder` returns None).
- Claim stores `claimed_at`, `lease_until`, `lease` on the job hash
  (`jobs.py:510`).

## REUSE — read these, do not reimplement

- **Lease-expiry check** — `jobs.py:305` `_mutex_holder`. The watchdog
  reads mutex presence; it never invents its own liveness test.
- **Sweep semantics** — `jobs.py:666` `cmd_sweep`: every claimed job
  whose mutex is gone gets requeued via `jobs.py:312` `_requeue_fields`
  (clears claim fields, status back to open, mutex deleted, REQUEUE
  announced). Prints `REQUEUED <jid>` or `SWEEP_CLEAN`.
- **Manual requeue guard** — `jobs.py:644` `cmd_requeue` refuses when the
  mutex is still active. The watchdog must never requeue; v1 alerts only.
- **Lazy requeue on read** — `jobs.py:323` `_claim_or_requeue`: any read
  of a claimed job with a dead mutex reopens it first. Snapshot readers
  (including the watchdog) see post-sweep state, not stale claims.
- **Renewal semantics** — `jobs.py:547` `_renew_lease` (SET XX EX, with
  NX re-acquire fallback) drives both `cmd_heartbeat` (`jobs.py:565`)
  and `cmd_progress` (`jobs.py:580`). Heartbeat and progress both renew.
- **Overseer tick chassis** — `mos/overseer.py:175` `tick()` already
  runs `jobs.main(["sweep"])`, parses the `REQUEUED` lines into
  `report["swept"]`, calls `capabilities.prune_stale()`, and verifies
  done-but-unverified jobs. The watchdog loop does NOT call sweep again;
  the overseer owns state changes, the watchdog owns alerts.
- **Caps registry + freshness** — `mos/capabilities.py:97` `agents()`,
  `:44` `register`, `:84` `unregister`, `:114` `_fresh`, `:161`
  `prune_stale` (unregisters agents whose heartbeat is stale). The
  presence-stall detector reads the registry; it does not keep its own.
- **Presence listing** — `relay_common.py:167` `presence_list`,
  `:114` `status_get_many`, `:142` `presence_beat`, `:273`
  `nick_holders`. Presence keys are the "worker alive" signal.

## REWRITE — new watchdog-side code, no existing equivalent

- **Presence-stall detector (WDG-002)**: nick in caps registry, presence
  key gone past threshold, holding a claimed job. No existing detector.
- **Progress-stall detector (WDG-003)**: heartbeat alive, no progress
  beyond threshold. Gap: `cmd_progress` (`jobs.py:580`) overwrites the
  single `note` field with no timestamp, and heartbeat updates
  `lease_until` only. The watchdog must observe note *changes* across
  ticks to detect progress, unless jobs.py gains a progress timestamp
  (Pax decision, see below).
- **Lease-risk warning (WDG-004)**: no pre-expiry warning exists
  anywhere; the sweep only acts after expiry.
- **Alert store, dedupe, lifecycle, explanations, drills** (WDG-010
  through WDG-022): entirely new, per plan in `intel/store.py` and
  `intel/watchdog.py`.

## BLOCKED on schema — detectors whose inputs do not exist yet

These need Pax decisions (FND-029 key-shape session) before the
detectors can be written honestly. Verified by grep over jobs.py and
mos/overseer.py at this commit: no such fields exist.

- **Dead-dep / missing-dep (WDG-005, WDG-006)**: no `deps` field on
  the job hash. `cmd_post` (`jobs.py:333`) stores title, room, branch,
  base, accept, status, lease, created_by, created_host, created_at.
  Nothing records what a job depends on.
- **File-collision (WDG-007)**: no `files` field on the job hash, and
  no branch-file index is read anywhere in jobs.py or overseer.py.
  Collision input is TBD: a files field on post, or a branch-diff
  source Pax names.
- **Attempt-exhaustion (WDG-008)**: no `attempts` or `max_attempts`
  field on the job hash. Nothing counts requeues per job today.

## Decisions needed (not mine to make alone)

1. Pax: job-hash schema additions (deps, files, attempts) or alternate
   detector inputs — gates WDG-005/006/007/008.
2. Pax: progress timestamp on the job hash vs watchdog-side note-change
   observation — gates a clean WDG-003.
3. Pax (FND-029): watchdog state key shapes, to be written into
   `intel/store.py` docstring once agreed.
4. Dale (GOV-003): git workflow ruling RULED 2026-10-24: new repo
   meta-os, relay merged as base; lane files updated by INT-012.
