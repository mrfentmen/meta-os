# Failure plan — row by row against the sources (B-L1-140)

`FAILURE.md` was written from intent before the code existed. This is the re-trace: every claim in
it, checked against the symbol that is supposed to implement it. Method: `grep` for the *exact*
name the document uses, then read the function. A claim whose name does not exist in the tree is
not "roughly right" — it is a claim nobody can trace, which is how a failure plan becomes fiction.

Result: **9 claims trace to code, 8 did not.** Two of the eight were code bugs and are fixed in
source today (items 6 and 7 below); the other six were the document naming a mechanism that does
not exist, and the document is corrected to say what is real. Nothing was renamed to make a table
look green. (The count moved from 7 to 8 during the pass: the `bootlog` retention ring was in the
"traced" column by assumption until its own header was read — see item 8.)

## Traced — claim, symbol, line

| Claim in `FAILURE.md` | Symbol | Where | Verdict |
|---|---|---|---|
| "the supervisor's decision table" | `sup_decide` | `services/supervisor/supervisor.goose:398` | TRACED — but the signature is `(slot, exited_clean, uptime_ms) -> (decision, delay_ms)`, not `(policy, code, uptime)`. Corrected below. |
| "restart after backoff" | `sup_backoff_ms` | `supervisor.goose:378` | TRACED — exponential from `base_ms`, clamped to `max_ms`. |
| "give up, mark DEAD" | `RT_GIVE_UP` | `supervisor.goose:354` | TRACED — decision value 1, returned when restarts exceed `max_restarts`. |
| "crash count survives log rotation" | `ServiceEntry.restarts` | `supervisor.goose:74` | TRACED — a field in the slot, not a log line. |
| "start gating on every needs bit" | `bo_ready` | `bootorder.goose:156` | TRACED — `(needs & running) == needs`. |
| "fatal failure cascade" | `bo_cascade` / `bo_is_fatal` | `bootorder.goose:180` / `:145` | TRACED — mask returned, cascade only for fatal. |
| "a non-fatal failure degrades its dependants" | `bo_cascade` | `bootorder.goose:180` | TRACED as a rule: the function returns only the failed service when it is not fatal. |
| "the boot order is a checked table" | `bo_order_ok` | `bootorder.goose:205` | TRACED — and now also proven from outside by `bootorder_check.py` (B-L1-139). |
| "audit degrades rather than fails" | `audit_room` / `audit_dropped_count` | `audit/audit.goose:85` / `:89` | TRACED — records are refused by budget (`AUD_REC_BUDGET`, `:46`) and counted, not silently dropped. |

## Not traced — and what was done about each

### 1. `sup_decide(policy, code, uptime)` — wrong signature (document fixed)

The document describes the policy as an argument. The policy lives in the slot
(`ServiceEntry.policy`, `supervisor.goose:76`), which is deliberate per B-L1-21: one table, so the
policy cannot desync from the entry it describes. Corrected in `FAILURE.md`.

### 2. `RESTART_ALWAYS` / `RESTART_ON_FAILURE` / `RESTART_BACKOFF` / `NO_RESTART` — wrong names (document fixed)

Real names: `RP_ALWAYS`, `RP_ON_FAIL`, `RP_NEVER` (`supervisor.goose:60-62`), plus the decision
values `RT_NOW`, `RT_AFTER`, `RT_LEAVE`, `RT_GIVE_UP` (`:353-356`). There is no
`RESTART_BACKOFF` policy: backoff is a delay returned with the decision, which is why a policy and
a delay can be chosen independently. Corrected in `FAILURE.md`.

### 3. `SVC_CRASHLOOP` — the record does not exist (document corrected to the real mechanism)

No service emits a record by that name, and inventing a record kind here would invent an
interface other layers would have to honour. The mechanism that is real: the slot enters
`ST_FAILED` (`supervisor.goose:40`), `sup_decide` returns `RT_GIVE_UP`, and the supervisor's
`transition_legal` table refuses a further restart. Corrected in `FAILURE.md` to name
`ST_FAILED` + `RT_GIVE_UP`, and flagged below as an open item: a *user-visible* line for a
crash-loop is still only in the plan.

