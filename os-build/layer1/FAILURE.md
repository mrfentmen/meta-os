# FAILURE PLAN — layer 1 (B-L1-65)

Status: **WRITTEN, UNCOMPILED, NEVER EXERCISED.** Nothing in this document has
happened. It describes what the code is supposed to do when something breaks,
and it is written now — before the code runs — because a failure plan invented
after the first crash is a description of the crash, not a plan.

The executable parts are `services/supervisor/supervisor.goose` (restart
policy, `sup_decide`) and `services/supervisor/bootorder.goose` (`bo_cascade`,
`bo_is_fatal`). Where this document and those disagree, the document is the
intent and the code is the bug.

## The four failure classes

Every failure in this layer is one of four shapes. Naming them is the point:
the response is chosen by class, not by which service happened to die.

### 1. A service exits (cleanly or not)

Handled by the supervisor's decision table `sup_decide(policy, code, uptime)`:

| policy | exit | uptime | decision |
|---|---|---|---|
| `RESTART_ALWAYS` | any | any | restart |
| `RESTART_ON_FAILURE` | 0 | any | stay down |
| `RESTART_ON_FAILURE` | ≠0 | < backoff window | restart, after backoff |
| `RESTART_BACKOFF` | ≠0 | ≥ 3 crashes in 60s | **give up**, mark DEAD |
| `NO_RESTART` | any | any | stay down |

The give-up case exists because the alternative is a service that crash-loops
forever and buries the record of why. The count lives in the service's slot
(`sup_slot.crashes`), not in the log, so it survives log rotation.

**A give-up is loud**: it emits `SVC_CRASHLOOP` at WARN, and if the service is
`fatal` in the boot table the whole layer ends the boot. A silent give-up is the
failure mode this design is most afraid of.

### 2. A service hangs

The watchdog (`services/watchdog/`) is the only thing that can see this. Each
service holds a heartbeat token; the watchdog expires it after
`WD_TIMEOUT_TICKS` and treats expiry as a crash (class 1) with `code = E_TIMEOUT`.

Two rules that matter:

- **The watchdog never kills.** It marks the service DEAD and reports. Killing
  belongs to the supervisor, because two components that both kill is a system
  where a slow service gets killed twice and restarted between the kills.
- **The watchdog cannot watch itself.** It is not in its own watch list, and
  `wd_register("watchdog", ...)` is refused. Its liveness is the supervisor's
  problem, and the supervisor's liveness is the kernel's.

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
- **Timeout**: if a service is not RUNNING within `BOOT_STEP_MS` (2000 ms) of
  its dependencies being ready, the supervisor gives up on it and treats it as a
  crash. A boot that waits forever is a boot that reports nothing.

### 4. A boot that cannot proceed

If any `fatal` service fails, the layer stops starting new services, records
`BOOT_ABORTED` with the service that caused it, and **flushes the log before
doing anything else**. The order matters: abort → flush → report. A machine that
aborts and then loses the reason is worse than one that hangs, because a hang is
at least visible.

The seven fatal services: `bootlog`, `devices`, `time`, `storage`, `callmatrix`,
`supervisor`, `log`.

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

Losing `log` is fatal, but there is a window — log starts ninth — where services
1..8 have already written diagnostics with nowhere to put them. So:

- `bootlog` buffers into a fixed ring (capacity set in `common/boot/boot.goose`).
- On `log` coming up, the ring is drained into it **first**, before any new
  line, so the boot sequence reads in order.
- If `log` never comes up, the ring is dumped to the console verbatim and the
  boot aborts. A partial record beats no record.

### The audit disk is full

`audit` degrades rather than fails: it keeps writing to RAM (`AUD_RAM_ENTRIES`)
and sets a `TRUNCATED` flag on every subsequent record. Dropping audit records
silently would make the audit trail a document that lies about its own
completeness, which is the one thing an audit trail must never do.

### The agent host dies

`agenthost` is non-fatal for the machine and **critical for the report**. It is
the last service in the boot order and the only one whose absence is invisible
from the console — the user sees a normal desktop and simply has no agent. So
its death always produces a user-visible line (`AGENT LAYER DOWN`), not just a
log entry, and it is never restarted silently more than twice.

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
