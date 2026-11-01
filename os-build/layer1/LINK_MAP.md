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
