# Service failure table — what a missing service does at boot

Companion to `BOOT_MANIFEST.md`. That file says what the boot order is; this one says what the
boot does when a row is not there, and **where the contract actually says so**.

Rules this table follows:

- A symptom is written from the service's own contract (`services/<name>/*.goose` or its
  `README.md`) and cites the line. Where the contract says nothing about the service being
  absent, the row says **contract silent** and gives only what the supervisor guarantees.
- The supervisor's authority is `services/supervisor/bootorder.goose:45-46`: "`fatal` means the
  layer refuses to continue without it ... Everything else degrades and reports."
- **Not one of these symptoms has been observed**, because no service has been started in this
  order on any machine. This is a reading of contracts, not a boot log. The first real boot
  either confirms it or files a correction.

## The table

| service | contract says (citation) | contract silent on absence? | boot symptom when missing | dependants that die |
|---|---|---|---|---|
| bootlog | refuses a record that does not fit its cap (`bootlog.goose:49,55`) | yes | **boot stops** (fatal); no boot record at all | every later row |
| devices | device state machine treats `DS_ABSENT` as normal, anything may vanish (`devices.goose:193-194`) | yes — device absence, not service absence | **boot stops** (fatal); no inventory for drivers | time, storage, net |
| time | refuses a clock with a nonsense rate at construction (`time.goose:152`) | yes | **boot stops** (fatal); no monotonic clock, so every timeout is undefined | logfmt, watchdog, audit, session, dhcp, socket, timesync, updater |
| storage | no absence statement in `storage.goose` | yes | **boot stops** (fatal); fs, audit, updater, agenthost have no blocks | log, audit, netcfg, fs, updater, agenthost |
| callmatrix | states which edges exist; no absence statement (`callmatrix.goose:63,135`) | yes | **boot stops** (fatal); every service call is unauthorised | supervisor |
| supervisor | it is the starter (`bootorder.goose:45-46`) | no — the header defines the policy | **boot stops** (fatal); the kernel starts nothing else | all table-started services |
| console | escape parser may drop a leading style rather than refuse the call (`esc.goose:315`) | yes | effectively fatal: `log` needs it, so the boot stops | log, input, display, session |
| logfmt | truncates an over-long message and marks it (`logfmt.goose:102,152`) | yes | effectively fatal: `log` needs it, so the boot stops | log, agenthost |
| log | a refused queue slot is counted, not hidden (`logd.goose:32`; `entry.goose:20`) | yes | **boot stops** (fatal); nothing can report the failure that stopped it | audit, input, display, session, dhcp, dns, updater, agenthost |
| watchdog | metric registry is fixed-size and refuses unknowns (`metrics.goose:25`) | yes | boot continues; deaths are noticed only by restart-on-exit | — |
| audit | a full buffer refuses rather than truncating (`audit.goose:83-84`) | yes | boot continues; no audit trail, and `agenthost` dies with it | session, updater, agenthost |
| netcfg | a static address without a mask is refused (`netcfg.goose:275,345`) | yes | boot continues; no interfaces, so the network stack has nothing to bind | net, dhcp, dns, socket |
| net | ARP keeps the oldest entry rather than refusing the new (`arp.goose:13`) | yes | boot continues; no packets, and everything above it dies | dhcp, dns, socket |
| input | events with no buffer are dropped and counted (`input.goose:86`); a bad keymap falls back with `ok=false` (`keymaps2.goose:48`) | yes | boot continues; no key events, no session | session, agenthost |
| display | a width under the ellipsis degrades to a prefix (`text.goose:133`) | yes | boot continues; no draw calls, no session | session, agenthost |
| session | state machine with one honest refusal; an empty token refuses every login (`login.goose:16,147`) | yes | boot continues; nobody is at the console, no agents | agenthost |
| dhcp | unknown options are skipped, a refused request is not retried (`dhcp.goose:262,423`) | yes | boot continues; no lease, static configuration only | — |
| dns | `RCODE_REFUSED` is a real answer code; jump and name length are capped (`dns.goose:27,55`) | yes | boot continues; names do not resolve, socket dies | socket |
| socket | a send with no destination is refused (`socket.goose:202`); `0.0.0.0` refused as a destination (`README.md:40`) | yes | boot continues; no network API above layer 4 | timesync, updater |
| timesync | a server with a different date, or a stale reply, is refused not applied (`timesync.goose:46,186`) | yes | boot continues; the wall clock drifts uncorrected | — |
| updater | a delta is refused unless the base is exactly what it was built against (`delta.goose:15,19`) | yes | boot continues; no updates, no rollback | — |
| agenthost | refuses grants it has no mandate for; no root bit implies others (`agenthost.goose:24,48`) | yes | boot continues; no agent can be spawned, granted or limited | — |

## What this table makes obvious

1. **Twenty-one of the twenty-two contracts say nothing about their own absence.** Only the
   supervisor's header states a policy for a service being missing. Every other contract
   describes what the service does while running, in detail, and is silent on the boot without
   it. That is why the supervisor's `fatal` flag and its cascade are the only real source of
   symptoms for most rows — and why the 7-on-paper / 9-in-effect correction in
   `BOOT_MANIFEST.md` matters.
2. **The most complete failure behaviour belongs to the services that are least fatal.**
   `audit`, `socket`, `updater` and `agenthost` all refuse precisely and say why; the fatal seven
   mostly have no absence statement at all. The failure discipline was built where it was
   interesting, not where it is load-bearing.
3. **Three symptoms are unobservable by design.** `log` missing means the reason is unlogged;
   `console` missing means nothing is displayed; `bootlog` missing means there is no record of
   the attempt. Those three cannot report their own absence, which is the argument for the
   kernel's serial line staying independent of all of them.

## Proposal that follows

Every service README should gain one paragraph: "when this service is not running, the boot
does X". It is four lines per service and it is the difference between a table like this being
a reading of contracts and being a specification. That is a lane-local change to `services/`,
not to anyone's kernel code.
