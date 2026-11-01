# FAILURE PLAN — layer 1 (B-L1-65)

Status: **WRITTEN, UNCOMPILED, NEVER EXERCISED.** Nothing in this document has
happened. It describes what the code is supposed to do when something breaks,
and it is written now — before the code runs — because a failure plan invented
after the first crash is a description of the crash, not a plan.

The executable parts are `services/supervisor/supervisor.goose` (restart
policy, `sup_decide`) and `services/supervisor/bootorder.goose` (`bo_cascade`,
`bo_is_fatal`). Where this document and those disagree, the document is the
intent and the code is the bug.

**Re-traced against the sources on 2026-11-01 (B-L1-140): `FAILURE_TRACE.md`.**
That pass found seven claims here that did not name anything real. Two were code
bugs and are fixed (`wd_set_self`, `ah_down_line`); five were this document using
the wrong name, and the corrections are marked **[corrected 2026-11-01]** inline.
One claim — the start timeout — is **not implemented at all** and is marked so.

## The four failure classes

Every failure in this layer is one of four shapes. Naming them is the point:
the response is chosen by class, not by which service happened to die.

### 1. A service exits (cleanly or not)

Handled by the supervisor's decision table `sup_decide(slot, exited_clean,
uptime_ms) -> (decision, delay_ms)` — the policy is read from the slot, not passed
in, so it cannot desync from the entry it describes **[corrected 2026-11-01]**:

| policy | exit | restarts | decision |
|---|---|---|---|
| `RP_ALWAYS` | any | under `max_restarts` | `RT_NOW` or `RT_AFTER(delay)` |
| `RP_ON_FAIL` | 0 (clean) | any | `RT_LEAVE` — stay down |
| `RP_ON_FAIL` | ≠0 | under `max_restarts` | `RT_AFTER(sup_backoff_ms)` |
| `RP_ON_FAIL` / `RP_ALWAYS` | ≠0 | at `max_restarts` | **`RT_GIVE_UP`**, slot → `ST_FAILED` |
| `RP_NEVER` | any | any | `RT_LEAVE` |

There is no separate `RESTART_BACKOFF` policy: the backoff is a property of the
delay returned with the decision (`sup_backoff_ms`, exponential from `base_ms`,
clamped at `max_ms`), which lets the policy and the delay be chosen apart.

The give-up case exists because the alternative is a service that crash-loops
forever and buries the record of why. The count lives in the service's slot
(`sup_slot.crashes`), not in the log, so it survives log rotation.

**A give-up is loud**: the slot goes to `ST_FAILED` and stays there — the state
table refuses the next restart — and if the service is `fatal` in the boot table
the whole layer ends the boot **[corrected 2026-11-01: there is no
`SVC_CRASHLOOP` record; the mechanism is `ST_FAILED` + `RT_GIVE_UP`, and the
user-visible line for a crash-loop is still only in this plan]**. A silent give-up
is the failure mode this design is most afraid of.

### 2. A service hangs

The watchdog (`services/watchdog/`) is the only thing that can see this. Each
service holds a heartbeat token; the watchdog expires it per watch, after
`period_ms + grace_ms` with `miss_allow` misses tolerated, and treats expiry as a
crash (class 1) with `code = E_TIMEOUT` **[corrected 2026-11-01: there is no
`WD_TIMEOUT_TICKS`; timeout is per watch, `wd_watch`/`wd_check_one`]**.

Two rules that matter:

- **The watchdog never kills.** It marks the service DEAD and reports. Killing
  belongs to the supervisor, because two components that both kill is a system
  where a slow service gets killed twice and restarted between the kills.
- **The watchdog cannot watch itself.** It records its own handle once
  (`wd_set_self`) and `wd_watch` refuses it with `E_INVAL`
  **[corrected 2026-11-01: implemented, and not yet wired — nothing calls
  `wd_set_self` until the supervisor's watchdog start path exists]**. Its
  liveness is the supervisor's problem, and the supervisor's liveness is the
  kernel's.

### 3. A dependency is missing

`bo_ready(id, running)` is the gate. A service that starts before its
dependencies is not "early", it is broken: it will read an empty storage, or log
to a log service that does not exist.

- **Start gating**: the supervisor only starts a service when every `needs` bit
  is RUNNING. It does not start it "anyway and let it fail" — the failure is
  indistinguishable from a real bug in the log.
- **Fatal failure cascade**: `bo_cascade(id)` returns the mask of services that
  must also stop. It only cascades when the failed service is `fatal`; a
  non-fatal failure marks its dependants DEGRADED and leaves them running.
- **Timeout**: **NOT IMPLEMENTED (checked 2026-11-01).** The intent is that a
  service not RUNNING within 2000 ms of its dependencies being ready is given up
  on and treated as a crash. There is no `BOOT_STEP_MS`, no timer, and no field
  recording when a slot entered `ST_STARTING` — so a service that spawns and
  never reports ready holds the boot silently. This is the one gap in this plan
  that the watchdog cannot cover either, because it only watches services that
  reached RUNNING. Open item 1 in `BUFFY_REPORT.md`.

### 4. A boot that cannot proceed

If any `fatal` service fails, the layer stops starting new services, records the
service that caused it, and **flushes the log before doing anything else**. The
order matters: abort → flush → report. A machine that aborts and then loses the
reason is worse than one that hangs, because a hang is at least visible.
**[corrected 2026-11-01: the record is not a `BOOT_ABORTED` kind — no such
record exists yet; the flush-then-report order is a rule for the supervisor's
abort path, which is not built.]**

The seven fatal services, as the boot table has them: `bootlog`, `devices`,
`time`, `storage`, `callmatrix`, `supervisor`, `logd`.
**[corrected 2026-11-01: `logd`, not `log` — the boot table's name table is the
service's directory name; `bootorder_check.py` enforces it.]**

## Per-service failure responses

| service | fatal | if it dies | why |
|---|---|---|---|
| bootlog | yes | abort boot | nothing can record what happened |
| devices | yes | abort boot | no storage or clock underneath anything |
| time | yes | abort boot | every record has a timestamp; a wrong one is worse than none |
| storage | yes | abort boot | config, records and the log's backing store are gone |
| callmatrix | yes | abort boot | authorization is not optional; see below |
| supervisor | yes | kernel restart, once | two restarts means the layer is down |
| log | yes | abort boot | see "the log dies" below |
| console | no | degrade to serial | the screen is a display, the serial line is the record |
| logfmt | no | degrade to plain lines | formatting is a nicety; the fields still go out |
| watchdog | no | **loud WARN, keep booting** | unsupervised is degraded, not dead |
| audit | no | WARN + RAM-only records | a full audit disk must not stop the machine |
| netcfg | no | loopback only | a machine with no config still boots |
| net | no | no network, boot continues | offline is a normal state |
| dhcp | no | fall back to static/loopback | |
| dns | no | numeric addresses only | |
| socket | no | network clients fail on their own | |
| timesync | no | clock drifts, WARN | |
| updater | no | no checks this boot | |
| input | no | keyboard-less session | |
| display | no | headless session | |
| session | no | no user session; services still run | |
| agenthost | no | **no agent layer**; must be reported, never silent | a missing agent is the one absence a user cannot see for themselves |

## The three cases that are not a service dying

### The log dies

Losing `log` is fatal, but there is a window — `logd` starts ninth — where
services 1..8 have already written diagnostics with nowhere to put them. So:

- `bootlog` buffers into a fixed ring.
- On `logd` coming up, the ring is drained into it **first**, before any new
  line, so the boot sequence reads in order.
- If `logd` never comes up, the ring is dumped to the console verbatim and the
  boot aborts. A partial record beats no record.

**[corrected 2026-11-01: the ring is not built. `bootlog` writes each record
straight to the kernel serial line in one call and has no retention buffer of its
own — its header says so. The window it describes therefore does not exist
today: early records go to serial and are not replayed into `logd` when it
starts.]**

### The audit disk is full

`audit` degrades rather than fails: records are refused by a fixed budget
(`AUD_REC_BUDGET`) and **counted** (`audit_dropped_count`), so the trail says how
much it lost rather than pretending it lost nothing
**[corrected 2026-11-01: no `AUD_RAM_ENTRIES`, no per-record `TRUNCATED` flag;
the real mechanism is `audit_room` + `aud_dropped`]**. Dropping audit records
silently would make the audit trail a document that lies about its own
completeness, which is the one thing an audit trail must never do.

### The agent host dies

`agenthost` is non-fatal for the machine and **critical for the report**. It is
the last service in the boot order and the only one whose absence is invisible
from the console — the user sees a normal desktop and simply has no agent. So
its death always produces a user-visible line, not just a log entry, and it is
never restarted silently more than twice.
**[corrected 2026-11-01: the line exists as data — `AH_DOWN_LINE` /
`ah_down_line` in `agenthost.goose` — but nothing calls the emitter yet; the
supervisor's report path is not built.]**

## What is deliberately not covered

- **Kernel panics.** That is K4/K5, above this layer. The layer's job is to not
  cause one.
- **Power loss.** `storage` has no journal yet; B-L1-51's records are append-only
  and length-prefixed so a torn tail is detectable and discardable, which is the
  most that can be promised without a journal. Written down so nobody assumes
  durability.
- **A service that is alive and wrong.** No heartbeat detects a service
  returning bad data. Nothing in this layer can; it is a job for tests, not for
  the supervisor.

## The drill this plan asks for

When there is a runner (B-L1-76), each row above gets exercised once: kill the
service, assert the response, and paste the log line into
`os-build/layer1/FAILURE_DRILL.md`. Until that file exists, every claim in this
document is a claim about code nobody has run.
