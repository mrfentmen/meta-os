# BUILD_MATRIX — Layer 4 compile+run (Lane B, R5, 2026-11-04)

Toolchain: `/opt/homebrew/bin/goose` (goose b781587, runtime 3901ec457ba9). Method per row: generated driver (`import std;` + `import common.err.err;` + service modules, empty main), `goose check`, `goose -o --standalone`, `clang -O1` link with `os-build/layer1/host/host_shim.c`, host run under a 2s cap. Full command+output per row lives in the cited log; every row below matches its log's VERDICT line.

| service | status | log path | blocker |
|---|---|---|---|
| bootlog | COMPILED | services/bootlog/BUILD_LOG.txt | none (runs: exit: 0) |
| console | COMPILED | services/console/BUILD_LOG.txt | none for COMPILED; host run TIMEOUTs by design (service_main polls read_key forever; shim has no keyboard, so it yields until killed — banner+prompt captured) |
| time | COMPILED | services/time/BUILD_LOG.txt | none (runs: exit: 0) |
| logfmt | COMPILED | services/logfmt/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| logd | COMPILED | services/logd/BUILD_LOG.txt | none (runs: exit: 0) |
| supervisor | COMPILED | services/supervisor/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| watchdog | COMPILED | services/watchdog/BUILD_LOG.txt | none (runs: exit: 0) |
| storage | COMPILED | services/storage/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| input | COMPILED | services/input/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| display | COMPILED | services/display/BUILD_LOG.txt | COMPILED; supported driver t56 exit 0; known-red draft t115 (a .red file, not a test) has 7 FAILs recorded in log |
| netcfg | COMPILED | services/netcfg/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| dhcp | COMPILED | services/dhcp/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| dns | COMPILED | services/dns/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| timesync | COMPILED | services/timesync/BUILD_LOG.txt | none (runs: exit: 0) |
| updater | COMPILED | services/updater/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| audit | COMPILED | services/audit/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| agenthost | COMPILED | services/agenthost/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| session | COMPILED | services/session/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| fs | COMPILED | services/fs/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| shell | COMPILED | services/shell/BUILD_LOG.txt | none (runs: exit: 0; exit: 0) |
| example | COMPILED | services/example/BUILD_LOG.txt | no host run possible: svc_entry takes BootInfo& (kernel boot block); COMPILED only |
| socket | COMPILED | services/socket/BUILD_LOG.txt | COMPILED; supported driver t77 exit 0; known-red draft t132 (a .red file, not a test) has 5 FAILs recorded in log |
| registry | NOT BUILT | n/a (see services/registry/README.md) | NOT BUILT: logic lives in supervisor/supervisor.goose (sup_register/sup_lookup); a second table would be a second answer (services/registry/README.md:9-14) |
| devmgr | NOT BUILT | n/a (see services/devmgr/README.md) | NOT BUILT: retired name; implementation is services/devices/devices.goose (services/devmgr/README.md:1-5) |
| sockets | NOT BUILT | n/a (see services/sockets/README.md) | README ONLY: retired plural; implementation is services/socket/socket.goose (services/sockets/README.md:1-8); MANIFEST row 16 edit owed to manifest owner |

## Shared libraries (services/common/) — one line each (B4)

| library | status | log section | blocker |
|---|---|---|---|
| args | COMPILED | services/common/BUILD_LOG.txt##args | none |
| boot | COMPILED | services/common/BUILD_LOG.txt##boot | none |
| bytes | COMPILED | services/common/BUILD_LOG.txt##bytes | none |
| cfg | COMPILED | services/common/BUILD_LOG.txt##cfg | none |
| enc | COMPILED | services/common/BUILD_LOG.txt##enc | none |
| err | COMPILED | services/common/BUILD_LOG.txt##err | none |
| fmt | COMPILED | services/common/BUILD_LOG.txt##fmt | none |
| hash | COMPILED | services/common/BUILD_LOG.txt##hash | none |
| hex | COMPILED | services/common/BUILD_LOG.txt##hex | none |
| json | COMPILED | services/common/BUILD_LOG.txt##json | none |
| pool | COMPILED | services/common/BUILD_LOG.txt##pool | none |
| ring | COMPILED | services/common/BUILD_LOG.txt##ring | none |
| sort | COMPILED | services/common/BUILD_LOG.txt##sort | none |
| status | COMPILED | services/common/BUILD_LOG.txt##status | none |
| str | COMPILED | services/common/BUILD_LOG.txt##str | none |
| sys | COMPILED | services/common/BUILD_LOG.txt##sys | none |
| table | COMPILED | services/common/BUILD_LOG.txt##table | none |
| text | COMPILED | services/common/BUILD_LOG.txt##text | none |

Counts: services COMPILED 22 of 22 built (21 MANIFEST WRITTEN + socket, the real implementation behind MANIFEST row 16); NOT BUILT 3 of 24 MANIFEST rows (registry, devmgr, sockets — all README-only by design, B29); libraries COMPILED 18 of 18 (12 gating + 6 later: enc, text, table, sort, pool, status).
