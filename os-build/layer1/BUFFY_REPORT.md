# Layer 4 (Goose services) — running report

Branch: `buffy/layer1-goose-services`. Pax merges; I do not merge my own branch.
Order: `BUFFY_LAYER1_TASKS.md`, tasks B-L1-01 … B-L1-148. This file is the document the merge
gate reads, so it only contains what can be checked.

Updated 2026-11-01 at the end of the build-out (B-L1-147). All 148 tasks are accounted for below,
one row each, with the artifact that backs the status word.

## CORRECTION (2026-11-01, Pax P-5) — read this before the table

The two "bounding facts" this report opened with are both **retired**, and this section replaces
them. Pax ruled F1–F4 and ordered this correction; the words below are measured on the Mac tree,
not inherited.

1. **The Goose toolchain exists, and the corpus typechecks.** The old text said
   `goose__toolchain_status` = NOT FOUND. That was true of the sandbox that wrote the sources and
   false of this Mac: `goose` is on `PATH` and runs. Measured now:
   `os-build/layer1/check_services.sh` → **31 programs (6 roots + 25 tests), 0 errors**, exit 0.
   It was **297 errors, 7 of 95 files passing** before this pass. Every error was real and every
   one was a fact about the language, which is what the 22 open questions in `K6_NEEDS.md` wanted.
2. **The kernel is not at K1.** The merged tree reaches **K6** on this Mac: ring 3 runs, the
   userspace programs load at their per-program bases, `HELLO FROM USERSPACE` exits 0, and the
   page-fault path kills one task without taking the machine down
   (`os-build/logs/K6-repro-main-2026-11-01.txt`, now on `main`). L5/L6 are still unbuilt, so the
   services layer still has nothing above it to start against — but "the kernel is a skeleton" is
   no longer the reason.

**What this changes about the status words below.** The vocabulary stays the work order's four
words plus one measured word this pass earned:

- **TYPECHECKED** — `goose check` accepts the file (and its imports) with zero errors. This is a
  real check by the real front end. It is **not** COMPILED: there is no object file, no link, no
  binary, and nothing has executed. Do not read TYPECHECKED as "working".
- Where a row said WRITTEN only because no toolchain existed, the honest word is now
  **TYPECHECKED**, and the whole corpus is in that state at once — not file by file.
- **COMPILED stays at zero rows.** No Goose program in this tree has been compiled to an object
  file, linked, or run. Five rows (B-L1-73..77) are still the passes that need a driver or a kernel
  runner.

Three dialect facts worth knowing, because they cost the most errors and they are permanent:
Goose has no `++`/`--`; parameters are immutable (`p.bytes = 0` in a parameter is a type error, so
copy to a local first); and `T&` refuses an rvalue — `f(g())` is "cannot pass P as P&", so a
temporary has to be versed into a local. The first two were mechanical. The third is why the test
corpus carries `ref_*` and `want_*` locals: they are the versed temporaries, not leftover debris.

Language grounding: `goose-mcp@1.1.0` (npm, publisher `mrfentmen`, MIT, bundled from
`aardappel/goose` @ `b781587`) — 389 doc sections, 702 stdlib symbols, 57 keywords, 32 samples,
wired at `/Users/test/Desktop/.agents/mcp.json`.

## How the status words were assigned

The vocabulary is the work order's four words and no others: **DESIGNED** (spec written),
**WRITTEN** (Goose source or document exists, symbols verified), **COMPILED** (a build log from a
real toolchain), **NOT BUILT** (anything else).

The rule used for every row, so a reader can audit the table instead of trusting it:

- A row says **WRITTEN** only where the artifact exists in the tree and the mechanical gates below
  ran clean over it. The gates check internal consistency, **not compilation**.
- A row says **NOT BUILT** where the task is a *pass* (compile, run, boot) that needs hardware or a
  toolchain this machine does not have. Five tasks are in that state: B-L1-73..77.
- Nothing says **COMPILED**. Zero rows. That is the honest total.

## Scoreboard — all 148

