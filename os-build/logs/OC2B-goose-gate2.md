# OC2B §19 — Goose gate-2 on the Mac (OC2B-457–467, 468, 471)

Branch: `opencode2/500`. No goose runner files fixed or edited (Buffy R12 owns the runner —
errors below are filed FOR her, verbatim). `services/run-goose-tests.sh` was **grepped only,
never executed**. `tests/` additions: none.
Method (no file edits): per-file `$GOOSE check <file>` with cwd=`services/`,
`GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose` supplied on the command line.
`check` = parse + typecheck, run nothing — the right gate without a kernel (BUILD.md: running
needs K6). Warnings do not fail a file; exit code decides PASS/FAIL.
Ordering: files 1–6 = the six named roots; files 7–30 = services/MANIFEST.md build order
(primary `<svc>/<svc>.goose`; registry/devmgr/sockets are README-only → SKIP, no source to check);
files 31–53 = remaining service dirs alphabetically (all `.goose` files). `common/` libs excluded
by definition (not service files). Total covered: **53 entries (50 checked + 3 SKIP)**.

## OC2B-457 — goose binary (path + version)

- Path: `/Users/test/mcp-servers/toolchains/goose-src/build/goose`
- Version: `goose b781587 (runtime 3901ec457ba9)` (`goose version` and `goose --version` agree)
- Size/date: 9,319,256 bytes, built Nov 1 12:42. Secondary copy `/opt/homebrew/bin/goose` reports the same version.

## OC2B-471 — build provenance (for the toolchain report)

- Source: `/Users/test/mcp-servers/toolchains/goose-src` (git HEAD `b78158797a3a4199a2c519d90d4e5421b2760fe3`
  — `fix: allow packaging without builtin libs and static link MinGW (#155)`).
- Binary: `/Users/test/mcp-servers/toolchains/goose-src/build/goose`, md5 `d4b72870edd8c7c763e12626d7728362`.
- Locating followed `services/BUILD.md` (Goose→C recipe, `goose -o <out.c> <in.goose>`); no build was needed —
  a compiled binary already existed at the toolchain path.

## OC2B-458 — does run-goose-tests.sh still hardcode the toolchain path?

Yes. `grep -c "/Users/test/mcp-servers/toolchains/goose-src/build/goose" services/run-goose-tests.sh` → `1`,
line 8: `GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose` (unconditional assignment —
`GOOSE=... sh run-goose-tests.sh` cannot override it; hence the per-file direct-binary method above).
On this Mac the hardcoded path happens to exist and work; on any other machine the runner breaks.
Diff sketch proposed (NOT applied) at the end of this file.

## OC2B-459 — root cluster: root.goose, root_bootlog.goose, root_console.goose

- File 1 `root.goose` → **PASS** (exit 0; 130 warning lines, all `redundant as i64/u64` style, e.g.
  `updater/updater.goose:167: warning: redundant \`as i64\`: a u8 converts to i64 implicitly here`).
  The whole library typechecks through this root.
- File 2 `root_bootlog.goose` → **PASS** (exit 0, no output).
- File 3 `root_console.goose` → **PASS** (exit 0, no output).

## OC2B-460 — root_example.goose + root_logd.goose + root_time.goose

- File 4 `root_example.goose` → **PASS** (exit 0; 18 warning lines, same redundant-cast style,
  e.g. `example/example.goose:181: warning: redundant \`as u64\`: a u32 converts to u64 implicitly here`).
- File 5 `root_logd.goose` → **PASS** (exit 0, no output).
- File 6 `root_time.goose` → **PASS** (exit 0, no output).

## OC2B-461 — files 7–16 in MANIFEST order