### 4. `BOOT_STEP_MS` — start timeout **not implemented** (open item, not papered over)

`FAILURE.md` promises: "if a service is not RUNNING within `BOOT_STEP_MS` (2000 ms) of its
dependencies being ready, the supervisor gives up on it and treats it as a crash."

There is no such constant, no such timer, and no field on `ServiceEntry` that records when a
service entered `ST_STARTING`. So today a service that spawns and never reports ready holds the
boot where it is, forever, with no record — exactly the failure class the paragraph claims to
cover, and the one class the watchdog cannot see (it only watches services that reached
`RUNNING`).

Why it is not fixed in this pass: it needs a `starting_since_ms` field on `ServiceEntry`, a
parameter for the step budget in `sup_can_start`, and a test that a stall is detected — a
scheduler policy change with no runner to prove it. Written down as the top open item in
`BUFFY_REPORT.md` rather than implemented blind at the end of the build. `FAILURE.md` now says
"planned, not implemented" on that paragraph.

### 5. `WD_TIMEOUT_TICKS` — wrong mechanism (document fixed)

No such constant. The watchdog is per-watch configured: `wd_watch(handle, period_ms, grace_ms,
miss_allow, now_ms)` (`watchdog.goose:73`) arms `deadline_ms = now + period + grace`, and
`wd_check_one` (`:160`) returns `WD_DEAD` once misses exceed the allowance. A single global
timeout would have made a 50 ms input poller and a 30 s updater check share one number.
Corrected in `FAILURE.md`.

### 6. "`wd_register("watchdog", ...)` is refused" — was **not implemented**; now is (code fixed)

The real API is handle-based and there is no name argument, so the documented guard could not have
existed. It was a real defect: a watchdog watching itself reports its own scheduling delay as a
system failure.

Fixed in source today: `wd_set_self(handle)` (`watchdog.goose:61`) records the watchdog's own
handle, and `wd_watch` returns `E_INVAL` for it (`:74`). **Not wired**: nothing calls
`wd_set_self` yet, because the supervisor's watchdog start path is not built — so the guard is
inert until it is. Untested (no runner), and stated as such in the README.

### 7. "`AGENT LAYER DOWN`" — the line did not exist; now it does, as data (code fixed)

`FAILURE.md` promises the agent host's death produces a user-visible line, not just a log entry.
Nothing produced that string. Fixed in source: `AH_DOWN_LINE` and `ah_down_line(out, cap)`
(`agenthost/agenthost.goose:238`), so the console prints it and a test can assert the exact
string. What is still missing is the caller: nothing in the supervisor calls it yet, because the
supervisor's report path is not built. Flagged.

### 8. "`bootlog` buffers into a fixed ring" — there is no ring (document corrected)

The paragraph on losing the log claims `bootlog` keeps early records in a fixed ring and drains
them into `logd` when it starts. `services/bootlog/bootlog.goose` says the opposite in its own
header: retention is planned ("B-L1-11 provides the ring"), and until then records go straight to
the kernel serial line. So the window the plan describes — eight services logging with nowhere to
put it — is real, and the mitigation is not. Corrected in `FAILURE.md`.

What it costs: nothing, *until* a boot needs the early records to explain a failure in `logd`
itself, which is precisely the case the ring was for. It is a small job (wire `common.ring.ring`
into `bootlog`) and it is listed as an open item rather than done here, because it changes what a
record is — buffered until `logd`, then replayed — and that wants a runner to prove.

## What this re-trace says about the plan as a whole

The mechanisms that exist are the mechanical ones: gating, cascade, restart policy, watchdog
expiry, audit budget. The claims that did not trace are the *presentation* claims — the named
record, the named policy, the timeout, the user-visible line — which is the predictable failure of
a plan written before the code: the machinery got built, the vocabulary did not.

Status of every row above: **TRACED** means the code exists and was read, not that it ran. Nothing
in this layer has executed. The drill that would turn these into facts is B-L1-76, and it needs a
kernel.
