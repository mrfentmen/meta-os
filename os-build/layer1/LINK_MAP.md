# Layer 4 link map (B-L1-63)

Drawn from the sources, not from the plan. Every row below was read out of the file named in
the first column (`grep '^import'` and the call sites), so a row that looks wrong is a row to
argue with in the source.

## 1. Service → library (`import` edges, all of them)

These are real compile-time edges: the module is in scope in that file.

| Service | Imports | For |
|---|---|---|
| `bootlog` | `std` | `format` for the record line |
| `console` | `common.sys.sys`, `common.ring.ring`, `common.err.err` | write calls, history ring, codes |
| `logd` | `common.sys.sys`, `common.ring.ring`, `common.err.err`, `common.fmt.fmt` | flush, record ring, codes, formatting |
| `time` | `std` | `format`-class helpers in the clock paths |
| `supervisor` | `common.err.err`, `common.ring.ring` | codes, backoff/history ring |
| `watchdog` | `common.err.err` | codes |
| `devices` | `common.boot.boot`, `common.err.err` | `BootInfo`, codes |
| `storage` | `common.err.err` | codes |
| `input` | `common.err.err` | codes |
| `display` | `common.err.err` | codes |
| `net` | `common.err.err` | codes |
| `netcfg` | `common.cfg.cfg`, `common.err.err` | config text, codes |
| `dhcp` | `common.err.err`, `netcfg.netcfg` | codes, `Ipv4`/`ip4` |
| `dns` | `common.err.err`, `netcfg.netcfg` | codes, address model |
| `socket` | `common.err.err`, `netcfg.netcfg` | codes, address model |
| `updater` | `common.err.err`, `common.hash.hash` | codes, SHA-256 verification |
| `timesync` | `common.err.err` | codes |
| `agenthost` | `common.err.err` | codes |
| `audit` | `common.err.err` | codes |
| `session` | `common.err.err` | codes |
| `callmatrix` | `common.err.err` | codes |
| `logfmt` | `common.err.err` | codes |

**Warning this table exposes:** `dhcp`, `dns` and `socket` import `netcfg.netcfg` as a
LIBRARY, which means the address model is linked into each of them. That is fine while
`netcfg` is a data model, and it stops being fine the moment `netcfg` starts owning runtime
state (a lease, an interface up/down flag): three copies of the state would then exist.
Recorded as a question for the K6 integration, not resolved here.

## 2. Service → service (declared, not yet linked)

No service in this tree imports another service. Every intended edge is expressed twice:
as a row in `services/callmatrix/callmatrix.goose` (`cm_init`), and as a name looked up
through the supervisor's registry. So the matrix below is POLICY, and there is no code yet
that would fail if it were wrong. That is the honest state: the enforcement point
(`cm_allows`, called from the registry) exists; the callers that would exercise it do not.

| Caller | May call | Why |
|---|---|---|
| `bootlog` | console, log, time, devices | early output, then hand off |
| `console` | bootlog, log | record what was typed |
| `log` | console, storage, logfmt, time | mirror to screen, persist, format, stamp |
| `logfmt` | time | timestamp |
| `time` | devices | tick rate from BootInfo |
| `supervisor` | log, watchdog, session, audit, time, agenthost | the lifecycle owner |
| `watchdog` | supervisor, time, log | escalate, stamp, record |
| `devices` | log, bootlog | device changes |
| `storage` | log, devices | I/O failures |
| `input` | session, display, log | route keys |
| `display` | session, log | which console is visible |
| `net` | netcfg, log, devices | link settings |
| `netcfg` | net, storage, log | persistence |
| `dhcp` | net, netcfg, time, log | lease timing |
| `dns` | net, netcfg, log | queries |
| `socket` | net, dns, log, time | datagrams, deadlines |
| `updater` | socket, storage, audit, log, time | fetch, verify, record |
| `timesync` | socket, time, log | measure, hold the offset |
| `agenthost` | supervisor, audit, session, log, time, storage | lifecycle, grants |
| `audit` | storage, time, log | write, stamp |
| `session` | display, input, audit, log, time | focus, keys, records |