- File 7 `bootlog/bootlog.goose` (MANIFEST #1 bootlog) → **FAIL** (exit 1; module-resolution, see §466)
- File 8 `console/console.goose` (MANIFEST #2 console) → **FAIL** (exit 1)
- File 9 `time/time.goose` (MANIFEST #3 time) → **FAIL** (exit 1)
- File 10 `logfmt/logfmt.goose` (MANIFEST #4 logfmt) → **FAIL** (exit 1)
- File 11 `logd/logd.goose` (MANIFEST #5 logd) → **FAIL** (exit 1)
- File 12 `supervisor/supervisor.goose` (MANIFEST #6 supervisor) → **FAIL** (exit 1)
- File 13 `registry` (MANIFEST #7 registry) → **SKIP** (NOT BUILT, README-only, no `.goose` source to check)
- File 14 `watchdog/watchdog.goose` (MANIFEST #8 watchdog) → **FAIL** (exit 1)
- File 15 `devmgr` (MANIFEST #9 devmgr) → **SKIP** (NOT BUILT, README-only, no `.goose` source to check)
- File 16 `storage/storage.goose` (MANIFEST #10 storage) → **FAIL** (exit 1)

## OC2B-462 — files 17–26 in MANIFEST order

- File 17 `input/input.goose` (MANIFEST #11 input) → **FAIL** (exit 1)
- File 18 `display/display.goose` (MANIFEST #12 display) → **FAIL** (exit 1)
- File 19 `netcfg/netcfg.goose` (MANIFEST #13 netcfg) → **FAIL** (exit 1)
- File 20 `dhcp/dhcp.goose` (MANIFEST #14 dhcp) → **FAIL** (exit 1)
- File 21 `dns/dns.goose` (MANIFEST #15 dns) → **FAIL** (exit 1)
- File 22 `sockets` (MANIFEST #16 sockets) → **SKIP** (NOT BUILT, README-only, no `.goose` source to check)
- File 23 `timesync/timesync.goose` (MANIFEST #17 timesync) → **FAIL** (exit 1)
- File 24 `updater/updater.goose` (MANIFEST #18 updater) → **FAIL** (exit 1)
- File 25 `audit/audit.goose` (MANIFEST #19 audit) → **FAIL** (exit 1)
- File 26 `agenthost/agenthost.goose` (MANIFEST #20 agenthost) → **FAIL** (exit 1)

## OC2B-463 — files 27–36

- File 27 `session/session.goose` (MANIFEST #21 session) → **FAIL** (exit 1)
- File 28 `fs/fs.goose` (MANIFEST #22 fs) → **FAIL** (exit 1)
- File 29 `shell/shell.goose` (MANIFEST #23 shell) → **FAIL** (exit 1)
- File 30 `example/example.goose` (MANIFEST #24 example) → **FAIL** (exit 1)
- File 31 `board/board.goose` (extra) → **FAIL** (exit 1)
- File 32 `callmatrix/callmatrix.goose` (extra) → **FAIL** (exit 1)
- File 33 `dashboard/dashboard.goose` (extra) → **FAIL** (exit 1)
- File 34 `devices/devices.goose` (extra) → **FAIL** (exit 1)
- File 35 `devices/hotplug.goose` (extra) → **FAIL** (exit 1)
- File 36 `dock/dock.goose` (extra) → **FAIL** (exit 1)

## OC2B-464 — files 37 to the end (17 files)

- File 37 `echo/echo.goose` (extra) → **PASS** (exit 0, no output)
- File 38 `heartbeat/heartbeat.goose` (extra) → **PASS** (exit 0, no output)
- File 39 `hello/hello.goose` (extra) → **PASS** (exit 0, no output)
- File 40 `mcp-host/host.goose` (extra) → **PASS** (exit 0, no output)
- File 41 `net/arp.goose` (extra) → **FAIL** (exit 1)
- File 42 `net/icmp.goose` (extra) → **FAIL** (exit 1)
- File 43 `net/ip.goose` (extra) → **FAIL** (exit 1)
- File 44 `net/loopback.goose` (extra) → **FAIL** (exit 1)
- File 45 `net/packet.goose` (extra) → **FAIL** (exit 1)
- File 46 `net/tcp.goose` (extra) → **FAIL** (exit 1)
- File 47 `net/udp.goose` (extra) → **FAIL** (exit 1)
- File 48 `notify/notify.goose` (extra) → **FAIL** (exit 1)
- File 49 `settings/settings.goose` (extra) → **FAIL** (exit 1)
- File 50 `socket/bind.goose` (extra) → **FAIL** (exit 1)
- File 51 `socket/socket.goose` (extra) → **FAIL** (exit 1)
- File 52 `updater_client/updater_client.goose` (extra) → **FAIL** (exit 1)
- File 53 `wallpaper/wallpaper.goose` (extra) → **FAIL** (exit 1)

Total files covered: **53 entries (50 checked + 3 SKIP)**. No files beyond 53: the remaining
`.goose` files under `services/` live in `common/` (libraries, out of scope) and `services/tests/`
(harness fixtures, out of scope) — stated so the count is auditable.

## OC2B-465 — gate-2 table

| Outcome | Count | Files |
|---|---|---|
| PASS | 10 | root.goose, root_bootlog.goose, root_console.goose, root_example.goose, root_logd.goose, root_time.goose, echo/echo.goose, heartbeat/heartbeat.goose, hello/hello.goose, mcp-host/host.goose |
| FAIL | 40 | bootlog, console, time, logfmt, logd, supervisor, watchdog, storage, input, display, netcfg, dhcp, dns, timesync, updater, audit, agenthost, session, fs, shell, example, board, callmatrix, dashboard, devices, devices/hotplug, dock, net/arp, net/icmp, net/ip, net/loopback, net/packet, net/tcp, net/udp, notify, settings, socket/bind, socket/socket, updater_client, wallpaper (each `<svc>/<svc>.goose` unless noted) |
| SKIP (NOT BUILT, no source) | 3 | registry, devmgr, sockets |
| **Total** | **53** | 50 checked + 3 SKIP |

Reading: the 6 roots pass (the library typechecks as a whole through `root.goose`, exit 0),
and the 4 import-free standalone programs pass. All 40 failures share ONE cause (next section) —
they are a runner-resolution finding, not 40 independent code verdicts. No source file was fixed
on this branch.

## OC2B-466 — first error line verbatim per failing file (record for Buffy R12; no fixes)

Common cause (exemplar full block, `bootlog/bootlog.goose`):
```
bootlog/bootlog.goose:27: error: cannot find the module common.fmt.fmt, looked for
    /Users/test/meta-os-500/services/bootlog/common/fmt/fmt.goose
    /Users/test/mcp-servers/toolchains/goose-src/stdlib/common/fmt/fmt.goose
bootlog/bootlog.goose:28: error: cannot find the module common.sys.sys, looked for
    /Users/test/meta-os-500/services/bootlog/common/sys/sys.goose
    /Users/test/mcp-servers/toolchains/goose-src/stdlib/common/sys/sys.goose
```
`goose check <service-file>` resolves `import common.…` relative to the FILE's own directory (then the
toolchain stdlib), not relative to the services root — the root files work because imports resolve
from the root's directory (per the `root.goose` header comment, Pax ruling F3). Same failure from the
service's own directory (verified `cd bootlog && goose check bootlog.goose` → exit 1, identical error).
Per-file first error lines:

- `console/console.goose:24: error: cannot find the module common.sys.sys, looked for`
- `time/time.goose:23: error: cannot find the module common.sys.sys, looked for`
- `logfmt/logfmt.goose:38: error: cannot find the module common.err.err, looked for`
- `logd/logd.goose:35: error: cannot find the module common.sys.sys, looked for`
- `supervisor/supervisor.goose:29: error: cannot find the module common.err.err, looked for`
- `watchdog/watchdog.goose:34: error: cannot find the module common.err.err, looked for`
- `storage/storage.goose:30: error: cannot find the module common.err.err, looked for`
- `input/input.goose:34: error: cannot find the module common.err.err, looked for`
- `display/display.goose:30: error: cannot find the module common.err.err, looked for`
- `netcfg/netcfg.goose:27: error: cannot find the module common.cfg.cfg, looked for`
- `dhcp/dhcp.goose:34: error: cannot find the module common.err.err, looked for`
- `dns/dns.goose:38: error: cannot find the module common.err.err, looked for`
- `timesync/timesync.goose:34: error: cannot find the module common.err.err, looked for`
- `updater/updater.goose:40: error: cannot find the module common.err.err, looked for`
- `audit/audit.goose:43: error: cannot find the module common.err.err, looked for`
- `agenthost/agenthost.goose:34: error: cannot find the module common.err.err, looked for`
- `session/session.goose:27: error: cannot find the module common.err.err, looked for`
- `fs/fs.goose:27: error: cannot find the module common.err.err, looked for`
- `shell/shell.goose:30: error: cannot find the module common.args.args, looked for`
- `example/example.goose:33: error: cannot find the module common.boot.boot, looked for`
- `board/board.goose:26: error: cannot find the module common.err.err, looked for`
- `callmatrix/callmatrix.goose:30: error: cannot find the module common.err.err, looked for`
- `dashboard/dashboard.goose:27: error: cannot find the module common.err.err, looked for`
- `devices/devices.goose:34: error: cannot find the module common.boot.boot, looked for`
- `devices/hotplug.goose:32: error: cannot find the module common.err.err, looked for`
- `dock/dock.goose:27: error: cannot find the module common.err.err, looked for`
- `net/arp.goose:16: error: cannot find the module common.err.err, looked for`
- `net/icmp.goose:20: error: cannot find the module common.err.err, looked for`
- `net/ip.goose:27: error: cannot find the module common.err.err, looked for`
- `net/loopback.goose:29: error: cannot find the module common.err.err, looked for`
- `net/packet.goose:33: error: cannot find the module common.err.err, looked for`
- `net/tcp.goose:23: error: cannot find the module common.err.err, looked for`
- `net/udp.goose:19: error: cannot find the module common.err.err, looked for`
- `notify/notify.goose:37: error: cannot find the module common.err.err, looked for`
- `settings/settings.goose:29: error: cannot find the module common.err.err, looked for`
- `socket/bind.goose:27: error: cannot find the module common.err.err, looked for`
- `socket/socket.goose:30: error: cannot find the module common.err.err, looked for`
- `updater_client/updater_client.goose:33: error: cannot find the module common.err.err, looked for`
- `wallpaper/wallpaper.goose:28: error: cannot find the module common.err.err, looked for`

(File 7 bootlog's first line is the exemplar block above: `bootlog/bootlog.goose:27: error:
cannot find the module common.fmt.fmt, looked for`.)

## OC2B-467 — node --test tests/goose-programs.test.mjs beside the binary results

Command: `GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose node --test tests/goose-programs.test.mjs`
Result: **tests 4, pass 4, fail 0** (`✔ hello prints its one line`, `✔ echo answers the line it was
given`, `✔ heartbeat stops cleanly on the STOP sentinel and beats zero times`,
`✔ mcp-host answers list and echo, and logs both requests`; duration ~169 ms).
Beside the binary gate: the same 4 programs that PASS `goose check` standalone (files 37–40) are
exactly the 4 the node suite runs — consistent. The node suite passes `GOOSE` through env
(`process.env.GOOSE || "goose"`); the shell runner does not (see OC2B-458).

## OC2B-468 — MAC-ONLY failures (Goose half)

- MAC-ONLY: none. No Goose failure on this Mac is Mac-specific: the 40 per-file `check` failures are
  toolchain module-resolution behavior (import search path), reproducible anywhere the binary runs;
  the sandbox has no goose binary at all (`Goose toolchain: NOT FOUND` per BUILD.md), so there is no
  sandbox counterpart to diverge from. The hardcoded runner path (OC2B-458) happens to exist on this
  Mac only — noted as portability fact, not a labelled failure.

## Path-fix diff SKETCH (OC2B-473 — text only, NOT applied, for Buffy/Pax)

```diff
--- a/services/run-goose-tests.sh
+++ b/services/run-goose-tests.sh
@@ -5,7 +5,7 @@
 # Every check is a real process with a real assertion. Stated, not
 # hidden: runner script because the language lacks one.
 set -eu
-GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose
+GOOSE=${GOOSE:-/Users/test/mcp-servers/toolchains/goose-src/build/goose}
 PASS=0; FAIL=0
```

Effect: `GOOSE=/other/path sh services/run-goose-tests.sh` (or PATH `goose`) overrides the default
without editing; default preserves current-Mac behavior. Untested here (script not executed per grep-only rule).

## Proposed §19 status sub-block — Goose (NOT applied; status file untouched per spawn rules)

```
### §19 Goose gate-2 (OC2B-457–467, 468, 471, 473) — DONE on the Mac, status file edit pending owner
- Binary /Users/test/mcp-servers/toolchains/goose-src/build/goose, `goose b781587 (runtime 3901ec457ba9)`;
  source b78158797a3a4199a2c519d90d4e5421b2760fe3, md5 d4b72870edd8c7c763e12626d7728362.
- run-goose-tests.sh line 8 still hardcodes the toolchain path (grep count 1); diff sketch filed, not applied.
- Gate-2 (`goose check`, binary path on CLI, no file edits): 53 entries — 10 PASS (6 roots + echo/heartbeat/hello/host),
  40 FAIL (single shared cause: per-file import resolution looks beside the file, not the services root),
  3 SKIP (registry/devmgr/sockets README-only). All 40 first-error lines filed verbatim for Buffy R12; nothing fixed.
- node goose-programs: 4/4 PASS with GOOSE env pointing at the Mac binary. MAC-ONLY: none. tests/ additions: none.
```

Wall time §19 (OC2B-474): start 2026-11-02T16:04:18Z, end 2026-11-02T16:10:23Z (~6 min on the Mac).

Goose truth line: Goose gate-2 on the Mac passes the six roots and four standalone programs while forty service files fail per-file checks on one shared module-resolution cause, filed verbatim for the runner owner.
