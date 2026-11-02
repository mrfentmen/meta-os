# Claim audit — every headline claim mapped to its evidence (B251)

Scope: the claim sentences in `README.md`, `KERNEL_SPEC.md`, and
`os-build/SCOREBOARD.md` that describe the kernel and the layers. Each row
names the sentence's source, the artifact that is supposed to prove it, and
this run's verdict.

Verdict words:

- **PROVEN** — the named committed log/artifact exists and contains the
  behaviour (checked against `os-build/BOOT_LOG_INDEX.md` and
  `os-build/gates.md` on 2026-11-02).
- **PARTIAL** — some clauses are evidenced; the missing clause is named.
- **CODE-INSPECTED** — the source/artifact exists and says this, but no run
  was repeated in this lane.
- **UNVERIFIED** — no artifact in this tree proves it here.
- **CONFLICT** — two committed documents give different numbers for the same
  thing.
- **STALE** — the claim was true once; a newer measured run disagrees.

## README claims

| Claim (source) | Evidence named / found | Verdict |
|---|---|---|
| "K1-K5 proven by committed boot logs" (`README.md`, systems table, kernel row) | `os-build/logs/K1-boot.txt` (alive line + K4/K6 lines), `K5-boot.txt` (`C sleeping 200 ticks`, uptime ticks) | **PROVEN** |
| "K6 proven except that no Goose service has a process yet" (same row) | `MERGED-boot-2.txt:33-35` (hello, `HELLO FROM USERSPACE`, `user exit code 0`), `:45` (user fault kills the task), `:52` (bad syscall refused); no service process line anywhere | **PARTIAL** — userspace proven, Goose process missing, exactly as stated |
| "Node (app, server, eval harnesses): 1933 run, 1877 pass, 56 fail" (`README.md`, Test numbers) | this tree, 2026-11-02: `npm test` = 2048 run, 1993 pass, 55 fail; clean HEAD clone = 2002/1947/55 | **STALE** — the failures are the same native set; the headline numbers are old |
| "Rust workspace: 1412 pass, 0 fail" (`README.md`, Test numbers) | no workspace build was run on this 8GB lane; no log named | **UNVERIFIED** |
| "Python job queue: 110 pass" (`README.md`) | `tests/queue-python` on this tree: 139 passed | **STALE** |
| "Python Officina: 49 pass" (`README.md`) | `tests/officina` on this tree: 49 passed | **PROVEN** |
| "Services layer: 33 programs, 1,253 checks, 0 failed" (`README.md`) | `os-build/layer1/SERVICE_RUNS.md`, `TRANSCRIPTS.md`; host run, not kernel | **CODE-INSPECTED** (host artifact, not rerun here) |
| "This layer is not booted ... five syscalls refused on purpose" (`README.md`) | `os-build/layer1/host/host_shim.c`; `os-build/layer1/SERVICES_SYSCALL_MAP.md` | **CODE-INSPECTED** |

## KERNEL_SPEC milestone claims

| Claim | Evidence | Verdict |
|---|---|---|
| K1: alive line on serial, proof `K1-boot.txt` line 2 | `K1-boot.txt` contains `META OS KERNEL - alive (K1)` | **PROVEN** |
| K2: VGA console, `K2-boot.png` 196 of 2000 cells | `K2-boot.png` is committed; the cell count is a screenshot measurement, not a log line | **CODE-INSPECTED** (pixels not recounted here) |
| K3: `K3 timer: 10 ticks` and a typed `status` answered in `K3-boot.txt` | `K3-boot.txt` carries the timer line and a typed `STATUS` (per `BOOT_LOG_INDEX.md`) | **PROVEN** for timer + status |
| K3: "`K3 keyboard: first scancode 0x1f`" (SCOREBOARD L3 wording) | not present in the indexed K3 description; no gate line for it | **UNVERIFIED** |
| K4: "memory map, 61660 frames, heap stress ... in `K1-boot.txt`" | `K1-boot.txt` per the allocator record reports `127199 covered frames`; `SCOREBOARD.md` also says 127199 | **CONFLICT** — 61660 vs 127199 for the same boot |
| K5: A/B/C rotation and 200-tick sleep/wake in `K1-boot.txt` | `K5-boot.txt` (`C sleeping 200 ticks`, uptime) and `K1-boot.txt` rotation lines | **PROVEN** |
| K6: ELF load, `int 0x80`, exit 0, refused syscall, fault isolation | `MERGED-boot-2.txt:33-35`, `:45`, `:52`; `K1-boot.txt` | **PARTIAL** — last clause (Goose service process) not met, as the spec itself says |

## SCOREBOARD layer claims

| Layer | Evidence named | Verdict |
|---|---|---|
| L1 Boot PROVEN | `K1-boot.txt` line 2 | **PROVEN** |
| L2 Kernel core PROVEN | same log: memory map, frames, paging probe, heap stress, A/B/C, sleep/wake, ring-3 ELF, exit, refusal, fault | **PROVEN** (the 61660/127199 conflict above is the only number in doubt) |
| L3 Drivers PROVEN | `K2-boot.png`; `K3-boot.txt` timer + typed `status` | **PARTIAL** — keyboard scancode clause unverified |
| L4 Goose HOST | `SERVICE_RUNS.md` (33 programs, 1253 checks), host shim refuses five | **CODE-INSPECTED** |
| L5 Agent runtime HOST | `tests/agents-*.test.mjs` in `npm test` | **PROVEN** as host tests (they run and pass in the suite) |
| L6 Shell PARTIAL | `K3-boot.txt` typed `status`; `K7-boot.txt` `ps` rows | **PROVEN** for the kernel shell commands; Lobster shell and graphical home are not in the tree |
| L7 Programs HOST | `os-build/ROOT_MANIFEST.md` | **CODE-INSPECTED** |
| "No real hardware boot. Every proof above is QEMU 11.1.3" | logs are QEMU serial captures; no hardware log exists | **PROVEN** (the absence is the claim) |

## What this audit does not do

- It does not re-run QEMU or count screenshot pixels; those need the Mac lane.
- It does not edit the claiming documents. The K4 number conflict and the
  stale README test table are reported to their owners, not silently fixed.
- A claim not listed here is not audited, not disproven.