## 3. Cycles in the declared map

Present, and deliberate:

- `bootlog ↔ console`: the console's first lines are boot-log lines, and the boot log writes
  through the console. Broken at runtime by ORDER (bootlog is written before console exists),
  not by the matrix.
- `input ↔ session/display`, `display ↔ session`: the focus decision genuinely is mutual.
- `net ↔ netcfg`, `log ↔ console`.

A call matrix cannot express order, and pretending otherwise is how a startup deadlock is
designed in. Order is `os-build/layer1/BOOT_ORDER.md`'s job, and the supervisor's start
sequence is the only thing that resolves these.

## 4. Edges to Layers 1–3

Only `bootlog`, `time`, `display` and `net` declare `extern fn` calls. Everything else reaches
the kernel through `common/sys/sys.goose` or not at all. That is deliberate: one file to change
when K6 publishes a different signature.

---

# Round 2 — regenerated after Waves G–J (B-L1-138)

Round 1 above was drawn by hand before the network, filesystem and shell waves landed. Round 2
is `python3 os-build/layer1/linkmap.py`, which reads `^import` out of every `.goose` file and
compares the result against the round-1 table parsed back out of this file. So the drift below
is measured, not remembered.

Measured: **26 services with source, 74 Goose files, 46 service→service edges.** Round 1 read
23 services; `example`, `fs`, `shell` and `tests` were not in it.

## Drift vs round 1

| Service | Gained | Why |
|---|---|---|
| `agenthost` | `common.fmt.fmt` | quota/channel messages format numbers |
| `net` | `net.net` + `netcfg.netcfg` | Waves G–H modules (IP/ARP/ICMP/UDP/TCP, loopback) share the address model |
| `netcfg` | `common.fmt.fmt`, `fs.fs` | `persist.goose` (B-L1-104) writes its config through the filesystem |
| `socket` | `net.net` | `bind.goose` binds a real UDP endpoint |
| `time` | `common.err.err` | calendar/zones return registry codes |
| `updater` | `common.enc.enc`, `common.fmt.fmt` | delta encoding (B-L1-121) and manifest printing |
| `supervisor`, `watchdog` | `common.fmt.fmt` | dependency messages and metric lines |
| `audit`, `input`, `session` | own-module import | see the question below |
| `fs`, `shell`, `example`, `tests` | — | new since round 1 |

Nothing was removed: every round-1 edge still exists in source. Round 1's warning stands
unchanged — `dhcp`, `dns`, `socket` still import `netcfg.netcfg` as a library, so the address
model is compiled into four places.

## The one new question this round surfaces

Eleven files import their own service's module (`services/socket/bind.goose` does
`import socket.socket;`, `services/agenthost/*` does `import agenthost.agenthost;`, and the same
in `audit`, `input`, `net`, `netcfg`, `session`, `supervisor`, `updater`, `tests`).

That is how a sibling file reaches the types its own service defines, and it is correct **if**
Goose treats one directory as one package and makes the import a no-op. If it instead pulls the
module in twice, every symbol in it is defined twice at link. Filed as Q-B-L1-21 in
`os-build/layer1/K6_NEEDS.md`: *does a file importing its own package's module duplicate
definitions?* Until answered, status stays WRITTEN.

## Reading these numbers honestly

An import edge is not a permission and not a call: `services/fs/fs.goose` importing `storage`
says the block API is in scope, not that `fs` is allowed to call it at runtime. The permission
question lives in `CALLMATRIX_DRIFT.md`: every import edge in this map now has a permission (round 2
added the last twelve, and ids 22–24 for `fs`, `shell` and the template), and what remains open is
the 67 rows that allow a call no import makes. Both documents are true at once; the map is what the
linker sees, the matrix is what the kernel enforces.
