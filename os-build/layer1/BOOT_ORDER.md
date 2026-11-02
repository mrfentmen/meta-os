# BOOT ORDER — layer 1 (B-L1-64)

Status: **WRITTEN, UNCOMPILED.** `services/supervisor/bootorder.goose` is the
executable copy of this table; this file is the argument for it. If the two
disagree, the `.goose` file is wrong, not this document — but tell Milo, because
a table that drifted from its note is how a boot sequence gets quietly reordered.

## The sequence

29 services. The `#` column is `BootEntry.order`; `needs` is the bitmask in the
file, written here as names because nobody audits base-2 in their head. The bitmask uses
this table's own ids (1..29, contiguous), not the call matrix's — the two agreed only as far
as id 1, and `bootorder_check.py` proves these are consistent with each other.

| # | service | needs (must be RUNNING first) | fatal | started by |
|---|---|---|---|---|
| 1 | bootlog | — | yes | table |
| 2 | devices | bootlog | yes | table |
| 3 | time | devices | yes | table |
| 4 | storage | devices | yes | table |
| 5 | callmatrix | — | yes | table |
| 6 | **supervisor** | callmatrix | yes | **kernel** |
| 7 | console | bootlog | no | table |
| 8 | logfmt | time | no | table |
| 9 | log | console, logfmt, storage | yes | table |
| 10 | watchdog | time | no | table |
| 11 | audit | log, storage, time | no | table |
| 12 | netcfg | storage | no | table |
| 13 | net | devices, netcfg | no | table |
| 14 | input | log | no | table |
| 15 | display | log | no | table |
| 16 | session | audit, display, input | no | table |
| 17 | dhcp | log, net, netcfg, time | no | table |
| 18 | dns | log, net, netcfg | no | table |
| 19 | socket | dns, log, net, time | no | table |
| 20 | timesync | log, socket, time | no | table |
| 21 | updater | audit, log, socket, storage, time | no | table |
| 22 | agenthost | audit, log, session, storage, supervisor | no | table |
| 23 | settings | log, storage | no | table |
| 24 | wallpaper | log, settings, storage | no | table |
| 25 | dock | log, session, settings, storage | no | table |
| 26 | dashboard | log, session, settings, supervisor, watchdog | no | table |
| 27 | updater_client | log, net, socket, time, updater | no | table |
| 28 | board | log, net, storage, time | no | table |
| 29 | notify | log, time | no | table |

`notify` is last because it is what the others push into: a feed that started before its
producers would be a feed whose first events had nowhere to go. It needs only `log` and
`time`, so it never waits on the face services that call it — `board` and `updater_client`
have that edge declared in the call matrix and dormant until one of them imports it.

## Why the supervisor is number six and not number one

The kernel starts the supervisor; the supervisor starts everything else. So the
supervisor cannot be gated on `log` being up even though it logs — the log
service is one of the things it starts. `BootEntry.by_kernel` marks that single
exception, and its `needs` field then means "what its own table wants at
runtime" (`callmatrix`, its authorization source) rather than "what must already
be running".

Writing it as an ordinary dependency would put the starter last in its own
start order. That table reads perfectly and cannot boot, which is exactly the
class of mistake this note exists to make visible.

## Why this order and not a clever one

1. **Nothing before `log` may need `log`.** The first five services either write
   to the console directly (`bootlog`) or to storage (`devices`, `storage`).
   Their diagnostics are buffered and flushed once `log` is up; they do not
   block on it.
2. **`log` before the network.** A network stack that starts before the log
   service has nowhere to report a failed DHCP handshake.
3. **`watchdog` before `audit` and the network.** The watchdog is the thing that
   notices a service died; starting it after the services it supervises leaves a
   window with no supervision. It needs only `time`.
4. **`session` before the network clients.** `display`/`input` are what a user
   sees; a session that comes up after DHCP is a machine that sits black for two
   seconds while it negotiates.
5. **`agenthost` last.** It needs the supervisor (to be granted services), the
   session (to be a citizen of it), audit (to record grants) and storage (for
   its record). Nothing may depend on the agent host, so it is never a
   bottleneck.
6. **The six face services are dead last, and none of them is fatal.** They are the
   things the home surface draws: settings, wallpaper, dock, the dashboard feed, the
   updater's client half and the board client. Each is a window onto something that
   already works, so a face service that hangs costs the user a pane, not a boot — which
   is the only reason a service this late is allowed to exist at all.
7. **`updater` second-to-last.** It needs a socket, storage and audit — i.e. the
   whole floor — and nothing needs it. An updater that runs before the network
   is a service that fails its first check every boot and logs a lie.

## The invariant the table is checked against

`bo_order_ok()` walks `order` 1..28 and returns false the moment a `needs` bit
refers to a service whose order is not strictly smaller. The generator that
produced the table asserted the same invariant before writing the file, so the
static check and the runtime check cannot disagree without a hand edit — and a
hand edit is what the check is for.

## What is NOT in this table

- **Kernel threads** (the idle loop, the timer, the interrupt dispatch). K3/K4.
  They exist before any of this and are not services.
- **The dev carrier.** Layer 1 runs on it (B-L1-73..77) with the same ids and the
  same table; only `SVC_START` is a host function instead of a kernel syscall.
- **Anything agent-facing.** `agenthost` is the last row on purpose: the agent
  layer gets a machine that already booted, never one mid-boot.

## Failure behaviour

`boot_entry(id).fatal` decides whether a failure stops the boot. The seven
fatal rows are `bootlog`, `devices`, `time`, `storage`, `callmatrix`,
`supervisor`, `log` — no logging, no clock, no storage or no authorization means
the layer is not running, it is merely present. Everything else degrades:
`bo_cascade` marks dependants DEAD and the boot continues with a shorter
service list. Full plan: `FAILURE.md` (B-L1-65).

## Unverified

No service has been started, in this order or any other. There is no kernel and
no dev carrier runner yet. This document describes an intended sequence; the
first row that matters is the one Milo writes down when something actually
boots.