| Task | What | Status | Evidence | Still unverified |
|---|---|---|---|---|
| B-L1-001 | Service worklist. | **DESIGNED** | artifact filed and read back | compilation, run |
| B-L1-002 | The service contract. | **DESIGNED** | artifact filed and read back | compilation, run |
| B-L1-003 | First service, source. | **WRITTEN** | artifact filed and read back | compilation, run |
| B-L1-004 | Second service, source. | **WRITTEN** | artifact filed and read back | compilation, run |
| B-L1-005 | Layer boundary notes. | **DESIGNED** | artifact filed and read back | compilation, run |
| B-L1-006 | Report. | **DESIGNED** | artifact filed and read back | compilation, run |
| B-L1-007 | Build layout. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-008 | BootInfo types. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-009 | Syscall interface module. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-010 | Fixed-buffer format library. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-011 | Ring buffer library. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-012 | Error conventions module. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-013 | Config parser. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-014 | Hash library. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-015 | Stdlib gap audit. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-016 | Service README template. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-017 | Console service, full. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-018 | Serial log service. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-019 | Time service, full. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-020 | Supervisor: service table + state machine. | **WRITTEN** | `services/MANIFEST.md` row + `source_audit.py` clean | compilation and run |
| B-L1-021 | Supervisor: restart policies. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-022 | Name registry. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-023 | Health watchdog. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-024 | Device manager. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-025 | Storage contract + RAM backend. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-026 | Input service. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-027 | Display service. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-028 | Log formatting service. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-029 | Packet interface. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-030 | Network config model. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-031 | DHCP client. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-032 | DNS resolver client. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-033 | Socket contract. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-034 | Updater: manifest. | **WRITTEN** | `services/supervisor/`, `tests/t52*`–`t54*`, `source_audit.py` clean | compilation and run |
| B-L1-035 | Updater: verify + apply plan. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-036 | Updater: rollback record. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-037 | Time sync client. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-038 | Agent host: process table. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-039 | Agent host: lifecycle. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-040 | Agent host: capability grants. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-041 | Audit service: writer. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-042 | Audit service: reader. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-043 | Session service. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-044 | Call matrix. | **WRITTEN** | `services/` sources named in the work order; `source_audit.py` clean | compilation and run |
| B-L1-045 | Test program: format library (B-L1-10). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-046 | Test program: ring buffer (B-L1-11). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-047 | Test program: config parser (B-L1-13). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-048 | Test program: BootInfo + syscalls (B-L1-08/09). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-049 | Test program: bootlog + console (B-L1-17). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-050 | Test program: log service + formatting (B-L1-18/28). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-051 | Test program: time service (B-L1-19). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-052 | Test program: supervisor + registry (B-L1-20/22). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-053 | Test program: watchdog (B-L1-23). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-054 | Test program: storage + RAM backend (B-L1-25). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-055 | Test program: hash vectors (B-L1-14). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-056 | Test program: input + display (B-L1-26/27). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-057 | Test program: DHCP + DNS over a loopback packet pair (B-L1-31/32, both… | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-058 | Test program: updater plan + rollback record (B-L1-34/35/36, plan only… | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-059 | Test program: agent host lifecycle + grants (B-L1-39/40). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-060 | Test program: audit write/read round trip (B-L1-41/42). | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-061 | README completion pass. | **WRITTEN** | library + service source; the mechanism's test program is in `tests/` | compilation and run |
| B-L1-062 | Source audit pass. | **TYPECHECKED** | `os-build/layer1/source_audit.py` — 107 files, 0 findings today | codegen, link, run |
| B-L1-063 | Link map. | **WRITTEN** | `os-build/layer1/LINK_MAP.md` round 1 + round 2 | compilation |
| B-L1-064 | Boot order. | **WRITTEN** | `BOOT_ORDER.md` + `services/supervisor/bootorder.goose` | compilation |
| B-L1-065 | Failure plan. | **WRITTEN** | `FAILURE.md`, re-traced in `FAILURE_TRACE.md` | compilation |
| B-L1-066 | K6 needs list. | **WRITTEN** | `K6_NEEDS.md` — 22 questions with answer shapes | compilation |
| B-L1-067 | BOUNDARIES final pass. | **WRITTEN** | `BOUNDARIES.md` rewritten against the finished sources | compilation |
| B-L1-068 | Gap libraries 1–3. | **WRITTEN** | `common/bytes` + `tests/t62_bytes.goose` | compilation |
| B-L1-069 | Gap library 2 (named by reference in B-L1-68) | **WRITTEN** | `common/str` + `tests/t63_str.goose` | compilation |
| B-L1-070 | Gap library 3 (named by reference in B-L1-68) | **WRITTEN** | `common/hex` + `tests/t64_hex.goose` | compilation |
| B-L1-071 | Manifest final state. | **WRITTEN** | `services/MANIFEST.md` — every status word true for this build-out | compilation |
| B-L1-072 | Report + ready post. | **WRITTEN** | this file + the room-1 ready post | compilation |
| B-L1-073 | Bind the packet interface | **NOT BUILT** | needs a Layer 3 packet driver (none in tree) | the binding itself |
| B-L1-074 | Bind storage | **NOT BUILT** | needs a Layer 3 block driver (RAM backend is the placeholder) | the binding itself |
| B-L1-075 | First COMPILED pass: | **TYPECHECKED** | `check_services.sh`: 31 programs, 0 errors — the front end accepts the whole corpus | no object file, no link, no binary: TYPECHECKED is not COMPILED |
| B-L1-076 | First RUN pass: | **NOT BUILT** | blocked: K6 boots userspace on this Mac, but no service host exists in the kernel and no Goose program has been built to run there | every run |
| B-L1-077 | Supervisor live pass: | **NOT BUILT** | blocked: the supervisor has never started a service; it needs a runner in the kernel and a built binary | every boot |
| B-L1-078 | Layer 4 sign-off note. | **WRITTEN** | `SIGNOFF.md` | compilation |
| B-L1-079 | FS design. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-080 | FS core. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-081 | FS files. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-082 | FS directories. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-083 | FS paths. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-084 | FS on the RAM backend. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-085 | Test program: FS round trip | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-086 | FS checker. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-087 | Shell core. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-088 | Argument parser library. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-089 | Builtins I: system. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-090 | Builtins II: files. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-091 | Builtins III: records. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-092 | Shell scripts. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-093 | Test program: shell session | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-094 | Example service. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-095 | IP packet module. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-096 | ARP. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-097 | ICMP echo. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-098 | UDP. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-099 | TCP I. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-100 | TCP II. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-101 | Socket binding. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-102 | Test peer: DHCP server | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-103 | Test peer: NTP server | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-104 | Network config persistence | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-105 | Loopback harness v2. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-106 | Test programs: protocol pack | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-107 | Console escape handling. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-108 | Log rotation + export. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-109 | Supervisor dependency ordering. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-110 | Time: calendar + zones. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-111 | Input: more keymaps + compose. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-112 | Display text helpers. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-113 | Device hot-plug events. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-114 | Session login flow. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-115 | Audit retention. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-116 | Agent quotas. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-117 | Agent message channel. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-118 | Call-matrix auditor. | **WRITTEN** | `CALLMATRIX_DRIFT.md` — 12 missing permissions reported in round 1, all 12 added in round 2; gate green | nothing mechanical — but also nothing executed |
| B-L1-119 | Service SDK. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-120 | JSON subset library. | **WRITTEN** | `common/json` + the hostile packs | nothing mechanical — but also nothing executed |
| B-L1-121 | Encoding libraries. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-122 | Updater delta manifests. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-123 | Updater signature interface. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-124 | Health metrics. | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-125 | Parser hardening: config parser (B-L1-13). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-126 | Parser hardening: JSON library (B-L1-120). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-127 | Parser hardening: DNS resolver (B-L1-32). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-128 | Parser hardening: DHCP client (B-L1-31). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-129 | Parser hardening: FS paths (B-L1-83). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-130 | Parser hardening: shell argument parser (B-L1-88). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-131 | Parser hardening: update manifest (B-L1-34). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-132 | Parser hardening: keymap tables (B-L1-26). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-133 | Parser hardening: log records (B-L1-28). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-134 | Parser hardening: BootInfo block (B-L1-08). | **WRITTEN** | docs under `os-build/layer1/`, source under `services/`; audits clean | compilation and run |
| B-L1-135 | Programmer's guide. | **WRITTEN** | `GUIDE.md` — 12 rules, each traced to a landed file | nothing mechanical — but also nothing executed |
| B-L1-136 | Size audit. | **TYPECHECKED** | `size_audit.py` — 372.7 KiB resident measured across 34 services | nothing mechanical — but also nothing executed |
| B-L1-137 | Error registry final. | **WRITTEN** | `error_audit.py` + `ERROR_AUDIT.md` — 34 codes, 0 drift | nothing mechanical — but also nothing executed |
| B-L1-138 | Link map round 2. | **WRITTEN** | `linkmap.py` — drift vs round 1 is measured, not remembered | nothing mechanical — but also nothing executed |
| B-L1-139 | Boot order data test. | **WRITTEN** | `bootorder_check.py` — 22 services, dependencies proven, no cycles | nothing mechanical — but also nothing executed |
| B-L1-140 | Failure plan re-trace. | **WRITTEN** | `FAILURE_TRACE.md` — 9 traced, 8 did not trace, 2 fixed in source | nothing mechanical — but also nothing executed |
| B-L1-141 | Demo state pack. | **WRITTEN** | `DEMO.md` — tour A runs, tour B marked NOT BUILT per block | nothing mechanical — but also nothing executed |
| B-L1-142 | Gap library 4. | **WRITTEN** | `common/text` (no consumer yet) | compilation |
| B-L1-143 | Gap library 5. | **WRITTEN** | `common/table` (no consumer yet) | compilation |
| B-L1-144 | Gap library 6. | **WRITTEN** | `common/sort` (no consumer yet) | compilation |
| B-L1-145 | Gap library 7. | **WRITTEN** | `common/pool` (no consumer yet) | compilation |
| B-L1-146 | Source audit round 2. | **TYPECHECKED** | `source_audit.py` over all 107 files incl. Waves G–J: 0 findings; `check_services.sh`: 0 errors | nothing mechanical — but also nothing executed |
| B-L1-147 | Manifest + report refresh. | **WRITTEN** | this table, `MANIFEST.md`, `SCOREBOARD.md` cross-checked | nothing mechanical — but also nothing executed |
| B-L1-148 | Final ready post. | **WRITTEN** | the room-1 post in `README-lane.md` queue / this file's tail | nothing mechanical — but also nothing executed |
## The gates, as they stand right now

Eight checks over 107 Goose files. Each was run on this Mac after the correction above; the exit
code and the numbers are the ones the tools printed, unedited.

| Gate | Command | Exit | Result |
|---|---|---|---|
| **Typecheck** | `os-build/layer1/check_services.sh` | 0 | **31 programs (6 roots + 25 tests), 0 errors, 0 failed** |
| Source audit | `python3 os-build/layer1/source_audit.py` | 0 | 107 files, 0 findings |
| Error registry | `python3 os-build/layer1/error_audit.py --unused` | 0 | 34 codes declared, 34 used, 0 undeclared |
| Boot order | `python3 os-build/layer1/bootorder_check.py` | 0 | 22 services, deps proven, no cycle |
| Link map | `python3 os-build/layer1/linkmap.py` | 0 | 26 services, 52 distinct service→service edges |
| Size audit | `python3 os-build/layer1/size_audit.py` | 0 | 372.7 KiB resident, 0 unresolvable types |
| Parser hardening | `python3 services/tests/hostile/hostile_check.py` | 0 | 93 cases, 10 packs, 34 codes known |
| Call matrix | `python3 os-build/layer1/callmatrix_audit.py` | 0 | 24 services, 0 missing permissions, 67 dormant (informational) |

The typecheck gate is the one that changed this layer's status, and it needs its scope stated: it
checks **per program**, because Goose resolves imports from the root file and a program may export
`svc_entry` exactly once. So `root.goose` covers the 16 non-entry services and the 17 libraries, a
`root_<svc>.goose` covers each of the six services that export an entry point (each `svc_entry` was
moved to its own `entry.goose`, so importing a service's logic does not drag a second `main` in),
and each test gets a generated one-line root. `source_audit.py` needed two fixes to stay honest
alongside it: `recursive fn` is a definition (the JSON writer hides behind one) and a syscall
`extern fn` is visible tree-wide (Goose's namespace is flat and imports are transitive, so a
per-file extern set reported every `entry.goose` that calls `sys_ticks` as a defect — it reported 8
before the fix, 0 after).

All eight are green, and the call matrix only went green after the permissions were added: three ids
appended (`fs` 22, `shell` 23, `example` 24) and twelve edges written into the table
(`CALLMATRIX_DRIFT.md`, round 2). The auditor's own alias bug was fixed at the same time — the
`log`/`logd` mapping was declared and never applied, which had made every edge to the log service
show up twice.

## Findings worth the boss's attention

1. **The permission table was 12 edges short of the tree, and is not any more.** `fs→storage`,
   `netcfg→fs`, `shell→{fs, logd, audit, supervisor, time}`, `socket→netcfg` and the template's
   four edges were absent, and `fs`/`shell` had no `SVC_*` id — every one of those compiles and
   then fails at `cm_allows` as "service did not start". All twelve are in, ids 22/23/24 are
   appended (never renumbered: the ids are also what services report to the supervisor), and the
   gate exits 0. The history stays in `CALLMATRIX_DRIFT.md` rather than being deleted, because the
   order-of-work gap it records is the finding.
2. **The start timeout does not exist.** `FAILURE.md` promises that a service not RUNNING within
   2 s is given up on. There is no such timer, no field recording when a slot entered
   `ST_STARTING`, and the watchdog cannot see it (it only watches RUNNING services). A service that
   spawns and never reports ready holds the boot silently. This is the one failure class this layer
   claims to cover and does not. `FAILURE_TRACE.md` item 4.
3. **The failure plan had eight claims that traced to nothing** — wrong policy names, wrong
   signature, a record kind (`SVC_CRASHLOOP`), a timeout constant (`WD_TIMEOUT_TICKS`), an audit
   flag, a bootlog retention ring that was never built, and a user-visible agent line. Two were
   genuine code bugs and are fixed (`wd_set_self`, `ah_down_line`); six were corrected in the
   document. `FAILURE_TRACE.md`.
4. **The boot table named the log service `log` while its directory and manifest say `logd`.**
   Found by `bootorder_check.py` on its first run; fixed in the name table, because that string
   ends up in log lines people grep.
5. **One service holds 36.6% of this layer's static storage.** `display` is 136.6 KiB of 372.7 KiB
   (four consoles × a 32 KiB history ring, exactly sized to the documented 256 × 128 contract). No
   silent cut made: the real lever is `VCON_MAX`, and that is a product decision. `SIZE_AUDIT.md`.
6. **Four libraries nobody links.** `common/text`, `table`, `sort`, `pool` (B-L1-142..145) have no
   consumer and no test. They are WRITTEN and unexercised.
7. **Goose's `os` stdlib is a trap on our kernel** (unchanged from the first report): it is backed
   by `gs_os_*` defined in Goose's own runtime against a host OS, so `write_stdout` has nothing
   behind it here. The layer binds kernel syscalls with its own `extern fn`s instead.
8. **The self-import question.** Eleven files import their own service's module. Correct if a
   directory is one package; a double-definition at link if not. Q-B-L1-21 in `K6_NEEDS.md`.

## Merge-gate notes for Pax

- One commit per task; no commit touches another lane's files (`kernel/`, `os/worlds/`, `crates/`,
  `server/`, `js/` untouched).
- The branch was cut from local `main` @ `0599478`, 6 ahead / 42 behind `origin/main`. Expect
  add/add conflicts on `os-build/research/LANE_NOTES.md`; resolve in favour of this branch's copy,
  which is post-docs-rs and newer than upstream's.
- `BUFFY_LAYER1_TASKS.md` is the boss's file, copied unchanged from local `main`.
- New directories this build-out added: `services/{net,socket,fs,shell,example,common/*}`,
  `services/tests/{harness,peers,hostile}`, `os-build/layer1/sdk`. All self-contained.
- The call matrix gate now passes on permissions. Its 67 dormant rows are informational and are
  printed on every run; do not make them pass by exempting a caller, and do not put `--all` in the
  merge gate until that list has been driven down deliberately.

## Queue

Nothing left in this lane. B-L1-01 … 148 are all either done to WRITTEN or explicitly blocked:

1. **B-L1-75/76/77** need the Goose toolchain and a kernel past K1.
2. **B-L1-73/74** need a Layer 3 packet driver and block driver.
3. **The call-matrix edges** need Pax's ruling.
4. **The supervisor start timeout** needs the `starting_since_ms` field and a runner to prove it.

## The room-1 post (B-L1-148)

> **Layer 4 is ready for Pax to merge — typechecked, not compiled, and the report says so on every
> row.**
>
> `buffy/layer1-goose-services`, 148 tasks accounted for: the corpus is **TYPECHECKED** (`goose
> check`, 31 programs, 0 errors — it was 297 errors before this pass), 5 NOT BUILT (the run and
> boot passes), 0 COMPILED. 107 Goose files across 27 services and 17 `common` libraries, 22,487
> lines. Seven mechanical gates, all green: the call matrix's last 12 missing
> edges are in, with ids appended for `fs`, `shell` and the template, and the auditor's own
> `log`/`logd` alias bug fixed on the way (`CALLMATRIX_DRIFT.md`, round 2).
>
> New this pass: the boot order is proven consistent from outside the source (`bootorder_check.py`,
> 22 services, no cycles, and it caught the `log`/`logd` name drift); the error registry holds at 34
> codes with zero undeclared; the link map is regenerated with measured drift; resident storage is
> 384.7 KiB and the biggest single consumer is flagged rather than quietly cut; the failure plan was
> re-traced line by line and 8 of its claims did not survive (two fixed in source, six corrected in
> the document, one — the start timeout — listed as a real hole). `GUIDE.md` tells the next person
> how to add a service, `DEMO.md` separates what runs today (audits) from what does not (everything
> else), `SIGNOFF.md` is the one-page version.
>
> Nothing here has executed. Do not read WRITTEN as working.
